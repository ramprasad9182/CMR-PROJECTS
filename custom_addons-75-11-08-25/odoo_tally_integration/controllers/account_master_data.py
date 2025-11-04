# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request,Response
import logging


_logger = logging.getLogger(__name__)

class GETAccounts(http.Controller):

    @http.route('/odoo/api/get_accounts_json_data', type='http', auth='public', methods=['GET'])
    def get_accounts_json_data(self, **kwargs):
        # Fetch active Tally Integration record
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])
        print(integration)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message":"Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        # Check if API key is valid (assuming it's passed as a query param)
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('api_key')
        print(api_key)
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message":"Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        # Check if 'account_group' checkbox is enabled
        if not integration.coa:
            _logger.warning("Account master flag not active.")
            return request.make_response(json.dumps({"message":"Account master is not active"}),
                                         headers=[('Content-Type', 'application/json')],status=404)
        result = []
        # Fetch accounts based on the provided date
        data = request.env['account.account'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No Accounts found matching the criteria.")
            return request.make_response(json.dumps({"message": "No Account found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        tally_company_code_coa = integration.coa_tally_company_code_ids
        for account in data:
            # if request.env.company in account.company_ids:
            account_type = False
            if account.account_type == 'asset_receivable':
                account_type = 'Receivable'
            elif account.account_type == 'asset_cash':
                account_type = 'Bank and Cash'
            elif account.account_type == 'asset_current':
                account_type = 'Current Assets'
            elif account.account_type == 'asset_non_current':
                account_type = 'Non-current Assets'
            elif account.account_type == 'asset_prepayments':
                account_type = 'Prepayments'
            elif account.account_type == 'asset_fixed':
                account_type = 'Fixed Assets'
            elif account.account_type == 'liability_payable':
                account_type = 'Payable'
            elif account.account_type == 'liability_credit_card':
                account_type = 'Credit Card'
            elif account.account_type == 'liability_current':
                account_type = 'Current Liabilities'
            elif account.account_type == 'liability_non_current':
                account_type = 'Non-current Liabilities'
            elif account.account_type == 'equity':
                account_type = 'Equity'
            elif account.account_type == 'equity_unaffected':
                account_type = 'Current Year Earnings'
            elif account.account_type == 'income':
                account_type = 'Income'
            elif account.account_type == 'income_other':
                account_type = 'Other Income'
            elif account.account_type == 'expense':
                account_type = 'Expenses'
            elif account.account_type == 'expense_depreciation':
                account_type = 'Depreciation'
            elif account.account_type == 'expense_direct_cost':
                account_type = 'Cost of Revenue'
            elif account.account_type == 'off_balance':
                account_type = 'Off-Balance Sheet'
            company_name = " "
            for company in account.company_ids:
                if company.id == request.env.company.id:
                    company_name = company.name
            account_entry = {
                'Odoo_id': str(account.id),
                'Code': account.code,
                'Name': account.name,
                'Type': account_type,
                'Company': company_name,
                'Group': account.group_id.name,
                'Sequence': account.group_id.sequence,
                'TallyCompanyCode':tally_company_code_coa
            }
            if account.tag_ids:
                account_entry['Tags'] = [tag.name for tag in account.tag_ids]

            result.append(account_entry)  # Append each account entry to the result

        # If no valid accounts were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid account found.")
            return request.make_response(json.dumps({"message": 'No valid accounts found'}),
                                         headers=[('Content-Type', 'application/json')],
                                         status=404)
        print(result)

        return request.make_response(json.dumps({"accounts": result}), headers=[('Content-Type', 'application/json')],
                                     status=200)
    @http.route('/odoo/api/update_flag_accounts_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_flag_accounts_data(self, **kwargs):
        # Fetch active Tally Integration record
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])
        print(integration)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Check if API key is valid (assuming it's passed as a query param)
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('api_key')
        print(api_key)
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')
            if odoo_id:
                # Fetch account based on the provided name
                accounts = request.env['account.account'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])

                if not accounts:
                    existing_accounts = request.env['account.account'].sudo().browse(int(odoo_id))
                    if existing_accounts.exists():
                            if existing_accounts.nhcl_tally_flag == 'y':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id COA Record Create Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id COA Record Create Flag value already updated'
                                })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id COA Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for account in accounts:
                            account.write({'nhcl_tally_flag': 'y'})
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Record COA Create Flag updated successfully.'
                            })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })

        return result

    @http.route('/odoo/api/get_updated_accounts_json_data', type='http', auth='public', methods=['GET'])
    def get_updated_accounts_json_data(self, **kwargs):
        # Fetch active Tally Integration record
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])
        print(integration)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Check if API key is valid (assuming it's passed as a query param)
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('api_key')
        print(api_key)
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Check if 'account_group' checkbox is enabled
        if not integration.coa:
            _logger.warning("Account master flag not active.")
            return request.make_response(json.dumps({"message":"Account master is not active"}),
                                         headers=[('Content-Type', 'application/xml')],status=404)

        result = []
        data = request.env['account.account'].sudo().search([('update_flag', '=', 'update')])
        if not data:
            _logger.warning("No Accounts found matching the criteria.")
            return request.make_response(
                json.dumps({"message": "No Account found"}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )
        tally_company_code_coa = integration.coa_tally_company_code_ids
        for account in data:
            account_entry = {
                'Odoo_id': str(account.id),
                'Code': account.code,
                'Name': account.name,
                'TallyCompanyCode': tally_company_code_coa
            }
            result.append(account_entry)

        if not result:
            _logger.warning("No Updated valid account found.")
            return request.make_response(({"message": "No valid Accounts found"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        return request.make_response(
            json.dumps({"account": result}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )

    @http.route('/odoo/api/update_updated_accounts_flag_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_accounts_flag_data(self, **kwargs):
        # Fetch active Tally Integration record
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])
        print(integration)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Check if API key is valid (assuming it's passed as a query param)
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('api_key')
        print(api_key)
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')
            if odoo_id:
                # Fetch account based on the provided name
                accounts = request.env['account.account'].sudo().search(
                    [('id', '=', int(odoo_id)), ('update_flag', '=', 'update')])

                if not accounts:
                    existing_accounts = request.env['account.account'].sudo().browse(int(odoo_id))
                    if existing_accounts.exists():
                            if existing_accounts.update_flag == 'no_update':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id COA Record Update Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id COA Record Update Flag value already updated'
                                })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id COA Record Not Found'
                        })

                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for account in accounts:
                        account.write({'update_flag': 'no_update'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id COA Record Update Flag updated successfully'
                        })


        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result