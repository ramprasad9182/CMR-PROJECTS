from odoo import http
from odoo.http import request,Response
import logging
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
_logger = logging.getLogger(__name__)



def json_to_xml(json_obj, root_tag="transactions"):
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
                # If it's a list of journal entries, wrap it in <Journal Entry>
                if isinstance(item, dict):
                    # Check if it's a journal entry (dictionary)
                    if 'Lines' in item:
                        line_element = ET.SubElement(parent_element, 'JournalEntry')
                    else:
                        line_element = ET.SubElement(parent_element, 'item')
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



class GETJournals(http.Controller):

    @http.route('/odoo/api/get_journal_entries', type='http', auth='public', methods=['GET'])
    def get_journal_entries(self, **kwargs):
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

        # Fetch journal entries based on the provided date
        data = request.env['account.move'].sudo().search([('nhcl_tally_flag', '=', 'n'),('state','=','posted')])
        print(data)
        if not data:
            _logger.warning("No journal entries found matching the criteria.")
            return request.make_response('<transactions>No journal entries found</transactions>',
                                         headers=[('Content-Type', 'application/xml')])

        for move in data:
            if move.narration != False:
                soup = BeautifulSoup(move.narration or '', 'html.parser')
                narration = soup.get_text()
            else:
                narration = False
            journal_entry = {
                'RecordID' : str(move.id),
                'Date': move.date.strftime('%Y-%m-%d'),
                'Name': move.name,
                'Ref': move.ref,
                'Journal': move.journal_id.name,
                'Company': move.company_id.name,
                'Notes': narration,
                'Lines': []  # Prepare list for journal lines
            }



            # Add line items to the journal entry
            for line in move.line_ids:
                # siva
                branch = line.partner_id.name
                sequence= " "
                journal_entry['Lines'].append({
                    'AccountCode': line.account_id.code,
                    'AccountName': line.account_id.name,
                    'AccountType': line.account_id.account_type,
                    'Branch': branch,  # Use "False" if no branch
                    # 'Sequence': sequence,
                    'Debit': line.debit,
                    'Credit': line.credit
                })

                # If no lines are added, log the information
            if not journal_entry['Lines']:
                _logger.warning(f"Journal entry {move.name} has no line items.")

            result.append(journal_entry)  # Append each journal entry to the result
        print(result)
        # If no valid journal entries were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid journal entries with lines found.")
            return request.make_response('<transactions>No valid journal entries found</transactions>',
                                         headers=[('Content-Type', 'application/xml')])

        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="transactions")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_journal_entries', type='http', auth='public', methods=['POST'],csrf=False)
    def update_journal_entries(self, **kwargs):
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
            name = kwargs.get('name') or request.params.get('name')
            if name:
                journal_entry = request.env['account.move'].sudo().search(
                    [('name', '=', name), ('nhcl_tally_flag', '=', 'n'),('state','=','posted')])

                if not journal_entry:
                    journal_entry = request.env['account.move'].sudo().search(
                        [('name', '=', name), ('nhcl_tally_flag', '=', 'y'),('state','=','posted')])
                    if journal_entry:
                        status = "success"
                        message = "JE Flag Already Updated successfully"
                    else:
                        status = "error"
                        message = "JE Not Found"
                else:
                    for je in journal_entry:
                        if je.nhcl_tally_flag == 'n':
                            je.write({'nhcl_tally_flag': 'y'})
                            status = "success"
                            message = "JE Flag updated successfully"
                        elif je.nhcl_tally_flag == 'y':
                            status = "success"
                            message = "JE Flag Already Updated successfully"
                        else:
                            status = "error"
                            message = "JE Not Found"
            else:
                status = "error"
                message = "Missing required parameter: name"

        except Exception as e:
            status = "error"
            message = str(e)

        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')


    @http.route('/odoo/api/get_updated_journal_entries', type='http', auth='public', methods=['GET'])
    def get_updated_journal_entries(self, **kwargs):
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

        # Fetch journal entries based on the provided date
        data = request.env['account.move'].sudo().search([('update_flag', '=', 'update'),('state','=','posted')])

        if not data:
            _logger.warning("No Updated journal entries found matching the criteria.")
            return request.make_response('<transactions>No Updated journal entries found</transactions>',
                                         headers=[('Content-Type', 'application/xml')])

        for move in data:
            if move.narration != False:
                soup = BeautifulSoup(move.narration or '', 'html.parser')
                narration = soup.get_text()
            else:
                narration = False
            journal_entry = {
                'Name': move.name,
                'Ref': move.ref,
                'Notes': narration,
            }

            result.append(journal_entry)  # Append each journal entry to the result

        # If no valid journal entries were appended, log and return a suitable response
        if not result:
            _logger.warning("No Updated Valid journal entries with lines found.")
            return request.make_response('<transactions>No Updated Valid journal entries found</transactions>',
                                         headers=[('Content-Type', 'application/xml')])

        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="transactions")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_updated_journal_entries', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_journal_entries(self, **kwargs):
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
            name = kwargs.get('name') or request.jsonrequest.get('name') or request.params.get('name')
            if name:
                # Fetch journal entries based on the provided name
                journal_entry = request.env['account.move'].sudo().search(
                    [('name', '=', name), ('update_flag', '=', 'update'),('state','=','posted')])

                if not journal_entry:
                    journal_entry = request.env['account.move'].sudo().search(
                        [('name', '=', name), ('update_flag', '=', 'no_update'),('state','=','posted')])
                    if journal_entry:
                        status = 'success'
                        message = 'JE Flag Already Updated successfully'
                    else:
                        status = 'error'
                        message = 'Updated JE Not Found'

                else:
                    # Assuming the flag is a boolean field named 'update_flag'
                    for je in journal_entry:
                        if je.update_flag == 'update':
                            je.write({'update_flag': 'no_update'})
                            status ='success'
                            message = 'JE Flag updated successfully'
                        elif je.update_flag == 'no_update':
                            status ='success'
                            message = 'JE Flag Already Updated successfully'
                        else:
                            status = 'error'
                            message = 'Updated JE Not Found'

        except Exception as e:
            status = "error"
            message = str(e)


        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')