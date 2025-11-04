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
    @http.route("/api/create/sale_order", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_sale_orders(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing sale order from tally to odoo %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        if 'sale_orders' not in popup_data:
            _logger.info('@The Tally system does not contain any sale orders.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['sale_orders']),
            'tally_data': popup_data,
            'tally_entry_type': 'sale_order'
        })
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
            _logger.info('@ Total Received data to create sale order from Tally to Odoo: %s',
                         popup_data['sale_orders'])
        order_count = 0
        tally_log_ids = []
        for rec in popup_data['sale_orders']:
            try:
                order_count += 1
                tally_id = request.env['sale.order'].sudo().search([
                    ('tally_so_id', '=', rec['tally_so_id'])])
                customer_id = request.env['res.partner'].sudo().search(
                    [('tally_id', '=', rec['partner_id'])],limit=1)
                if not customer_id:
                    country_id = request.env['res.country'].sudo().search([
                        ('name', '=', str(rec['country']))], limit=1)
                    state_id = request.env['res.country.state'].sudo().search([
                        ('name', '=', str(rec['state']))], limit=1)
                    customer_id = request.env['res.partner'].sudo().create({
                        'name': rec['partner_name'],
                        'type_partner': 'customer',
                        'tally_id': int(rec['partner_id']),
                        'street': rec['street'],
                        'email': rec['email'],
                        'state_id': state_id.id or '',
                        'country_id': country_id.id or '',
                        'company_id': company_id.id,
                        'property_account_receivable_id': config_setup_id.property_recieveable.id,
                        'property_account_payable_id': config_setup_id.property_payable.id
                    })
                if not tally_id:
                    order_line = []
                    for line in rec['sale_order_lines']:
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])], limit=1)
                        if product_id:
                            tax_val = []
                            if 'tax_ids' in line:
                                for tax in line['tax_ids']:
                                    tax_name = tax['name'] + ' ' + str(tax['amount']) + '%'+ ' ' +'('+str(tax['emirate'])+')'
                                    account_tax = request.env['account.tax'].sudo().search(
                                        [('name', '=', str(tax_name)), ('type_tax_use', '=', 'sale')],
                                        limit=1)
                                    if not account_tax:
                                        account_tax = request.env['account.tax'].sudo().create({
                                            'name': str(tax_name),
                                            'amount': float(tax['amount']),
                                            'country_id': company_id.country_id.id,
                                            'type_tax_use': 'sale',
                                            'amount_type': 'percent'
                                        })
                                    tax_val.append(account_tax.id)
                            # else:
                            #     account_tax = request.env['account.tax'].sudo().search(
                            #         [('name', '=', 'VAT'), ('type_tax_use', '=', 'sale')],
                            #         limit=1)
                            #     if not account_tax:
                            #         tax_id = request.env['account.tax'].sudo().create({
                            #             'name': 'VAT',
                            #             'amount': 0.0,
                            #             'country_id': company_id.country_id.id,
                            #             'type_tax_use': 'sale',
                            #             'amount_type': 'percent'
                            #         })
                            #         tax_val.append(tax_id.id)
                            #     if account_tax:
                            #         tax_val.append(account_tax.id)
                            so_line = [0, 0, {
                                'product_id': product_id.id,
                                'product_uom_qty': line['product_qty'],
                                'price_unit': line['price_unit'],
                                'discount': line['discount'],
                                'tax_id': tax_val
                            }]
                            order_line.append(so_line)
                    if order_line:
                        warehouse_id = request.env['stock.warehouse'].sudo().search([('id', '=', int(rec['warehouse_id']))], limit=1)
                        date = datetime.strptime(rec['date_order'], '%d-%m-%Y')
                        date_val = date.strftime('%Y-%m-%d')
                        sale_order = request.env['sale.order'].sudo().create({
                            'partner_id': customer_id.id,
                            'date_order': date_val,
                            'tally_so_id': rec['tally_so_id'],
                            'tally_so_name': rec['tally_so_name'],
                            'warehouse_id': warehouse_id.id,
                            'order_line': order_line
                        })
                        # sale_order.sudo().button_confirm()

                        if module.state == 'installed':
                            vals = (0, 0, {
                                'master_type': 'sale_order',
                                'sync_action': 'create',
                                'sync_data': str(rec),
                                'error_data': 'sale order has been created',
                                'name': sale_order.name,
                                'sync_status': 'done',
                                'sync_for': 'trans',
                                'tally_record_name': rec['tally_so_name'],
                                'records_created_id': sale_order.id,
                                'tally_record_id': rec['tally_so_id']
                            })
                            tally_log_ids.append(vals)
                            _logger.info('Log line Created...: %s', rec['tally_so_name'])
                _logger.info('@ Number of order imported: %s', order_count)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'sale_order',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_so_name'],
                        'tally_record_id': rec['tally_so_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        status = ''
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
