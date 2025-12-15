import json
from odoo import http
from odoo.http import request,Response
import logging
from bs4 import BeautifulSoup
_logger = logging.getLogger(__name__)


class GETContacts(http.Controller):

    @http.route('/odoo/api/get_contacts_json_data', type='http', auth='public', methods=['GET'])
    def get_contacts_json_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=400)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Build domain based on integration flags
        domain = [('nhcl_tally_flag', '=', 'n'),('partner_type', '!=', False),('partner_type', '!=', 'others')]
        print(domain)
        if integration.customers and integration.vendors:
            domain += ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
            print(domain)
        elif integration.customers:
            domain += [('customer_rank', '>', 0)]
            print(domain)
        elif integration.vendors:
            domain += [('supplier_rank', '>', 0)]
            print(domain)
        else:
            _logger.warning("Neither customer nor vendor flag enabled.")
            return request.make_response(json.dumps({"message": "Contact master is not active"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        partners = request.env['res.partner'].sudo().search(domain)
        partners_count = request.env['res.partner'].sudo().search_count(domain)
        print(partners_count)
        if not partners:
            _logger.warning("No matching partners found.")
            return request.make_response(json.dumps({"message": "No Contacts found matching the criteria."}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Format partner data
        result = []
        contact_tally_company_code = ''
        tally_company_code_contact = []
        for partner in partners:
            narration = ''
            if partner.comment:
                soup = BeautifulSoup(partner.comment or '', 'html.parser')
                narration = soup.get_text()

            if partner.partner_type == 'customer':
                terms = partner.property_payment_term_id.name or ''
                contact_tally_company_code = integration.customers_tally_company_code_ids
                tally_company_code_contact = [code.strip() for code in contact_tally_company_code.split(',')]

            elif partner.partner_type == 'supplier':
                terms = partner.property_supplier_payment_term_id.name or ''
                contact_tally_company_code = integration.vendors_tally_company_code_ids
                tally_company_code_contact = [code.strip() for code in contact_tally_company_code.split(',')]

            else:
                terms = ''
                tally_company_code_contact = []
            # if not tally_company_code_contact:
            #     continue

            base_data = {
                'Odoo_id': str(partner.id),
                'Name': f"{partner.name}-{partner.contact_sequence}" if partner.contact_sequence else partner.name,
                "PartnerType": partner.partner_type,
                'Sequence': partner.contact_sequence,
                'MainCompany': partner.company_id.name,
                'TallyCompanyCode': tally_company_code_contact,
                'Mobile': partner.mobile,
                'Email': partner.email,
                'Website': partner.website,
                'Street': partner.street,
                'Street2': partner.street2,
                'City': partner.city,
                'State': partner.state_id.name if partner.state_id else '',
                'Zip': partner.zip,
                'Country': partner.country_id.name if partner.country_id else '',
                'TaxId': partner.vat,
                'Pan': partner.l10n_in_pan,
                'PaymentTerms': terms,
                'comment': narration,

            }


            if partner.company_type == 'person':
                base_data.update({
                    'PartnerCompany': partner.parent_id.name or '',
                    'Role': partner.function or '',
                })

            result.append(base_data)

        return request.make_response(
            json.dumps({'Contacts': result}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )


    @http.route('/odoo/api/update_flag_contacts_details', type='http', auth='public', csrf=False, methods=['POST'])
    def update_flag_contacts_details(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=400)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get("Odoo_id")
            if odoo_id:
                updated_count = 0
                contacts = request.env['res.partner'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])
                if not contacts:
                    existing_contacts = request.env['res.partner'].sudo().browse(int(odoo_id))
                    if existing_contacts.exists():
                        if existing_contacts.nhcl_tally_flag == 'y':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Contact Record Create Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Contact Record Create Flag Contain invalid value'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Contact Record Not Found'
                        })
                else:
                    for contact in contacts:
                        contact.write({'nhcl_tally_flag': 'y'})
                        updated_count += 1
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id Contact Record Create Flag updated successfully'
                        })

        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })

        return result


    @http.route('/odoo/api/get_updated_contacts_json_data', type='http', auth='public', methods=['GET'], csrf=False)
    def get_updated_contacts_json_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=400)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Build domain based on integration flags
        domain = [('update_flag', '=', 'update'),('partner_type', '!=', False),('partner_type', '!=', 'others')]
        print(domain)
        if integration.customers and integration.vendors:
            domain += ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
            print(domain)
        elif integration.customers:
            domain += [('customer_rank', '>', 0)]
            print(domain)
        elif integration.vendors:
            domain += [('supplier_rank', '>', 0)]
            print(domain)
        else:
            _logger.warning("Neither customer nor vendor flag enabled.")
            return request.make_response(json.dumps({"message": "Contact master is not active"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        partners = request.env['res.partner'].sudo().search(domain)
        if not partners:
            _logger.warning("No matching partners found.")
            return request.make_response(json.dumps({"message": "No Updated Contacts found matching the criteria."}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Format partner data
        result = []
        contact_tally_company_code = ''
        tally_company_code_contact = []
        for partner in partners:
            narration = ''
            if partner.comment:
                soup = BeautifulSoup(partner.comment or '', 'html.parser')
                narration = soup.get_text()

            if partner.partner_type == 'customer':
                terms = partner.property_payment_term_id.name or ''
                contact_tally_company_code = integration.customers_tally_company_code_ids
                tally_company_code_contact = [code.strip() for code in contact_tally_company_code.split(',')]

            elif partner.partner_type == 'supplier':
                terms = partner.property_supplier_payment_term_id.name or ''
                contact_tally_company_code = integration.vendors_tally_company_code_ids
                tally_company_code_contact = [code.strip() for code in contact_tally_company_code.split(',')]
            else:
                terms = ''
                tally_company_code_contact = []

            # if not tally_company_code_contact:
            #     continue

            base_data = {
                'Odoo_id': str(partner.id),
                'Name': f"{partner.name}-{partner.contact_sequence}" if partner.contact_sequence else partner.name,
                "PartnerType": partner.partner_type,
                'Mobile': partner.mobile,
                'TallyCompanyCode': tally_company_code_contact,
                'Email': partner.email,
                'Website': partner.website,
                'Street': partner.street,
                'Street2': partner.street2,
                'City': partner.city,
                'State': partner.state_id.name if partner.state_id else '',
                'Zip': partner.zip,
                'Country': partner.country_id.name if partner.country_id else '',
                'TaxId': partner.vat,
                'Pan': partner.l10n_in_pan,
                'PaymentTerms': terms,
                'comment': narration,
            }

            if partner.company_type == 'person':
                base_data.update({
                    'PartnerCompany': partner.parent_id.name or '',
                    'Role': partner.function or '',
                })

            result.append(base_data)

        return request.make_response(
            json.dumps({'Contacts': result}),
            headers=[('Content-Type', 'application/json')],
            status=200
        )


    @http.route('/odoo/api/update_updated_contacts_flag_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_updated_contacts_flag_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=400)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
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
                data = request.env['res.partner'].sudo().search(
                    [('id', '=', int(odoo_id)), ('update_flag', '=', 'update')])
                if not data:
                    existing_contacts = request.env['res.partner'].sudo().browse(int(odoo_id))
                    if existing_contacts.exists():
                        if existing_contacts.update_flag == 'no_update':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Contact Record Update Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Contact Record Update Flag Contain invalid value'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Contact Record Not Found'
                        })
                else:
                    for contact in data:
                        contact.write({'update_flag': 'no_update'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id Contact Record Update Flag Updated successfully'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result