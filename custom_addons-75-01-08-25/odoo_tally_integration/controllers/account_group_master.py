import json
from odoo import http
from odoo.http import request,Response
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)



def json_to_xml(json_obj, root_tag="AccountGroups"):
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
                # If it's a list of account_group, wrap it in <account_group>
                if isinstance(item, dict):
                    # Check if it's a account_group (dictionary)
                    line_element = ET.SubElement(parent_element, 'AccountGroup')
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



class GETAccountGroups(http.Controller):

    @http.route('/odoo/api/get_account_groups_data', type='http', auth='public', methods=['GET'])
    def get_account_groups_data(self, **kwargs):
        # api_key = kwargs.get('api_key')
        # if not api_key:
        #     api_key = request.httprequest.headers.get('x-api-key')
        # print(api_key)
        # if not api_key:
        #     return request.make_response(
        #         '<error>API key is required in header</error>',
        #         headers=[('Content-Type', 'application/xml')],
        #         status=401
        #     )
        #
        # api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])
        #
        # if not api_access:
        #     return request.make_response(
        #         '<error>Invalid API key</error>',
        #         headers=[('Content-Type', 'application/xml')],
        #         status=403
        #     )
        result = []

        # Fetch account_groups based on the provided date
        data = request.env['account.group'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No Account Group found matching the criteria.")
            return request.make_response('<account_groups>No Account Group found</account_groups>',
                                         headers=[('Content-Type', 'application/xml')])

        for account_group in data:
            if request.env.company == account_group.company_id:
                subtype = False
                type = False
                sub_type  = False
                if account_group.type == 'asset':
                    subtype = account_group.asset_sub_type
                    type = 'Asset'
                    if subtype == 'receivable':
                        sub_type = 'Receivable'
                    elif subtype == 'bank_cash':
                        sub_type = 'Bank & Cash'
                    elif subtype == 'current_assets':
                        sub_type = 'Current Assets'
                    elif subtype == 'non_current_assets':
                        sub_type = 'Non Current Assets'
                    elif subtype == 'prepayments':
                        sub_type = 'Prepayments'
                    elif subtype == 'fixed_assets':
                        sub_type = 'Fixed Assets'
                elif account_group.type == 'liability':
                    subtype = account_group.liability_sub_type
                    type = 'Liability'
                    if subtype == 'payable':
                        sub_type = 'Payable'
                    elif subtype == 'credit_card':
                        sub_type = 'Credit Card'
                    elif subtype == 'current_liabilities':
                        sub_type = 'Current Liabilities'
                    elif subtype == 'non_current_liabilities':
                        sub_type = 'Non Current Liabilities'
                elif account_group.type == 'equity':
                    subtype = account_group.equity_sub_type
                    type = 'Equity'
                    if subtype == 'equity':
                        sub_type = 'Equity'
                    elif subtype == 'current_year_earnings':
                        sub_type = 'Current Year Earnings'
                elif account_group.type == 'revenue':
                    subtype = account_group.revenue_sub_type
                    type = 'Revenue'
                    if subtype == 'income':
                        sub_type = 'Income'
                    elif subtype == 'other_income':
                        sub_type = 'Other Income'
                elif account_group.type == 'expenditure':
                    subtype = account_group.expense_sub_type
                    type = 'Expenditure'
                    if subtype == 'expenses':
                        sub_type = 'Expenses'
                    elif subtype == 'depreciation':
                        sub_type = 'Depreciation'
                    elif subtype == 'cost_of_revenue':
                        sub_type = 'Cost of Revenue'
                elif account_group.type == 'others':
                    subtype = account_group.other_sub_type
                    type = 'Others'
                    if subtype == 'off_balance':
                        sub_type = 'Off Balance'
                account_group_entry = {
                    'Name': account_group.name,
                    'Sequence': account_group.sequence,
                    'Type': type,
                    'SubType': sub_type,
                    'Company': account_group.company_id.name,
                }

                result.append(account_group_entry)  # Append each account_group entry to the result
        # If no valid account_groups were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid Account Group found.")
            return request.make_response('<account_group>No valid Account Groups found</account_group>',
                                         headers=[('Content-Type', 'application/xml')])
        print(result)
        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="AccountGroups")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_account_groups_data', type='http', auth='public', methods=['POST'],csrf=False)
    def update_account_groups_data(self, **kwargs):
        # api_key = kwargs.get('api_key')
        # if not api_key:
        #     api_key = request.httprequest.headers.get('x-api-key')
        # print(api_key)
        # if not api_key:
        #     return request.make_response(
        #         '<error>API key is required in header</error>',
        #         headers=[('Content-Type', 'application/xml')],
        #         status=401
        #     )
        #
        # api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])
        #
        # if not api_access:
        #     return request.make_response(
        #         '<error>Invalid API key</error>',
        #         headers=[('Content-Type', 'application/xml')],
        #         status=403
        #     )
        result =[]
        try:
            sequence = kwargs.get('sequence') or request.jsonrequest.get('sequence') or request.params.get('sequence')
            if sequence:
                # Fetch account_group based on the provided name
                account_groups = request.env['account.group'].sudo().search(
                    [('sequence', '=', sequence), ('nhcl_tally_flag', '=', 'n')])

                if not account_groups:
                    account_groups = request.env['account.group'].sudo().search(
                        [('sequence', '=', sequence), ('nhcl_tally_flag', '=', 'y')])
                    if account_groups:
                        result = json.dumps({
                            'status': 'success',
                            'message': 'Account Group Flag Already Updated successfully'
                        })
                    else:
                        result = json.dumps({
                        'status': 'error',
                        'message': 'Account Groups Not Found'
                    })

                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for account_group in account_groups:
                        if request.env.company == account_group.company_id:
                            account_group.write({'nhcl_tally_flag': 'y'})
                            result = json.dumps({
                                'status': 'success',
                                'message': 'Account Group Flag updated successfully'
                            })
                        elif account_group.nhcl_tally_flag == 'y':
                            result = json.dumps({
                                'status': 'success',
                                'message': 'Account Group Flag Already updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status' : 'error',
                                'message': 'Account Group Not Found'
                            })


        except Exception as e:
            result = json.dumps({
            'status' : 'error',
            'message' : str(e)
            })

        # Build XML response
        # root = ET.Element("response")
        # ET.SubElement(root, "status").text = status
        # ET.SubElement(root, "message").text = message
        # xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        # return Response(xml_response, content_type='application/xml;charset=utf-8')
        return result

    # @http.route('/odoo/api/get_updated_account_groups_name', type='http', auth='public', methods=['GET'], csrf=False)
    # def get_updated_account_groups_name(self, **kwargs):
    #     api_key = kwargs.get('api_key')
    #     if not api_key:
    #         api_key = request.httprequest.headers.get('x-api-key')
    #     print(api_key)
    #     if not api_key:
    #         return request.make_response(
    #             '<error>API key is required in header</error>',
    #             headers=[('Content-Type', 'application/xml')],
    #             status=401
    #         )
    #
    #     api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])
    #
    #     if not api_access:
    #         return request.make_response(
    #             '<error>Invalid API key</error>',
    #             headers=[('Content-Type', 'application/xml')],
    #             status=403
    #         )
    #     result = []
    #     data = request.env['account.group'].sudo().search([('update_flag', '=', 'update')])
    #
    #     if not data:
    #         _logger.warning("No Updated Account Group found")
    #         return request.make_response('<account_groups>No Updated Account Group found</account_groups>',
    #                                      headers=[('Content-Type', 'application/xml')])
    #     for account_group in data:
    #         if request.env.company == account_group.company_id:
    #             account_group_entry = {
    #                 'Name': account_group.name,
    #                 'Sequence': account_group.sequence,
    #             }
    #
    #             result.append(account_group_entry)
    #
    #
    #     if not result:
    #         _logger.warning("No Updated valid Account Group found.")
    #         return request.make_response('<account_group>No Updated valid Account Groups found</account_group>',
    #                                      headers=[('Content-Type', 'application/xml')])
    #
    #
    #     xml_data = json_to_xml(result, root_tag="account_groups")
    #
    #
    #     return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_updated_account_groups_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_account_groups_data(self, **kwargs):
        result = []
        try:
            sequence = kwargs.get('sequence') or request.jsonrequest.get('sequence') or request.params.get('sequence')
            if sequence:
                # Fetch account_group based on the provided name
                account_groups = request.env['account.group'].sudo().search(
                    [('sequence', '=', sequence), ('update_flag', '=', 'update')])

                if not account_groups:
                    account_groups = request.env['account.group'].sudo().search(
                        [('sequence', '=', sequence), ('update_flag', '=', 'no_update')])
                    if account_groups:
                        result = json.dump
                        status ='success'
                        message = 'Account Group Flag Already Updated successfully'

                    else:
                        status = 'error'
                        message = 'Updated Account Groups Not Found'
                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for account_group in account_groups:
                        if request.env.company == account_group.company_id:
                            account_group.write({'update_flag': 'no_update'})
                            status = 'success'
                            message = 'Account Group Flag updated successfully'
                        elif account_group.update_flag == 'no_update':
                            status = 'success'
                            message = 'Account Group Flag Already Updated successfully'
                        else:
                            status = 'error'
                            message = 'Updated Account Group Not Found'

        except Exception as e:
            status = 'error'
            message = str(e)

        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')



