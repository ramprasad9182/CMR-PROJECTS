""" APIController class for handling Tally integration in Odoo."""
import json
import logging
import psycopg2
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
    @http.route("/api/create/sale_invoices", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_sale_invoices(self, **post):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing sale Invoice from tally to odoo %s' % popup_data)
        if 'invoices' not in popup_data:
            _logger.info('@The Tally system does not contain any sale invoices.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['invoices']),
            'tally_data': popup_data,
            'tally_entry_type': 'out_invoice'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id

        module = request.env['ir.module.module'].sudo().search([('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s' % start_date)
        _logger.info('@ Total Received data to create invoice from Tally to Odoo: %s',
                     popup_data['invoices'])
        tally_log_ids = []
        invoice_count = 0
        for rec in popup_data['invoices']:
            try:
                _logger.info('@ Received data to create invoices from Tally to Odoo: %s', rec)
                sale_id = request.env['sale.order'].sudo().search(
                    [('tally_so_name', '=', rec['tally_so_name'])])
                if sale_id.picking_ids and not sale_id.invoice_ids:
                    sale_id.sudo()._create_invoices()
                # checking the Sale line and the newly recieved invoice line from
                # tally and updating the quantity,price and account
                if sale_id.invoice_ids:
                    names = sale_id.name
                    for line in rec['invoice_line_ids']:
                        account_id = request.env['account.account'].sudo().search(
                            [('tally_id', '=', line['account_id'])])
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])], limit=1)
                        for res in sale_id.invoice_ids:
                            if res.state == 'draft':
                                for invoice_line in res.invoice_line_ids:
                                    if invoice_line.product_id == product_id.id:
                                        invoice_line.sudo().write({
                                            'quantity': line['quantity'],
                                            'price_unit': float(line['price_unit']),
                                            'account_id': account_id.id
                                        })
                                    else:
                                        # Since there is no product create the same product on the PO
                                        # lines first and the add on the account.move.line
                                        continue
                                invoice_count += 1
                                if module.state == 'installed':
                                    vals = (0, 0, {
                                        'master_type': 'out_invoice',
                                        'sync_action': 'create',
                                        'error_data': 'Invoice created successfully',
                                        'name': names,
                                        'sync_status': 'done',
                                        'sync_for': 'trans',
                                    })
                                    tally_log_ids.append(vals)
                if not sale_id:
                    tally_invoice_ids = request.env['account.move'].sudo().search(
                        [('tally_invoice_id', '=', rec['tally_invoice_id']),
                         ('move_type', '=', 'out_invoice')])
                    customer_id = request.env['res.partner'].sudo().search([
                        ('tally_id', '=', int(rec['partner_id']))], limit=1)
                    if not customer_id:
                        country_id = request.env['res.country'].sudo().search([
                            ('name', '=', str(rec['country']))], limit=1)
                        state_id = request.env['res.country.state'].sudo().search([
                            ('name', '=', str(rec['state']))], limit=1)
                        customer_id = request.env['res.partner'].sudo().create({
                            'name': rec['partner_name'],
                            'type_partner': 'customer',
                            'tally_id': int(rec['partner_id']),
                            'street': rec['street'] if rec['street'] != 'NULL' else '',
                            'email': rec['email'] if rec['email'] != 'NULL' else '',
                            'vat': rec['vat'],
                            'state_id': state_id.id or '',
                            'country_id': country_id.id or '',
                            'company_id': company_id.id
                        })
                    if not tally_invoice_ids:
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
                                        [('name', '=', str(tax_name)), ('type_tax_use', '=', 'sale')], limit=1)
                                    if not account_tax:
                                        account_tax = request.env['account.tax'].sudo().create({
                                            'name': str(tax_name),
                                            'amount': float(tax['amount']),
                                            'country_id': company_id.country_id.id,
                                            'type_tax_use': 'sale',
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
                            sale_invoices = request.env['account.move'].sudo().create({
                                'move_type': 'out_invoice',
                                'partner_id': customer_id.id,
                                'invoice_date': date_val,
                                'date': date_val,
                                'tally_invoice_id': rec['tally_invoice_id'],
                                'tally_invoice_name': rec['tally_invoice_name'],
                                'tally_so_id': rec['tally_so_id'],
                                'invoice_line_ids': line_item
                            })
                            invoice_count += 1
                            sale_invoices.write({'picking_type_id': self._get_stock_type_ids(sale_invoices)})
                            sale_invoices.action_post()
                            sale_invoices.action_stock_transfer()
                            if module.state == 'installed':
                                vals = (0, 0, {
                                    'master_type': 'out_invoice',
                                    'sync_action': 'create',
                                    'sync_data': str(rec),
                                    'error_data': 'Sale Invoice has been created',
                                    'name': sale_invoices.name,
                                    'sync_status': 'done',
                                    'sync_for': 'trans',
                                    'tally_record_name': rec['tally_invoice_name']
                                })
                                tally_log_ids.append(vals)
                                _logger.info('Log line Created...')
            except psycopg2.DatabaseError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'out_invoice',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_invoice_name']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s' % tally_log_ids)
        _logger.info('@ Number of invoice imported: %s' % invoice_count)
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
            # total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.trans_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : " + str(rec.tally_record_id) + " - " + "ODOO ID : " + str(
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
