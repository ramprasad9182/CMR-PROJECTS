from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request
from datetime import datetime
import json
import logging
_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    @validate_token
    @http.route("/api/create/purchase_order", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_purchase_order(self, **post):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('@ Total Received data %s' % popup_data)
        if 'purchase_orders' not in popup_data:
            _logger.info('@The Tally system does not contain any purchase orders.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['purchase_orders']),
            'tally_data': popup_data,
            'tally_entry_type': 'purchase_order'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        module = request.env['ir.module.module'].sudo().search([('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s' % start_date)
            _logger.info('@ Total Received data to create Purchase order from Tally to Odoo: %s' % popup_data['purchase_orders'])
        order_count = 0
        tally_log_ids = []
        for rec in popup_data['purchase_orders']:
            try:
                order_count += 1
                tally_id = request.env['purchase.order'].sudo().search([('tally_po_id', '=', rec['tally_po_id'])])
                vendor_id = request.env['res.partner'].sudo().search([('tally_id', '=',rec['partner_id'])],limit=1)
                if not vendor_id:
                    country_id = request.env['res.country'].sudo().search([('name', '=', str(rec['country']))], limit=1)
                    state_id = request.env['res.country.state'].sudo().search([('name', '=', str(rec['state']))],
                                                                              limit=1)
                    vendor_id = request.env['res.partner'].sudo().create({
                        'name': rec['partner_name'],
                        'type_partner': 'supplier',
                        'tally_id': int(rec['partner_id']),
                        'street': rec['street'],
                        'email': rec['email'],
                        'state_id': state_id.id or '',
                        'country_id': country_id.id or '',
                        'company_id': company_id.id
                    })
                if not tally_id:
                    order_line = []
                    for line in rec['purchase_order_lines']:
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])], limit=1)
                        if product_id:
                            tax_val = []
                            if 'tax_ids' in line:
                                for tax in line['tax_ids']:
                                    tax_name = tax['name'] + ' ' + str(tax['amount']) + ' ' + '%'
                                    account_tax = request.env['account.tax'].sudo().search(
                                        [('name', '=', str(tax_name)), ('type_tax_use', '=', 'purchase')], limit=1)
                                    if not account_tax:
                                        account_tax = request.env['account.tax'].sudo().create({
                                            'name': str(tax_name),
                                            'amount': float(tax['amount']),
                                            'country_id': company_id.country_id.id,
                                            'type_tax_use': 'purchase',
                                            'amount_type': 'percent'
                                        })
                                    tax_val.append(account_tax.id)
                            po_line = [0,0, {
                                'product_id': product_id.id,
                                'product_qty': line['product_qty'],
                                'price_unit': line['price_unit'],
                                'taxes_id': tax_val
                            }]
                            order_line.append(po_line)
                    if order_line:
                        date = datetime.strptime(rec['date_order'], '%d-%m-%Y')
                        date_val = date.strftime('%Y-%m-%d')
                        purchase_order = request.env['purchase.order'].sudo().create({
                            'partner_id': vendor_id.id,
                            'date_order': date_val,
                            'tally_po_id': rec['tally_po_id'],
                            'tally_po_name': rec['tally_po_name'],
                            'order_line': order_line
                        })
                        # purchase_order.sudo().button_confirm()

                        if module.state == 'installed':
                            vals = (0,0,{
                                'master_type': 'purchase_order',
                                'sync_action': 'create',
                                'sync_data': str(rec),
                                'error_data': 'purchase order has been created',
                                'name': purchase_order.name,
                                'sync_status': 'done',
                                'sync_for': 'trans',
                                'tally_record_name': rec['tally_po_name'],
                                'records_created_id': purchase_order.id,
                                'tally_record_id': rec['tally_po_id']
                            })
                            tally_log_ids.append(vals)
                            _logger.info('Log line Created...: %s' % rec['tally_po_name'])
                    _logger.info('@ Number of order imported: %s' % order_count)

            except Exception as e:
                info = "There was a problem {}".format((e))
                error = "Something went wrong"

                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'purchase_order',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_po_name'],
                        'tally_record_id': rec['tally_po_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s' % tally_log_ids)

        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id.id,
                'trans_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s' % tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
            total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : " + str(rec.tally_record_id) + " - " + "ODOO ID : " + str(
                            rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.master_log_line_ids:
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