""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating account groups.
    It includes methods for processing Tally data and updating Odoo records accordingly. """

    def group_account_type(self, line):
        """ The Account Type of Chat of Account gets from this function"""
        if line['account_type'] == 'Receivable':
            key_type = 'asset_receivable'
        elif line['account_type'] == 'Bank and Cash':
            key_type = 'asset_cash'
        elif line['account_type'] == 'Current Assets':
            key_type = 'asset_current'
        elif line['account_type'] == 'Non-current Assets':
            key_type = 'asset_non_current'
        elif line['account_type'] == 'Prepayments':
            key_type = 'asset_prepayments'
        elif line['account_type'] == 'Fixed Assets':
            key_type = 'asset_fixed'
        elif line['account_type'] == 'Payable':
            key_type = 'liability_payable'
        elif line['account_type'] == 'Credit Card':
            key_type = 'liability_credit_card'
        elif line['account_type'] == 'Current Liabilities':
            key_type = 'liability_current'
        elif line['account_type'] == 'Non-current Liabilities':
            key_type = 'liability_non_current'
        elif line['account_type'] == 'Equity':
            key_type = 'equity'
        elif line['account_type'] == 'Current Year Earnings':
            key_type = 'equity_unaffected'
        elif line['account_type'] == 'Income':
            key_type = 'income'
        elif line['account_type'] == 'Other Income':
            key_type = 'income_other'
        elif line['account_type'] == 'Expenses':
            key_type = 'expense'
        elif line['account_type'] == 'Depreciation':
            key_type = 'expense_depreciation'
        elif line['account_type'] == 'Cost of Revenue':
            key_type = 'expense_direct_cost'
        elif line['account_type'] == 'Off-Balance Sheet':
            key_type = 'off_balance'
        return key_type


    @validate_token
    @http.route("/api/create/journals", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_journals(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing journal entries from tally to odoo %s', popup_data)
        if 'journals' not in popup_data:
            _logger.info('@The Tally system does not contain any journals.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['journals']),
            'tally_data': popup_data,
            'tally_entry_type': 'entry'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        entries_count = 0
        _logger.info('@ Total Received data to create journals from Tally to Odoo: %s',
                     popup_data['journals'])
        tally_log_ids = []
        for rec in popup_data['journals']:
            try:
                entries_count += 1
                tally_journal_ids = request.env['account.move'].sudo().search([
                    ('tally_journal_id', '=', rec['tally_journal_id']),
                    ('move_type', 'not in', ('out_refund','in_refund','out_invoice','in_invoice'))])
                if not tally_journal_ids:
                    line_item = []
                    for line in rec['invoice_line_ids']:
                        partner_id = None
                        account_id = None
                        if 'partner_id' in line :
                            partner_id = request.env['res.partner'].sudo().search(
                                [('tally_id', '=', line['partner_id'])],
                                limit=1)
                            default_property_account = (request.env['ppts.tally.integration'].
                                        sudo().search([('is_active', '=', True)], limit=1))
                            _logger.info('@  SELECTED PARTNER FOR THE RECORD CREATION %s',
                                         line['partner_id'])
                            if not partner_id:
                                partner_id = request.env['res.partner'].sudo().create({
                                    'name': line['partner_name'],
                                    'type_partner': 'customer',
                                    'tally_id': int(line['partner_id']),
                                    'property_account_receivable_id':
                                        default_property_account.property_recieveable.id,
                                    'property_account_payable_id':
                                        default_property_account.property_payable.id,
                                    'company_id': company_id
                                })
                            property_receviable_id = ''
                            property_payable_id = ''
                            #-------------------------------------------------------------------
                            # If the customer is already in Odoo, take the receivable and       |
                            #       payable and take it for the journal entry creation          |
                            # If the receivable/payable is set, take from the customer and      |
                            #       if not take from the configuration                          |
                            #-------------------------------------------------------------------|
                            if partner_id.type_partner == 'customer':
                                property_receviable_id = partner_id.property_account_receivable_id
                                if not property_receviable_id:
                                    property_receviable_id = (
                                        default_property_account.property_recieveable)
                            elif partner_id.type_partner == 'supplier':
                                property_payable_id = partner_id.property_account_payable_id
                                if not property_payable_id:
                                    property_payable_id = default_property_account.property_payable
                            if property_receviable_id:
                                account_id = property_receviable_id.id
                                _logger.info('@  property_receviable_id %s', account_id)
                            if property_payable_id:
                                account_id = property_payable_id.id
                                _logger.info('@  property_payable_id %s', account_id)
                            _logger.info('@  account_id %s', account_id)
                        else:
                            account_id = request.env['account.account'].sudo().search(
                                [('tally_id', '=', int(line['account_id']))], limit=1).id
                            if not account_id:
                                account_id = request.env['account.account'].sudo().search(
                                [('tally_id', '=', int(line['group_id']))], limit=1).id
                                if not account_id:
                                    account_type = self.group_account_type(line)
                                    account_id = request.env['account.account'].sudo().create({
                                        'code': line['group_id'] + line['account_id'],
                                        'name': line['group_name'],
                                        'account_type': account_type,
                                        'tally_group_id': int(line['account_group']),
                                        'company_id': company_id,
                                        'tally_id': line['group_id']
                                    })
                                    _logger.info('@  NEW ACCOUNT ID : account_id %s', account_id)

                        if account_id:
                            if 'debit' in line:
                                debit_amount = float(line['debit'])
                            else:
                                debit_amount = 0.0

                            if 'credit' in line:
                                credit_amount = float(line['credit'])
                            else:
                                credit_amount = 0.0

                            vals = (0, 0, {
                                'account_id': account_id,
                                'partner_id': partner_id.id if partner_id else '',
                                'name': line['name'],
                                'credit': credit_amount,
                                'debit': debit_amount
                            })
                            line_item.append(vals)
                    if line_item:
                        account_journal = request.env['account.journal'].sudo().search([
                            ('name', '=', rec['journal_name'])],limit=1)
                        date = datetime.strptime(rec['date'], '%d-%m-%Y')
                        date_val = date.strftime('%Y-%m-%d')
                        journal_entries = request.env['account.move'].sudo().create({
                            'move_type': 'entry',
                            'date': date_val,
                            'journal_id': account_journal.id,
                            'tally_journal_id': rec['tally_journal_id'],
                            'tally_journal_name': str(rec['tally_journal_name']),
                            'invoice_line_ids': line_item
                        })
                        journal_entries.action_post()
                        if module.state == 'installed':
                            vals = (0, 0,{
                                'master_type': 'entry',
                                'sync_action': 'create',
                                'sync_data': str(rec),
                                'error_data': 'journal entries has been created',
                                'name': journal_entries.name,
                                'sync_status': 'done',
                                'sync_for': 'trans',
                                'tally_record_name': rec['tally_journal_name'],
                                'records_created_id': journal_entries.id,
                                'tally_record_id': rec['tally_journal_id']
                            })
                            tally_log_ids.append(vals)
                            # _logger.info('Log line Created...:%s', journal_entries.name)
                    # _logger.info('@ Number of invoice imported: %s', entries_count)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                _logger.info('@ GETTING THE ISSUE ON THE EXCEPTION')
                if module.state == 'installed':
                    vals = (0,0,{
                        'master_type': 'entry',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_journal_name'],
                        'tally_record_id': rec['tally_journal_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
        if tally_log_ids:
            vals = {
                'data_from': 'tally',
                'company_id': company_id,
                'trans_log_line_ids':tally_log_ids
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
