import json
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)



class GETCompanies(http.Controller):

    @http.route('/odoo/api/get_company_json_data', type='http', auth='public', methods=['GET'])
    def get_companies_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        # Validate API key
        api_key = kwargs.get('api_key') or request.httprequest.headers.get('api_key')
        if not api_key or api_key != integration.api_key:
            _logger.warning("Invalid API key.")
            return request.make_response(json.dumps({"message": "Invalid API key"}),
                                         headers=[('Content-Type', 'application/json')], status=404)
        if not integration.company_enable:
            _logger.warning("company master not enabled  in integration configuration.")
            return request.make_response(
                json.dumps({"message": "company master not enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)

        data = request.env['res.company'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No company found matching the criteria.")
            return request.make_response(json.dumps({"message":"No company found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)
        result = []
        for company in data:
            company_list = {
                'OdooId': str(company.id),
                'Name': company.name,
                'ParentCompany': company.parent_id.name if company.parent_id else None ,
                # 'ShortName': company.warehouse_id.code,
                'Street': company.street,
                'City': company.city,
                'State': company.state_id.code,
                'Zip': company.zip,
                'Country': company.country_id.code,
                'TaxID': company.vat,
                'Phone': company.phone,
                'Email': company.email,
                # 'Branches': []
            }

            # Fetch branches: other companies with this company as parent
            # branches = request.env['res.company'].sudo().search([('parent_id', '=', company.id)])
            #
            # for branch in branches:
            #     branch_data = {
            #         'Name': branch.name,
            #         'ParentCompany': branch.parent_id.name,
            #         'ShortName': branch.warehouse_id.code,
            #         'Street': branch.street,
            #         'City': branch.city,
            #         'State': branch.state_id.code,
            #         'Zip': branch.zip,
            #         'Country': branch.country_id.code,
            #         'TaxID': branch.vat,
            #         'Phone': branch.phone,
            #         'Email': branch.email,
            #     }
            #     company_list['Branches'].append(branch_data)

            result.append(company_list)

        if not result:
            _logger.warning("No valid company found.")
            return request.make_response(json.dumps({"message": 'No valid company found'}),
                                         headers=[('Content-Type', 'application/json')],
                                         status=404)
        print(result)

        return request.make_response(json.dumps({"companies": result}), headers=[('Content-Type', 'application/json')],
                                     status=200)

    @http.route('/odoo/api/update_flag_company_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_companies_data(self, **kwargs):
        integration = request.env['tally.integration'].sudo().search([('active_record', '=', True)], limit=1)

        if not integration:
            _logger.warning("No active Tally Integration configuration found.")
            return request.make_response(json.dumps({"message": "Integration configuration not done"}),
                                         headers=[('Content-Type', 'application/json')], status=404)

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
                # Fetch company based on the provided name
                companies = request.env['res.company'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])

                if not companies:
                    existing_company = request.env['res.company'].sudo().browse(int(odoo_id))
                    if existing_company.exists():
                        if existing_company.nhcl_tally_flag == 'y':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Company Record Create Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Company Record Create Flag value already updated'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Company Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for company in companies:
                        company.write({'nhcl_tally_flag': 'y'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id Record Company Create Flag updated successfully.'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result