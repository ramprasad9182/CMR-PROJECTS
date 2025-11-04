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

    def group_account_type(self, rec):
        """ The Account Type of Chat of Account gets from this function"""
        if rec['account_type'] == 'Receivable':
            key_type = 'asset_receivable'
        elif rec['account_type'] == 'Bank and Cash':
            key_type = 'asset_cash'
        elif rec['account_type'] == 'Current Assets':
            key_type = 'asset_current'
        elif rec['account_type'] == 'Non-current Assets':
            key_type = 'asset_non_current'
        elif rec['account_type'] == 'Prepayments':
            key_type = 'asset_prepayments'
        elif rec['account_type'] == 'Fixed Assets':
            key_type = 'asset_fixed'
        elif rec['account_type'] == 'Payable':
            key_type = 'liability_payable'
        elif rec['account_type'] == 'Credit Card':
            key_type = 'liability_credit_card'
        elif rec['account_type'] == 'Current Liabilities':
            key_type = 'liability_current'
        elif rec['account_type'] == 'Non-current Liabilities':
            key_type = 'liability_non_current'
        elif rec['account_type'] == 'Equity':
            key_type = 'equity'
        elif rec['account_type'] == 'Current Year Earnings':
            key_type = 'equity_unaffected'
        elif rec['account_type'] == 'Income':
            key_type = 'income'
        elif rec['account_type'] == 'Other Income':
            key_type = 'income_other'
        elif rec['account_type'] == 'Expenses':
            key_type = 'expense'
        elif rec['account_type'] == 'Depreciation':
            key_type = 'expense_depreciation'
        elif rec['account_type'] == 'Cost of Revenue':
            key_type = 'expense_direct_cost'
        elif rec['account_type'] == 'Off-Balance Sheet':
            key_type = 'off_balance'
        return key_type


    @validate_token
    @http.route("/api/create/account_coa", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_account_coa(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing COA from tally to odoo %s', popup_data)
        if 'account_coa' not in popup_data:
            _logger.info('@The Tally system does not contain any chat of account.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries':len(popup_data['account_coa']),
            'tally_data':popup_data,
            'tally_entry_type': 'coa'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s',start_date)
        coa_count = 0
        _logger.info('@ The Accounting Master Creating COA: %s',popup_data['account_coa'])
        tally_log_ids = []
        for rec in popup_data['account_coa']:
            try:
                coa_count += 1
                account_id = request.env['account.account'].sudo().search([
                    ('tally_id', '=', rec['tally_id'])],limit=1)
                account_type = self.group_account_type(rec)
                if not account_id:
                    group = request.env['account.group'].sudo().search(
                        [('tally_id', '=', rec['group_id'])], limit=1)
                    if group:
                        tax_val = []
                        if 'tax_ids' in rec:
                            for tax in rec['tax_ids']:
                                account_tax = request.env['account.tax'].sudo().search([
                                    ('name', '=', tax['name']),
                                    ('type_tax_use', '=', 'sale')], limit=1)
                                tax_id = False
                                if not account_tax:
                                    tax_id = request.env['account.tax'].sudo().create({
                                        'name': tax['name'],
                                        'amount': float(tax['amount']),
                                        'country_id': company_id.country_id.id,
                                        'type_tax_use': 'sale',
                                        'amount_type': 'percent'
                                    })
                                    request.env.cr.commit()
                                    tax_val.append(tax_id.id)
                                tax_val.append(account_tax.id)
                        if not rec['is_tax'] == 'No':
                            account = request.env['account.account'].sudo().create({
                                'code': rec['group_id'] + rec['tally_id'],
                                'name': rec['name'],
                                'account_type': account_type,
                                'group_id': group.id,
                                'company_id': company_id.id,
                                'tally_id': rec['tally_id']
                            })
                        else:
                            account = request.env['account.account'].sudo().create({
                                'code': rec['group_id'] + rec['tally_id'],
                                'name': rec['name'],
                                'account_type': account_type,
                                'group_id': group.id,
                                'is_tax': bool(rec['is_tax']),
                                'types_tax': rec['types_tax'],
                                'tax_ids': tax_val,
                                'company_id': company_id.id,
                                'tally_id': rec['tally_id']
                            })
                        if group:
                            account.sudo().update({
                                'group_id': group.id,
                                'tally_group_id': group.name
                            })
                        if module.state == 'installed':
                            vals = (0, 0, {
                                'master_type': 'coa',
                                'sync_action': 'create',
                                'error_data': 'COA Has been Successfully Created',
                                'name': account.name,
                                'sync_status': 'done',
                                'sync_for': 'master',
                                'sync_data': str(rec),
                                'tally_record_name': rec['name'],
                                'records_created_id': account.id,
                                'tally_record_id': rec['tally_id']
                            })
                            tally_log_ids.append(vals)
                if account_id:
                    group = request.env['account.group'].sudo().search(
                        [('tally_id', '=', rec['group_id'])], limit=1)
                    if group:
                        account_id.sudo().update({
                            'group_id': group.id,
                            'tally_group_id': group.name
                        })
                _logger.info('@ Number of coa imported: %s',coa_count)
            except ImportError as e:
                # info = "There was a problem {%s}", e
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'coa',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'tally_record_name': rec['name'],
                        'tally_record_id': rec['tally_id']
                    })
                    tally_log_ids.append(vals)
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id.id,
                'master_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s',tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
            # total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : "
                                                + str(rec.tally_record_id)
                                                + " - " + "ODOO ID : "
                                                + str(rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'fail':
                        failed_records.append(rec.tally_record_name)

            return {
                'status': str(status),
                'created_records': str(created_records),
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return None
