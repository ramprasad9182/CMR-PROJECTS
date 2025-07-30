import json
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class GETLocations(http.Controller):

    @http.route('/odoo/get_location_json_data', type='http', auth='public', methods=['GET'])
    def get_location_json_data(self, **kwargs):
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
        if not integration.location_enable:
            _logger.warning("Location master not enabled  in integration configuration.")
            return request.make_response(
                json.dumps({"message": "Location master not enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)
        result = []

        # Fetch warehouse based on the provided date
        data = request.env['stock.location'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No stock location found matching the criteria.")
            return request.make_response(json.dumps({"message":"No stock location found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        for location in data:
            type = ' '
            if location.usage == 'view':
                type = 'View'
            elif location.usage == 'supplier':
                type ='Vendor Location'
            elif location.usage == 'transit':
                type ='transit Location'
            elif location.usage == 'internal':
                type ='Internal Location'
            elif location.usage == 'customer':
                type ='Customer Location'
            elif location.usage == 'inventory':
                type ='Inventory Loss'
            elif location.usage == 'production':
                type ='Production'
            location_entry = {
                'OdooId': str(location.id),
                'Name': location.name,
                'ParentLocation': location.location_id.name if location.location_id else None,
                'LocationType':type,
                'Company': location.company_id.name,
                'Street': location.company_id.street,
                'City': location.company_id.city,
                'State': location.company_id.state_id.code,
                'Zip': location.company_id.zip,
                'Country': location.company_id.country_id.code,
                'TaxId': location.company_id.vat
            }

            result.append(location_entry)


        if not result:
            _logger.warning("No valid stock location with lines found.")
            return request.make_response(json.dumps({"message": 'No valid stock location found'}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        return request.make_response(json.dumps({"StockLocation": result}),
                                     headers=[('Content-Type', 'application/json')], status=200)

    @http.route('/odoo/update_location_json_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_location_json_data(self, **kwargs):
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
                locations = request.env['stock.location'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])

                if not locations:
                    existing_location = request.env['stock.location'].sudo().browse(int(odoo_id))
                    if existing_location.exists():
                        if existing_location.nhcl_tally_flag == 'y':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Location Record Create Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Location Record Create Flag value already updated'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Location Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for location in locations:
                        location.write({'nhcl_tally_flag': 'y'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id Record Location Create Flag updated successfully.'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result


