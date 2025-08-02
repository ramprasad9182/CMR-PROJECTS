import json
from odoo import http
from odoo.http import request,Response
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)



def json_to_xml(json_obj, root_tag="accounts"):
    """ Convert JSON object to XML string. """

    def build_xml_element(obj, parent_element):
        """ Recursively build XML elements from JSON object. """
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Create a new element for each key-value pair
                child = ET.SubElement(parent_element, key)
                build_xml_element(value, child)
        elif isinstance(obj, list):
            for item in obj:
                # If it's a list of account, wrap it in <Account>
                if isinstance(item, dict):
                    # Check if it's a account (dictionary)
                    line_element = ET.SubElement(parent_element, 'Account')
                    build_xml_element(item, line_element)
                elif isinstance(item, list):  # If it's lines (list of dictionaries)
                    for line in item:  # Wrap each line in <line> tags
                        line_element = ET.SubElement(parent_element, 'line')
                        build_xml_element(line, line_element)
        else:
            # For primitive data types, set the text of the element
            parent_element.text = str(obj)

    # Create the root element
    root = ET.Element(root_tag)
    build_xml_element(json_obj, root)

    # Convert the tree to a string and return it
    return ET.tostring(root, encoding='unicode', method='xml')



class GETAccounts(http.Controller):

    @http.route('/odoo/api/get_accounts_data', type='http', auth='public', methods=['GET'])
    def get_accounts_data(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        print(api_key)
        if not api_key:
            return request.make_response(
                '<error>API key is required in header</error>',
                headers=[('Content-Type', 'application/xml')],
                status=401
            )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                '<error>Invalid API key</error>',
                headers=[('Content-Type', 'application/xml')],
                status=403
            )
        result = []

        # Fetch accounts based on the provided date
        data = request.env['account.account'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No Accounts found matching the criteria.")
            return request.make_response('<accounts>No account found</accounts>',
                                         headers=[('Content-Type', 'application/xml')])

        for account in data:
            if request.env.company in account.company_ids:
                account_type  = False
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
                company_name =" "
                for company in account.company_ids:
                    if company.id == request.env.company.id:
                        company_name = company.name
                        print(company_name)
                account_entry = {
                    'Code': account.code,
                    'Name': account.name,
                    'Type': account_type,
                    'Company': company_name,
                    'Group':account.group_id.name,
                    'Sequence':account.group_id.sequence
                }

                result.append(account_entry)  # Append each account entry to the result

        # If no valid accounts were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid account found.")
            return request.make_response('<accounts>No valid accounts found</accounts>',
                                         headers=[('Content-Type', 'application/xml')])
        print(result)
        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="Accounts")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_accounts_data', type='http', auth='public', methods=['POST'],csrf=False)
    def update_accounts_data(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        print(api_key)
        if not api_key:
            return request.make_response(
                '<error>API key is required in header</error>',
                headers=[('Content-Type', 'application/xml')],
                status=401
            )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                '<error>Invalid API key</error>',
                headers=[('Content-Type', 'application/xml')],
                status=403
            )
        try:
            code = kwargs.get('code') or request.jsonrequest.get('code') or request.params.get('code')
            if code:
                # Fetch account based on the provided name
                accounts = request.env['account.account'].sudo().search(
                    [('code', '=', code), ('nhcl_tally_flag', '=', 'n')])

                if not accounts:
                    accounts = request.env['account.account'].sudo().search(
                        [('code', '=', code), ('nhcl_tally_flag', '=', 'y')])
                    if accounts:
                        status = 'success'
                        message = 'Account Flag Already Updated successfully'
                    else:
                        status = 'error'
                        message = 'Account Not Found'
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for account in accounts:
                        if request.env.company in account.company_ids:
                            account.write({'nhcl_tally_flag': 'y'})
                            status = 'success'
                            message = 'Account Flag updated successfully'
                        elif account.nhcl_tally_flag == 'y':
                            status = 'success'
                            message = 'Account Flag Already Updated successfully'
                        else:
                            status = 'error'
                            message = 'Account Not Found'

        except Exception as e:
            status = 'error'
            message = str(e)

        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')


    @http.route('/odoo/api/get_updated_accounts_data', type='http', auth='public', methods=['GET'])
    def get_updated_accounts_data(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        print(api_key)
        if not api_key:
            return request.make_response(
                '<error>API key is required in header</error>',
                headers=[('Content-Type', 'application/xml')],
                status=401
            )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                '<error>Invalid API key</error>',
                headers=[('Content-Type', 'application/xml')],
                status=403
            )
        result = []

        # Fetch accounts based on the provided date
        data = request.env['account.account'].sudo().search([('update_flag', '=', 'update')])

        if not data:
            _logger.warning("No Updated Accounts found matching the criteria.")
            return request.make_response('<accounts>No Updated account found</accounts>',
                                         headers=[('Content-Type', 'application/xml')])

        for account in data:
            if request.env.company in account.company_ids:
                account_entry = {
                    'Code': account.code,
                    'Name': account.name,
                }

                result.append(account_entry)  # Append each account entry to the result

        # If no valid accounts were appended, log and return a suitable response
        if not result:
            _logger.warning("No Updated valid account found.")
            return request.make_response('<accounts>No Updated valid accounts found</accounts>',
                                         headers=[('Content-Type', 'application/xml')])

        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="accounts")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_updated_accounts_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_accounts_data(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        print(api_key)
        if not api_key:
            return request.make_response(
                '<error>API key is required in header</error>',
                headers=[('Content-Type', 'application/xml')],
                status=401
            )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                '<error>Invalid API key</error>',
                headers=[('Content-Type', 'application/xml')],
                status=403
            )
        try:
            code = kwargs.get('code') or request.jsonrequest.get('code') or request.params.get('code')
            if code:
                # Fetch account based on the provided name
                accounts = request.env['account.account'].sudo().search(
                    [('code', '=', code), ('update_flag', '=', 'update')])

                if not accounts:
                    accounts = request.env['account.account'].sudo().search(
                        [('code', '=', code), ('update_flag', '=', 'no_update')])
                    if accounts:
                        status = 'success'
                        message = 'Account Flag Already Updated successfully'
                    else:
                        status = 'error'
                        message = 'Updated Account Not Found'
                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for account in accounts:
                        if request.env.company in account.company_ids:
                            account.write({'update_flag': 'no_update'})
                            status = 'success'
                            message = 'Account Flag updated successfully'
                        elif account.update_flag == 'no_update':
                            status = 'success'
                            message = 'Account Flag Already Updated successfully'

                        else:
                            status = 'error'
                            message = 'Updated Account Not Found'
        except Exception as e:
            status = 'error'
            message = str(e)

        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')