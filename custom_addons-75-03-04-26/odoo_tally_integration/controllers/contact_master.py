import json
from odoo import http
from odoo.http import request,Response
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)



def json_to_xml(json_obj, root_tag="contacts"):
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
                # If it's a list of contact, wrap it in <contact>
                if isinstance(item, dict):
                    # Check if it's a contact (dictionary)
                    line_element = ET.SubElement(parent_element, 'Partner')
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



class GETContacts(http.Controller):

    @http.route('/odoo/api/get_contacts_data', type='http', auth='public', methods=['GET'])
    def get_contact_data(self, **kwargs):
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

        # Fetch Contacts based on the provided date
        data = request.env['res.partner'].sudo().search([('nhcl_tally_flag', '=', 'n'), '|',("customer_rank", ">", 0) , ("supplier_rank", ">", 0)])

        if not data:
            _logger.warning("No Contacts found matching the criteria.")
            return request.make_response('<contacts>No contact found</contacts>',
                                         headers=[('Content-Type', 'application/xml')])

        for contact in data:
            contact = {
                'Name': contact.name,
                # 'Group': contact.group_contact.name,
                'Sequence': contact.contact_sequence,
                'Company': contact.company_id.name,
                'Phone':contact.phone,
                'Email':contact.email,
                'Street':contact.street,
                'City': contact.city,
                'State' : contact.state_id.code,
                'Zip': contact.zip,
                'Country': contact.country_id.code,
                'TAXID' : contact.vat,
                'PAN' : contact.l10n_in_pan
            }

            result.append(contact)  # Append each contact entry to the result

        # If no valid Contacts were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid contact found.")
            return request.make_response('<contacts>No valid Contacts found</contacts>',
                                         headers=[('Content-Type', 'application/xml')])

        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="Contacts")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])


    @http.route('/odoo/api/update_contacts_details', type='http', auth='public',csrf=False, methods=['POST'])
    def update_contacts_details(self, **kwargs):
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
            sequence = kwargs.get('sequence') or request.jsonrequest.get('sequence') or request.params.get('sequence')
            print(sequence)
            if sequence:
                contact = request.env['res.partner'].sudo().search(
                    [('contact_sequence', '=', sequence), ('nhcl_tally_flag', '=', 'n')])

                if not contact:
                    contact = request.env['res.partner'].sudo().search(
                        [('contact_sequence', '=', sequence), ('nhcl_tally_flag', '=', 'y')])
                    if contact:
                        status = 'success'
                        message = 'Contact Flag Already Updated successfully'
                    else:
                        status = 'error'
                        message = 'contact Not Found'
                else:
                    if contact.nhcl_tally_flag == 'n':
                        contact.write({'nhcl_tally_flag': 'y'})
                        status = 'success'
                        message = 'Contact Flag updated successfully'
                    elif contact.nhcl_tally_flag == 'y':
                        status = 'success'
                        message = 'Contact Flag Already Updated successfully'
                    else:
                        status = 'error'
                        message = 'Contact Not Found'
        except Exception as e:
            status = 'error'
            message = str(e)


        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')

    @http.route('/odoo/api/get_updated_contacts_data', type='http', auth='public', methods=['GET'], csrf=False)
    def get_updated_contacts_data(self, **kwargs):
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

        # Fetch Contacts based on the provided date
        data = request.env['res.partner'].sudo().search(
            [('update_flag', '=', 'update'), '|', ("customer_rank", ">", 0), ("supplier_rank", ">", 0)])
        print(data)
        if not data:
            _logger.warning("No Updated Contacts found matching the criteria.")
            return request.make_response('<contacts>No Updated Contacts found</contacts>',
                                         headers=[('Content-Type', 'application/xml')])

        for contact in data:
            contact = {
                'Name': contact.name,
                'Sequence': contact.contact_sequence,
                'Phone': contact.phone,
                'Email': contact.email,
                'Street': contact.street,
                'City': contact.city,
                'State': contact.state_id.code,
                'Zip': contact.zip,
                'Country': contact.country_id.code,
                'TAXID': contact.vat,
                'PAN': contact.l10n_in_pan
            }

            result.append(contact)  # Append each contact entry to the result

        # If no valid Contacts were appended, log and return a suitable response
        if not result:
            _logger.warning("No Updated valid contact found.")
            return request.make_response('<contacts>No Updated valid Contacts found</contacts>',
                                         headers=[('Content-Type', 'application/xml')])

        # Convert the result list directly to XML
        xml_data = json_to_xml(result, root_tag="Contacts")

        # Return the XML response with the appropriate content type
        return request.make_response(xml_data, headers=[('Content-Type', 'application/xml')])

    @http.route('/odoo/api/update_updated_contacts_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_contacts_data(self, **kwargs):
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
            sequence = kwargs.get('sequence') or request.jsonrequest.get('sequence') or request.params.get('sequence')
            print(sequence)
            if sequence:
                data = request.env['res.partner'].sudo().search(
                    [('contact_sequence', '=', sequence), ('update_flag', '=', 'update')])

                if not data:
                    data = request.env['res.partner'].sudo().search(
                        [('contact_sequence', '=', sequence), ('update_flag', '=', 'no_update')])
                    if data:
                        status = 'success'
                        message = 'Contact Update Flag Already Updated successfully'
                else:
                    for contact in data:
                        if contact.update_flag == 'update':
                            contact.write({'update_flag': 'no_update'})
                            status = 'success'
                            message = 'Contact Update Flag updated successfully'
                        elif contact.update_flag == 'no_update':
                            status = 'success'
                            message = 'Contact Update Flag Already Updated successfully'
                        else:
                            status = 'error'
                            message = 'Contact Not Found'
        except Exception as e:
            status = 'error'
            message = str(e)

        # Build XML response
        root = ET.Element("response")
        ET.SubElement(root, "status").text = status
        ET.SubElement(root, "message").text = message
        xml_response = ET.tostring(root, encoding='utf-8', method='xml')

        return Response(xml_response, content_type='application/xml;charset=utf-8')




