""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating Products.
    It includes methods for processing Tally data and updating Odoo records accordingly. """
    @validate_token
    @http.route("/api/create/sale_delivery", type="json", auth="public",
                methods=["POST"], csrf=False)
    def _api_create_purchase_order(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing sale delivery %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        if 'sale_delivery' not in popup_data:
            _logger.info('@The Tally system does not contain any sale delivery.')
            return
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        # bill_count = 0
        _logger.info('@ Total Received data to sale delivery from Tally to Odoo: %s',
                     popup_data['sale_delivery'])
        tally_log_ids = []

        for rec in popup_data['sale_delivery']:
            try:
                sale_id = request.env['sale.order'].sudo().search([
                    ('tally_so_name', '=', rec['tally_so_name'])])
                order_date = sale_id.date_order
                if not sale_id.picking_ids:
                    order_line = []
                    for line in rec['tally_delivery_line']:
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])],
                            limit=1)
                        tax_val = []
                        if 'tax_ids' in line:
                            for tax in line['tax_ids']:
                                tax_name = tax['name'] + ' ' + str(tax['amount']) + '%'+ ' ' +'('+str(tax['emirate'])+')'
                                account_tax = request.env['account.tax'].sudo().search(
                                    [('name', '=', str(tax_name)), ('type_tax_use', '=', 'sale')], limit=1)
                                # tax_id = False
                                if not account_tax:
                                    tax_id = request.env['account.tax'].sudo().create({
                                        'name': str(tax_name),
                                        'amount': float(tax['amount']),
                                        'country_id': company_id.country_id.id,
                                        'type_tax_use': 'sale',
                                        'amount_type': 'percent'
                                    })
                                    request.env.cr.commit()
                                    tax_val.append(tax_id.id)
                                if account_tax:
                                    tax_val.append(account_tax.id)
                        for line_item in sale_id.order_line:
                            if line_item.product_id.id == product_id.id:
                                line_item.sudo().update({
                                    'product_uom_qty': line['product_qty'],
                                    'price_unit': line['price_unit'],
                                    'tax_id': tax_val
                                })
                            # if line_item.product_id.id != product_id.id:
                            #     line = {
                            #         'product_id': product_id.id,
                            #         'product_uom_qty': line['product_qty'],
                            #         'price_unit': line['price_unit'],
                            #         'tax_id': tax_val
                            #     }
                            #     order_line.append((0, 0, line))
                    sale_id.sudo().write({
                        'order_line': order_line
                    })
                    if not sale_id.picking_ids:
                        sale_id.sudo().action_confirm()
                        sale_id.sudo().write({
                            'date_order': order_date
                        })
                if sale_id.picking_ids:
                    for vals in sale_id.picking_ids:
                        if vals.state == 'assigned':
                            date = datetime.strptime(rec['date'], '%d-%m-%Y')
                            date_val = date.strftime('%Y-%m-%d')
                            vals.sudo().update({
                                'tally_receipt_no': rec['tally_delivery_id'],
                                'tally_receipt_name': rec['tally_delivery_id'],
                                'scheduled_date': date_val,
                                'date_deadline': date_val
                            })
                            move_product = 0
                            done_qty_product = 0
                            for line in rec['tally_delivery_line']:
                                product_id = request.env['product.product'].sudo().search(
                                    [('tally_id', '=', line['product_id'])],
                                    limit=1)
                                for move in vals.move_ids_without_package:
                                    move_product += 1
                                    if move.product_id.id == product_id.id:
                                        move_product += 1
                                        move.sudo().write({
                                            'quantity': line['quantity_done']#updated the field a quantity_done to quantity
                                        })
                                        if move.product_uom_qty == float(line['quantity_done']):
                                            done_qty_product += 1
                                # vals.button_validate()
                            if len(vals.move_ids_without_package) != done_qty_product:
                                wiz_act = vals.button_validate()
                                if wiz_act:
                                    wiz = (request.env[wiz_act['res_model']].sudo().
                                           with_context(wiz_act['context']))
                                    wiz.process()
                            else:
                                vals.button_validate()
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'delievry',
                            'sync_action': 'create',
                            'sync_data': str(rec),
                            'error_data': 'Sale Delivery has been created successfully',
                            'sync_status': 'done',
                            'sync_for': 'trans'
                        })
                        tally_log_ids.append(vals)

            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'delievry',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans'
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id.id,
                'trans_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s', tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
            # total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.trans_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : " +
                                                str(rec.tally_record_id) +
                                                " - " + "ODOO ID : " +
                                                str(rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.trans_log_line_ids:
                    if rec.sync_status == 'fail':
                        failed_records.append(rec.tally_record_name)
            return {
                'status': str(status),
                'created_records': str(created_records) if created_records else "0",
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return None
