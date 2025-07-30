# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class GETAccountGroups(http.Controller):
    @http.route('/odoo/api/get_account_groups_json_data', type='http', auth='public', methods=['GET'])
    def get_account_groups_json_data(self, **kwargs):
        # Fetch active Tally Integration record
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)])
        print(integration)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({ "message": "Integration configuration not done"}),
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
        if not integration.account_group:
            _logger.warning("Account Group master flag not active.")
            return request.make_response(json.dumps({"message": "Account Group master is not active"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        # Fetch data from account.group model for the integration.company only
        result= []
        data = request.env['account.group'].sudo().search([
            ('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No Account Group records found for base company.")
            return request.make_response(json.dumps({ "message": "No Account Group records found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)
        company_code = integration.account_group_tally_company_code_ids
        print(company_code)
        for account_group in data:
            # subtype = False
            # type = False
            # sub_type = False
            # if account_group.type == 'asset':
            #     subtype = account_group.asset_sub_type
            #     type = 'Asset'
            #     if subtype == 'receivable':
            #         sub_type = 'Receivable'
            #     elif subtype == 'bank_cash':
            #         sub_type = 'Bank & Cash'
            #     elif subtype == 'current_assets':
            #         sub_type = 'Current Assets'
            #     elif subtype == 'non_current_assets':
            #         sub_type = 'Non Current Assets'
            #     elif subtype == 'prepayments':
            #         sub_type = 'Prepayments'
            #     elif subtype == 'fixed_assets':
            #         sub_type = 'Fixed Assets'
            # elif account_group.type == 'liability':
            #     subtype = account_group.liability_sub_type
            #     type = 'Liability'
            #     if subtype == 'payable':
            #         sub_type = 'Payable'
            #     elif subtype == 'credit_card':
            #         sub_type = 'Credit Card'
            #     elif subtype == 'current_liabilities':
            #         sub_type = 'Current Liabilities'
            #     elif subtype == 'non_current_liabilities':
            #         sub_type = 'Non Current Liabilities'
            # elif account_group.type == 'equity':
            #     subtype = account_group.equity_sub_type
            #     type = 'Equity'
            #     if subtype == 'equity':
            #         sub_type = 'Equity'
            #     elif subtype == 'current_year_earnings':
            #         sub_type = 'Current Year Earnings'
            # elif account_group.type == 'revenue':
            #     subtype = account_group.revenue_sub_type
            #     type = 'Revenue'
            #     if subtype == 'income':
            #         sub_type = 'Income'
            #     elif subtype == 'other_income':
            #         sub_type = 'Other Income'
            # elif account_group.type == 'expenditure':
            #     subtype = account_group.expense_sub_type
            #     type = 'Expenditure'
            #     if subtype == 'expenses':
            #         sub_type = 'Expenses'
            #     elif subtype == 'depreciation':
            #         sub_type = 'Depreciation'
            #     elif subtype == 'cost_of_revenue':
            #         sub_type = 'Cost of Revenue'
            # elif account_group.type == 'others':
            #     subtype = account_group.other_sub_type
            #     type = 'Others'
            #     if subtype == 'off_balance':
            #         sub_type = 'Off Balance'
            account_group_entry = {
                'Odoo_id': str(account_group.id),
                'Name': account_group.name,
                'SubType': account_group.nhcl_parent_id.name,
                'Sequence': account_group.sequence,
                # 'Type': type,
                # 'SubType': sub_type,
                'Company': account_group.company_id.name,
                'TallyCompanyCode': company_code,
            }
            print("***********************888",account_group.name)
            result.append(account_group_entry)  # Append each account_group entry to the result
        # If no valid account_groups were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid Account Group found.")
            return request.make_response(
                json.dumps({"message": "No valid Account Groups found"}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )

        return request.make_response(
            json.dumps({"account_groups": result}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )

    @http.route('/odoo/api/update_account_groups_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_account_groups_data(self, **kwargs):
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
                # Fetch account_group based on the provided name
                account_groups = request.env['account.group'].sudo().search([('id', '=', int(odoo_id)),
                                                                             ('nhcl_tally_flag', '=', 'n')])
                if not account_groups:
                    existing_account_groups = request.env['account.group'].sudo().browse(int(odoo_id))
                    if existing_account_groups.exists():
                        if existing_account_groups.nhcl_tally_flag == 'Y':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Account Group Record Create Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Account Group Record JE Create Flag value invalid'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Account Group Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for account_group in account_groups:
                        account_group.write({'nhcl_tally_flag': 'y'})
                        result = json.dumps({
                            'id': odoo_id,
                            'status': 'success',
                            'message': 'Account Group Create Flag updated successfully'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result

    @http.route('/odoo/api/get_updated_account_groups_name', type='http', auth='public', methods=['GET'], csrf=False)
    def get_updated_account_groups_name(self, **kwargs):
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
        if not integration.account_group:
            _logger.warning("Account Group master flag not active.")
            return request.make_response(json.dumps({"message": "Account Group master is not active"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        # Fetch data from account.group model for the integration.company only
        data = request.env['account.group'].sudo().search([
            ('update_flag', '=', 'update')])

        if not data:
            _logger.warning("No Account Group records found for base company.")
            return request.make_response('<account_groups>No Account Group records found</account_groups>',
                                         headers=[('Content-Type', 'application/xml')])

        result = []
        company_code = integration.account_group_tally_company_code_ids
        for account_group in data:
            account_group_entry = {
                'Odoo_id': str(account_group.id),
                'Name': account_group.name,
                'Parent_id': account_group.nhcl_parent_id.name,
                'Sequence': account_group.sequence,
                'TallyCompanyCode':company_code,
            }
            print(account_group_entry)
            result.append(account_group_entry)

        if not result:
            _logger.warning("No valid Account Group found.")
            return request.make_response(
                json.dumps({"message": "No valid Account Groups found"}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )

        return request.make_response(
            json.dumps({"account_groups": result}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )


    @http.route('/odoo/api/update_updated_account_groups_data', type='http', auth='public', methods=['POST'],
                csrf=False)
    def update_updated_account_groups_data(self, **kwargs):
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
                # Fetch account_group based on the provided name
                account_groups = request.env['account.group'].sudo().search(
                    [('id', '=', int(odoo_id)), ('update_flag', '=', 'update')])

                if not account_groups:
                    existing_account_groups = request.env['account.group'].sudo().browse(int(odoo_id))
                    if existing_account_groups.exists():
                            if existing_account_groups.update_flag == 'no_update':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id Account Group Record Update Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id Account Group Record JE Update Flag value invalid'
                                })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Account Group Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for account_group in account_groups:
                        account_group.write({'update_flag': 'no_update'})
                        result = json.dumps({
                            'id': odoo_id,
                            'status': 'success',
                            'message': 'Account Group Update Flag updated successfully'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })

        return  result