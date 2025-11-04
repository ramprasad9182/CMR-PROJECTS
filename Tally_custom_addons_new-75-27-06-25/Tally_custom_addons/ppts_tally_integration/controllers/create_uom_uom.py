""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class APIController(http.Controller):
    """This class defines an API controller with routes for creating Product UOM.
    It includes methods for processing Tally data and updating Odoo records accordingly."""
    @validate_token
    @http.route("/api/create/product_uom", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_product_uom(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing product UOM from tally to odoo %s', popup_data)
        if 'uom' not in popup_data:
            _logger.info('@The Tally system does not contain any unit of measure.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['uom']),
            'tally_data': popup_data,
            'tally_entry_type': 'uom'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s',start_date)
        uom_count = 0
        tally_log_ids = []
        for rec in popup_data['uom']:
            try:
                _logger.info('@ Received data to create UOM from Tally to Odoo: %s', rec)
                uom_categ_id = request.env['uom.category'].sudo().search([
                    ('tally_id', '=', int(rec['tally_id']))], limit=1)
                if not uom_categ_id:
                    uom_categ_id = request.env['uom.category'].sudo().create({
                        'name': rec['category_name'],
                        'tally_id': int(rec['tally_id']),
                        'uom_ids': [(0, 0, {
                            'name': rec['uom_name'],
                            'tally_id': int(rec['tally_id']),
                        })]
                    })
                    uom_count += 1
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'uom',
                            'sync_action': 'create',
                            'sync_data': str(rec),
                            'error_data': 'The UOM has been Created from tally to Odoo ',
                            'name': uom_categ_id.name,
                            'sync_status': 'done',
                            'sync_for': 'master',
                            'tally_record_name': rec['category_name'],
                            'records_created_id': uom_categ_id.id,
                            'tally_record_id': int(rec['tally_id'])
                        })
                        tally_log_ids.append(vals)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'uom',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'tally_record_name': rec['category_name'],
                        'tally_record_id': rec['tally_id']
                    })
                    tally_log_ids.append(vals)
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id,
                'master_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s',tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
            # total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : "
                                                + str(rec.tally_record_id)
                                                + " - " + "ODOO ID : "
                                                + str(rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'fail':
                        failed_records.append(rec.tally_record_name)

            return {
                'status': str(status),
                'created_records': str(created_records) if created_records else "0",
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return True
