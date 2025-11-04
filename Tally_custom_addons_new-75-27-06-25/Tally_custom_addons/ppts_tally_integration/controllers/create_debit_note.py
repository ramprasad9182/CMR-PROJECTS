""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating debit note.
    It includes methods for processing Tally data and creating Odoo records accordingly. """
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
    @http.route("/api/create/debit_note", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_debit_note(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing credit note from tally to odoo %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        if 'debit_note' not in popup_data:
            _logger.info('@The Tally system does not contain any debit note.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['debit_note']),
            'tally_data': popup_data,
            'tally_entry_type': 'in_refund'
        })
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        _logger.info('@ Total Received data to create debit note from Tally to Odoo: %s',
                     popup_data['debit_note'])
        tally_log_ids = []
        debit_count = 0
        for rec in popup_data['debit_note']:
            try:
                tally_debit_ids = request.env['account.move'].sudo().search(
                    [('tally_debit_id', '=', rec['tally_debit_id'])])
                customer_id = request.env['res.partner'].sudo().search([
                    ('tally_id', '=', int(rec['partner_id']))], limit=1)
                if customer_id and not tally_debit_ids:
                    line_item = []
                    for line in rec['invoice_line_ids']:
                        if 'partner_id' in line:
                            partner_id = request.env['res.partner'].sudo().search(
                                [('tally_id', '=', line['partner_id'])],
                                limit=1)
                            if partner_id.type_partner == 'customer':
                                account_id = request.env['account.account'].sudo().search(
                                    [('id', '=', partner_id.property_account_receivable_id.id)],
                                    limit=1)
                            elif partner_id.type_partner == 'supplier':
                                account_id = request.env['account.account'].sudo().search(
                                    [('id', '=', partner_id.property_account_payable_id.id)],
                                    limit=1)
                        else:
                            account_id = request.env['account.account'].sudo().search(
                                [('tally_id', '=', int(line['account_id']))], limit=1)
                        product_id = request.env['product.product'].sudo().search(
                            [('tally_id', '=', line['product_id'])], limit=1)
                        tax_val = []
                        if 'tax_ids' in line:
                            for tax in line['tax_ids']:
                                account_tax = request.env['account.tax'].sudo().search(
                                    [('name', '=', tax['name']), ('type_tax_use', '=', 'sale')],
                                    limit=1)
                                if not account_tax:
                                    account_tax = request.env['account.tax'].sudo().create({
                                        'name': tax['name'],
                                        'amount': float(tax['amount']),
                                        'country_id': company_id.country_id.id,
                                        'type_tax_use': 'sale',
                                        'amount_type': 'percent'
                                    })
                                tax_val.append(account_tax.id)
                        if line['is_has_product'] == 'Yes':
                            vals = (0, 0, {
                                'product_id': product_id.id,
                                'name': line['name'],
                                'account_id': account_id.id,
                                'price_unit': float(line['price_unit']),
                                'discount': float(line['discount']),
                                'quantity': float(line['quantity']),
                                'tax_ids': tax_val
                            })
                            line_item.append(vals)
                        else:
                            vals = (0, 0, {
                                'name': line['name'],
                                'account_id': account_id.id,
                                'price_unit': float(line['price_unit']),
                                'quantity': float(line['quantity']),
                            })
                            line_item.append(vals)
                    if line_item:
                        date = datetime.strptime(rec['invoice_date'], '%d-%m-%Y')
                        date_val = date.strftime('%Y-%m-%d')
                        debit_note = request.env['account.move'].sudo().create({
                            'move_type': 'in_refund',
                            'partner_id': customer_id.id,
                            'invoice_date': date_val,
                            'date': date_val,
                            'ref': rec['ref'],
                            'tally_debit_id': rec['tally_debit_id'],
                            'tally_debit_name': rec['tally_debit_name'],
                            'invoice_line_ids': line_item
                        })
                        debit_note.write({'picking_type_id': self._get_stock_type_ids(debit_note)})
                        debit_note.action_post()
                        debit_note.action_stock_transfer()
                        debit_count += 1
                        if module.state == 'installed':
                            vals = (0, 0, {
                                'master_type': 'in_refund',
                                'sync_action': 'create',
                                'sync_data': str(rec),
                                'error_data': 'Debit Note has been created',
                                'name': debit_note.name,
                                'sync_status': 'done',
                                'sync_for': 'trans',
                                'tally_record_name': rec['tally_debit_name'],
                                'records_created_id': debit_note.id,
                                'tally_record_id': rec['tally_debit_id']
                            })
                            tally_log_ids.append(vals)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'in_refund',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_debit_name'],
                        'tally_record_id': rec['tally_debit_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        # status = ''
        _logger.info('@ Number of invoice imported: %s', debit_count)
        if tally_log_ids:
            vals = {
                'data_from': 'tally',
                'company_id': company_id.id,
                'trans_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(vals)
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
