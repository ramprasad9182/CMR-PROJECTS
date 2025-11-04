""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating payment internal Transfer.
        It includes methods for processing Tally data and updating Odoo records accordingly. """
    @validate_token
    @http.route("/api/create/payment_internal_transfer", type="json", auth="public",
                methods=["POST"], csrf=False)
    def _api_create_payment_internal_transfer(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Data Received from tally to create payment internal transfer %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        if 'payment_transfer' not in popup_data:
            _logger.info('@The Tally system does not contain any payment transfer.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['payment_transfer']),
            'tally_data': popup_data,
            'tally_entry_type': 'payment_transfer'
        })
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        _logger.info('@ Total Received data to create payment internal transfer from Tally to Odoo: %s',
                     popup_data['payment_transfer'])
        tally_log_ids = []
        payments_count = 0
        for rec in popup_data['payment_transfer']:
            try:
                payments_count += 1
                payments = request.env['account.payment'].sudo().search([
                    ('tally_payment_id', '=', rec['tally_payment_id']), ('is_internal_transfer', '=', True)], limit=1)
                account_journal = request.env['account.journal'].sudo().search([
                    ('name', '=', rec['from_journal_name'])], limit=1)
                destination_journal_id = request.env['account.journal'].sudo().search([
                    ('name', '=', rec['to_journal_name'])], limit=1)
                if not account_journal:
                    _logger.info('Missing the source journal name : %s', rec['from_journal_name'])
                    continue
                if not destination_journal_id:
                    _logger.info('Missing the destination journal name: %s', rec['to_journal_name'])
                    continue
                date = datetime.strptime(rec['payment_date'], '%d-%m-%Y')
                date_val = date.strftime('%Y-%m-%d')
                if rec['is_check'] == "Yes":
                    check_date = datetime.strptime(rec['check_date'], '%d-%m-%Y')
                    check_date_val = check_date.strftime('%Y-%m-%d')
                else:
                    check_date_val = False
                if not payments:
                    account_payment = request.env['account.payment'].sudo().create({
                        'date': date_val,
                        'amount': rec['amount'],
                        'ref': rec['ref'],
                        'is_internal_transfer': True,
                        'journal_id': account_journal.id,
                        'destination_journal_id': destination_journal_id.id,
                        'tally_payment_id': rec['tally_payment_id'],
                        'tally_payment_name': rec['tally_payment_name'],
                        'check_date': check_date_val or False,
                        'is_check': rec['is_check']
                    })
                    account_payment.action_post()
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'payment_transfer',
                            'sync_action': 'create',
                            'sync_data': str(rec),
                            'error_data': 'Internal Payment Transfer has been created',
                            'name': account_payment.name,
                            'sync_status': 'done',
                            'sync_for': 'trans',
                            'tally_record_name': rec['tally_payment_name'],
                            'records_created_id': account_payment.id,
                            'tally_record_id': rec['tally_payment_id']
                        })
                        tally_log_ids.append(vals)
                        _logger.info('Log line Created...:%s', account_payment.name)
                    _logger.info('@ Number of payments imported: %s', payments_count)
                else:
                    payments.sudo().update({
                        'date': date_val,
                        'amount': rec['amount'],
                        'ref': rec['ref'],
                        'journal_id': account_journal.id,
                        'destination_journal_id': destination_journal_id.id,
                        'check_date': check_date_val or False,
                        'is_check': rec['is_check']
                    })
            except ImportError as e:
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'payment_transfer',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_payment_name'],
                        'tally_record_id': rec['tally_payment_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id,
                'trans_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s', tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
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
