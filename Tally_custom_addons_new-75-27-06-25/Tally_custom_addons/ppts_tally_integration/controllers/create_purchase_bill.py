""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    def _get_stock_type_ids(self, move):
        """Default value function: This will determine picking type of incoming shipment"""
        data = request.env['stock.picking.type'].search([])
        if move.move_type == 'out_invoice':
            for line in data:
                if line.code == 'outgoing':
                    return line
        if move.move_type == 'in_invoice':
            for line in data:
                if line.code == 'incoming':
                    return line
        if move.move_type == 'out_refund':
            for line in data:
                if line.code == 'incoming':
                    return line
        if move.move_type == 'in_refund':
            for line in data:
                if line.code == 'outgoing':
                    return line

    @validate_token
    @http.route("/api/create/purchase_bill", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_purchase_bill(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Data Received from tally to create Purchase Bill %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        if 'bill' not in popup_data:
            _logger.info('@The Tally system does not contain any purchase bills.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['bill']),
            'tally_data': popup_data,
            'tally_entry_type': 'in_invoice'})
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        _logger.info('@ Total Received data to create bills from Tally to Odoo: %s',
                     popup_data['bill'])
        tally_log_ids = []
        bill_count = 0
        for rec in popup_data['bill']:
            try:
                _logger.info('@ Received data to create bills from Tally to Odoo: %s', rec)
                purchase_id = request.env['purchase.order'].sudo().search(
                    [('tally_po_name', '=', rec['tally_po_name'])])
                if purchase_id.picking_ids and not purchase_id.invoice_ids:
                    purchase_id.sudo().action_create_invoice()
                # Checking the purchase lines and the newly received bills
                # line from tally and updating the quantity,price and account
                if purchase_id.invoice_ids:
                    names = purchase_id.invoice_ids.name
                    for line in rec['invoice_line_ids']:
                        account_id = request.env['account.account'].sudo().search(
                            [('tally_id', '=', line['account_id'])])
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])], limit=1)
                        for res in purchase_id.invoice_ids:
                            if purchase_id.invoice_ids.state == 'draft':
                                for invoice_line in res.invoice_line_ids:
                                    if invoice_line.product_id == product_id.id:
                                        invoice_line.sudo().write({
                                            'quantity': line['quantity'],
                                            'price_unit': float(line['price_unit']),
                                            'account_id': account_id.id
                                        })
                                    # else:
                                    #     invoice_line.sudo().update({
                                    #         'product_id': product_id.id,
                                    #         'quantity': line['quantity'],
                                    #         'price_unit': float(line['price_unit']),
                                    #         'account_id': account_id.id
                                    #     })
                                date = datetime.strptime(rec['invoice_date'], '%d-%m-%Y')
                                date_val = date.strftime('%Y-%m-%d')
                                purchase_id.invoice_ids.sudo().write({
                                    'tally_bill_id': rec['tally_bill_id'],
                                    'invoice_date': date_val,
                                    'date': date_val,
                                    'invoice_date_due': date_val,
                                    'tally_bill_name': rec['tally_bill_name'],
                                    'tally_po_id': rec['tally_po_id'],
                                })
                            purchase_id.invoice_ids.action_post()
                            bill_count += 1
                            if module.state == 'installed':
                                vals = (0, 0, {
                                    'master_type': 'in_invoice',
                                    'sync_action': 'create',
                                    'sync_data': str(rec),
                                    'error_data': 'Purchase bills created successfully',
                                    'name': names,
                                    'sync_status': 'done',
                                    'sync_for': 'trans',
                                    'records_created_id': purchase_id.invoice_ids.id,
                                    'tally_record_id': rec['tally_po_id']
                                })
                                tally_log_ids.append(vals)
                if not purchase_id:
                    tally_bill_ids = request.env['account.move'].sudo().search(
                        [('tally_bill_id', '=', rec['tally_bill_id']),
                         ('move_type', '=', 'in_invoice')])
                    vendor_id = request.env['res.partner'].sudo().search([
                        ('tally_id', '=', int(rec['partner_id']))])

                    if not vendor_id:
                        country_id = request.env['res.country'].sudo().search([
                            ('name', '=', str(rec['country']))], limit=1)
                        state_id = request.env['res.country.state'].sudo().search([
                            ('name', '=', str(rec['state']))], limit=1)
                        vendor_id = request.env['res.partner'].sudo().create({
                            'name': rec['partner_name'],
                            'type_partner': 'supplier',
                            'tally_id': int(rec['partner_id']),
                            'street': rec['street'] if rec['street'] != 'NULL' else '',
                            'email': rec['email'] if rec['email'] != 'NULL' else '',
                            'vat': rec['vat'],
                            'state_id': state_id.id or '',
                            'country_id': country_id.id or '',
                            'company_id': company_id.id
                        })
                    if not tally_bill_ids:
                        line_item = []
                        for line in rec['invoice_line_ids']:
                            account_id = request.env['account.account'].sudo().search(
                                [('tally_id', '=', int(line['account_id']))], limit=1)
                            product_id = request.env['product.product'].sudo().search(
                                [('tally_id', '=', line['product_id'])], limit=1)
                            tax_val = []
                            if 'tax_ids' in line:
                                for tax in line['tax_ids']:
                                    tax_name = tax['name'] + ' ' + str(tax['amount']) + ' ' + '%'
                                    account_tax = request.env['account.tax'].sudo().search(
                                        [('name', '=', str(tax_name)),
                                         ('type_tax_use', '=', 'purchase')], limit=1)
                                    if not account_tax:
                                        account_tax = request.env['account.tax'].sudo().create({
                                            'name': str(tax_name),
                                            'amount': float(tax['amount']),
                                            'country_id': company_id.country_id.id,
                                            'type_tax_use': 'purchase',
                                            'amount_type': 'percent'
                                        })
                                    tax_val.append(account_tax.id)
                            if line['is_has_product'] == 'Yes':
                                vals = {
                                    'product_id': product_id.id,
                                    'name': line['name'],
                                    'account_id': account_id.id,
                                    'price_unit': float(line['price_unit']),
                                    'discount': float(line['discount']),
                                    'quantity': float(line['quantity']),
                                    'tax_ids': tax_val
                                }
                                line_item.append((0, 0, vals))
                            else:
                                vals = {
                                    'name': line['name'],
                                    'account_id': account_id.id,
                                    'price_unit': float(line['price_unit']),
                                    'quantity': float(line['quantity']),
                                }
                                line_item.append((0, 0, vals))
                        if line_item:
                            date = datetime.strptime(rec['invoice_date'], '%d-%m-%Y')
                            date_val = date.strftime('%Y-%m-%d')
                            purchase_bill = request.env['account.move'].sudo().create({
                                'move_type': 'in_invoice',
                                'partner_id': vendor_id.id,
                                'invoice_date': date_val,
                                'date': date_val,
                                'tally_bill_id': rec['tally_bill_id'],
                                'tally_bill_name': rec['tally_bill_name'],
                                'tally_po_id': rec['tally_po_id'],
                                'invoice_line_ids': line_item})
                            purchase_bill.write({'picking_type_id': self._get_stock_type_ids(purchase_bill)})
                            purchase_bill.action_post()
                            purchase_bill.action_stock_receive()
                            bill_count += 1
                            if module.state == 'installed':
                                vals = (0, 0, {
                                    'master_type': 'in_invoice',
                                    'sync_action': 'create',
                                    'sync_data': str(rec),
                                    'error_data': 'purchase bill has been created',
                                    'name': purchase_bill.name,
                                    'sync_status': 'done',
                                    'sync_for': 'trans',
                                    'tally_record_name': rec['tally_bill_name'],
                                    'records_created_id': purchase_bill.id,
                                    'tally_record_id': rec['tally_bill_id']
                                })
                                tally_log_ids.append(vals)
                                _logger.info('Log line Created...: %s', rec['tally_bill_name'])
            except Exception as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'in_invoice',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_bill_name'],
                        'tally_record_id': rec['tally_bill_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        # status = ''
        _logger.info('@ Number of bills imported: %s', bill_count)
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
                        created_records.append(("TALLY ID : " + str(rec.tally_record_id) +
                                                " - " + "ODOO ID : " + str(
                            rec.records_created_id)))
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
