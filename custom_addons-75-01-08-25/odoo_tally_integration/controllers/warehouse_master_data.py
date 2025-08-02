import json
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class GETWarehouse(http.Controller):

    @http.route('/odoo/get_warehouse_data', type='http', auth='public', methods=['GET'])
    def get_warehouse_data(self, **kwargs):
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
        if not integration.warehouse_enable:
            _logger.warning("Warehouse master not enabled  in integration configuration.")
            return request.make_response(
                json.dumps({"message": "Warehouse master not enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)
        result = []

        # Fetch warehouse based on the provided date
        data = request.env['stock.warehouse'].sudo().search([('nhcl_tally_flag', '=', 'n')])

        if not data:
            _logger.warning("No warehouse found matching the criteria.")
            return request.make_response(json.dumps({"message":"No warehouse found"}),
                                         headers=[('Content-Type', 'application/json')],status=404)

        for warehouse in data:
            warehouse_entry = {
                'OdooId':str(warehouse.id),
                'Name': warehouse.name,
                'ShortName': warehouse.code,
                'Address': warehouse.partner_id.name,
                'Company': warehouse.company_id.name,
                'Street': warehouse.company_id.street,
                'City': warehouse.company_id.city,
                'State': warehouse.company_id.state_id.code,
                'Zip': warehouse.company_id.zip,
                'Country': warehouse.company_id.country_id.code,
            }

            result.append(warehouse_entry)
        if not result:
            _logger.warning("No valid warehouse with lines found.")
            return request.make_response(json.dumps({"message": 'No valid warehouse found'}),
                                         headers=[('Content-Type', 'application/json')], status=404)

        return request.make_response(json.dumps({"Warehouse": result}),
                                     headers=[('Content-Type', 'application/json')], status=200)

    @http.route('/odoo/update_warehouse_data', type='http', auth='public', methods=['POST'], csrf=False)
    def update_warehouse_data(self, **kwargs):
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
        if not integration.warehouse_enable:
            _logger.warning("Warehouse master not enabled  in integration configuration.")
            return request.make_response(
                json.dumps({"message": "Warehouse master not enabled in integration settings"}),
                headers=[('Content-Type', 'application/json')], status=400)
        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')

            if odoo_id:
                # Fetch company based on the provided name
                warehouses = request.env['stock.warehouse'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])

                if not warehouses:
                    existing_warehouse= request.env['stock.warehouse'].sudo().browse(int(odoo_id))
                    if existing_warehouse.exists():
                        if existing_warehouse.nhcl_tally_flag == 'y':
                            result = json.dumps({
                                'status': 'success',
                                'message': f'{int(odoo_id)} Id Warehouse Record Create Flag Already Updated successfully'
                            })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id Warehouse Record Create Flag value already updated'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id Warehouse Record Not Found'
                        })
                else:
                    # Assuming the flag is a boolean field named 'nhcl_tally_flag'
                    for warehouse in warehouses:
                        warehouse.write({'nhcl_tally_flag': 'y'})
                        result = json.dumps({
                            'status': 'success',
                            'message': f'{int(odoo_id)} Id Record Warehouse Create Flag updated successfully.'
                        })
        except Exception as e:
            result = json.dumps({
                'status': 'error',
                'message': str(e)
            })
        return result


