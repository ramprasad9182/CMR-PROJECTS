""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating In Payment.
    It includes methods for processing Tally data and updating Odoo records accordingly. """

    # def in_payment_reconcile_add(self, payments, rec):
    #     """."""
    #     for line in list(rec['tally_bill_ids']):
    #         if not payments.filtered(lambda x: x.state == 'posted'):
    #             _logger.info('@ ODOO Payment record is not posted : %s', payments.name)
    #             continue
    #         account_move = request.env['account.move'].sudo().search([
    #             ('tally_bill_id', '=', line), ('payment_state', '=', 'not_paid'),
    #             ('state', '=', 'posted')])
    #         credit_aml = payments.invoice_line_ids.filtered('debit')
    #         if (credit_aml.credit < account_move.amount_residual
    #                 and len(list(rec['tally_bill_ids'])) != 1):
    #             _logger.info('@ ODOO Vendor Payment Record: %s and '
    #                          'Tally Vendor Payment Record: %s',
    #                          payments.name, payments.tally_payment_name)
    #             continue
    #         if account_move:
    #             account_move.js_assign_outstanding_line(credit_aml.id)
    #             _logger.info('@ Odoo vendor bill %s is reconcile with %s payment.',
    #                          account_move.name, payments.name)
    #         else:
    #             _logger.info('@ The vendor bill in Tally has not been updated to '
    #                          'match the bill record in Odoo.')

    def in_payment_reconcile_add(self, payments, rec):
        """The purchase payment are reconcile with the tally bill voucher number."""
        data = []
        curr_pool = request.env['res.currency']
        amount = 0
        payments.sudo().action_draft()
        payments.dev_invoice_line_ids.unlink()
        for pay in payments.dev_invoice_line_ids:
            amount += pay.allocation
        if amount > payments.amount:
            _logger.info("@ Allocation Amount is must be lesser than '%s'", payments.amount)
        if not amount > payments.amount:
            for line in list(rec['tally_bill_ids']):
                account_move = request.env['account.move'].sudo().search([
                    ('tally_bill_name', '=', line['tally_name']),
                    ('payment_state', 'in', ('not_paid', 'partial')),
                    ('partner_id', '=', payments.partner_id.id),
                    ('state', '!=', 'paid')], limit=1)
                if not account_move:
                    _logger.info('@ Nothing to reconcile:%s', payments.name)
                    continue
                original_amount = account_move.amount_total
                balance_amount = account_move.amount_residual
                if account_move.currency_id.id != payments.currency_id.id:
                    original_amount = account_move.amount_total
                    balance_amount = account_move.amount_residual
                    if account_move.currency_id.id != payments.currency_id.id:
                        currency_id = payments.currency_id.with_context(date=payments.date)
                        original_amount = curr_pool._compute(account_move.currency_id, currency_id,
                                                             original_amount, round=True)
                        balance_amount = curr_pool._compute(account_move.currency_id, currency_id,
                                                            balance_amount, round=True)
                full_reconcile = ''
                allocation = - float(line['reconcile_amount'])
                if float(line['reconcile_amount']):
                    if allocation >= balance_amount:
                        full_reconcile = True
                        allocation = balance_amount
                    else:
                        full_reconcile = False
                if allocation > float(rec['amount']):
                    _logger.info('@ The allocation amount %s grater then of Payment amount %s',
                                 allocation, rec['amount'])
                    continue
                data.append((0, 0, {
                    'invoice_id': account_move.id,
                    'account_id': account_move.partner_id.property_account_payable_id.id,
                    'date': account_move.invoice_date,
                    'due_date': account_move.invoice_date_due,
                    'full_reconcile': full_reconcile,
                    'allocation': allocation,
                    'original_amount': original_amount,
                    'balance_amount': balance_amount,
                    'currency_id': payments.currency_id.id,
                    'account_payment_id': payments.id
                }))
        payments.sudo().update({'dev_invoice_line_ids': data})
        payments.sudo().action_post()

    @validate_token
    @http.route("/api/create/in_payments", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_in_payments(self):
        popup_data = json.loads(request.httprequest.data)
        if 'payments' not in popup_data:
            _logger.info('@The Tally system does not contain any vendor payment.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['payments']),
            'tally_data': popup_data,
            'tally_entry_type': 'in_payment'
        })
        _logger.info('Importing Vendor Payments from tally to odoo %s', popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        payments_count = 0
        _logger.info('@ Total Received data to create payments from Tally to Odoo: %s',
                     popup_data['payments'])
        tally_log_ids = []
        for rec in popup_data['payments']:
            try:
                payments = request.env['account.payment'].sudo().search([
                    ('tally_payment_id', '=', rec['tally_payment_id']),
                    ('payment_type', '=', 'outbound')], limit=1)
                partner_id = request.env['res.partner'].sudo().search([
                    ('tally_id', '=', rec['partner_id'])], limit=1)
                account_journal = request.env['account.journal'].sudo().search([
                    ('name', '=', rec['journal_name'])], limit=1)
                if not account_journal:
                    _logger.info('@The tally payment %s is not import in odoo.'
                                 'The "%s" journal name not match with odoo journal name.',
                                 rec['tally_payment_name'], rec['journal_name'])
                    continue
                date = datetime.strptime(rec['payment_date'], '%d-%m-%Y')
                date_val = date.strftime('%Y-%m-%d')
                if rec['is_check'] == "Yes":
                    check_date = datetime.strptime(rec['check_date'], '%d-%m-%Y')
                    check_date_val = check_date.strftime('%Y-%m-%d')
                else:
                    check_date_val = False
                if not payments:
                    payments_count += 1
                    account_payment = request.env['account.payment'].sudo().create({
                        'partner_id': partner_id.id,
                        'date': date_val,
                        'amount': rec['amount'],
                        'ref': rec['ref'],
                        'payment_type': 'outbound',
                        'partner_type': 'supplier',
                        'journal_id': account_journal.id,
                        'tally_payment_id': rec['tally_payment_id'],
                        'tally_payment_name': rec['tally_payment_name'],
                        'check_date': check_date_val or False,
                        'is_check': rec['is_check']
                    })
                    account_payment.action_post()
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'in_payment',
                            'sync_action': 'create',
                            'sync_data': str(rec),
                            'error_data': 'Vendor Payment has been created',
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
                        'partner_id': partner_id.id,
                        'date': date_val,
                        'amount': rec['amount'],
                        'ref': rec['ref'],
                        'journal_id': account_journal.id,
                        'check_date': check_date_val or False,
                        'is_check': rec['is_check']
                    })
                if 'tally_bill_ids' in rec:
                    self.in_payment_reconcile_add(payments, rec)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'in_payment',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_payment_id'],
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
