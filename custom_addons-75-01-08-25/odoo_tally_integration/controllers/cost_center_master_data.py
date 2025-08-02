import json
from odoo import http
from odoo.http import request,Response
import logging


_logger = logging.getLogger(__name__)

class GETCostCenters(http.Controller):
    @http.route('/odoo/api/get_cost_centers_json_data', type='http', auth='public', methods=['GET'], csrf=False)
    def get_cost_centers_json_data(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        # print(api_key)
        if not api_key:
            return request.make_response(json.dumps({"message": "Api Key is required"}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                json.dumps({"message": "Invalid Api key"}),
                headers=[('Content-Type', 'application/json')],
                status=403
            )
        result = []
        # Fetch accounts based on the provided date
        data = request.env['account.analytic.account'].sudo().search([('nhcl_tally_flag', '=', 'n')])
        # print(data)

        if not data:
            _logger.warning("No Analytic Accounts/CostCenters found matching the criteria.")
            return request.make_response(json.dumps({"message": "No CostCenters found"}),headers=[('Content-Type','application/json')],status=404)

        for center in data:
            cos_center_data = {
                'Odoo_id': str(center.id),
                'name': center.name,
                'state': center.acc_state_id.state_id.name if center.acc_state_id and center.acc_state_id.state_id else '',
                'company' : center.company_name
            }
            result.append(cos_center_data)  # Append each cos center to the result

        # If no valid accounts were appended, log and return a suitable response
        if not result:
            _logger.warning("No valid account found.")
            return request.make_response(json.dumps({"message":'No valid accounts found'}),headers=[('Content-Type', 'application/json')],
                status=404)
        # print(result)

        return request.make_response(json.dumps({"accounts": result}),headers=[('Content-Type', 'application/json')],status = 200)

    @http.route('/odoo/api/update_cost_centers_create_flag', type='http', auth='public', methods=['POST'], csrf=False)
    def update_cost_centers_create_flag(self, **kwargs):
        api_key = kwargs.get('api_key')
        if not api_key:
            api_key = request.httprequest.headers.get('x-api-key')
        print(api_key)
        if not api_key:
            return request.make_response(json.dumps({"message": "Api Key is required"}),
                                         headers=[('Content-Type', 'application/json')],
                                         status=404
                                         )

        api_access = request.env['rest.api'].sudo().search([('api_key', '=', api_key)])

        if not api_access:
            return request.make_response(
                json.dumps({"message": "Invalid Api key"}),
                headers=[('Content-Type', 'application/json')],
                status=403
            )
        result = []
        try:
            body = request.httprequest.data
            data = json.loads(body)
            odoo_id = data.get('Odoo_id')
            tally_id = data.get('Tally_id')
            # name = kwargs.get('name') or request.jsonrequest.get('name') or request.params.get('name')
            if odoo_id:
                cos_center = request.env['account.analytic.account'].sudo().search(
                    [('id', '=', int(odoo_id)), ('nhcl_tally_flag', '=', 'n')])

                if not cos_center:
                    existing_center = request.env['account.analytic.account'].sudo().browse(int(odoo_id))
                    if existing_center.exists():
                        if existing_center.tally_record_id == tally_id:
                            if existing_center.nhcl_tally_flag == 'y':
                                result = json.dumps({
                                    'status': 'success',
                                    'message': f'{int(odoo_id)} Id CosCenter Record Create Flag Already Updated successfully'
                                })
                            else:
                                result = json.dumps({
                                    'status': 'info',
                                    'message': f'{int(odoo_id)} Id CosCenter Record Create Flag value invalid'
                                })
                        else:
                            result = json.dumps({
                                'status': 'info',
                                'message': f'{int(odoo_id)} Id CosCenter Record Tally Id Not Found'
                            })
                    else:
                        result = json.dumps({
                            'status': 'info',
                            'message': f'{int(odoo_id)} Id CosCenter Record Not Found'
                        })
                else:
                    for je in cos_center:
                        je.write({'nhcl_tally_flag': 'y'})
                        je.tally_record_id = tally_id
                        result = json.dumps({
                            'status': "success",
                            'message': f'{int(odoo_id)} Id Record CosCenter Create Flag updated successfully'
                        })
        except Exception as e:
            result = json.dumps({
                'status': "error",
                'message': str(e)
            })

        return result
