""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating account groups.
    It includes methods for processing Tally data and updating Odoo records accordingly. """
    @validate_token
    @http.route("/api/create/product_category", type="json", auth="public", methods=["POST"],
                csrf=False)
    def _api_create_product_category(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing Product Category from tally to odoo %s', popup_data)
        if 'product_category' not in popup_data:
            _logger.info('@The Tally system does not contain any product category.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['product_category']),
            'tally_data': popup_data,
            'tally_entry_type': 'prod_categ'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        categ_count = 0
        tally_log_ids = []
        for rec in popup_data['product_category']:
            try:
                categ_count += 1
                product_catg_id = request.env['product.category'].sudo().search([
                    ('tally_id', '=', int(rec['tally_id']))], limit=1)
                if not product_catg_id:
                    product_category = request.env['product.category'].sudo().create({
                        'name': rec['name'],
                        'tally_id': int(rec['tally_id']),
                    })
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'prod_categ',
                            'sync_action': 'create',
                            'error_data': 'The Product Category has been Created '
                                          'from tally to Odoo ',
                            'name': product_category.name,
                            'sync_status': 'done',
                            'sync_for': 'master',
                            'sync_data': str(rec),
                            'tally_record_name': rec['name'],
                            'records_created_id': product_category.id,
                            'tally_record_id': rec['tally_id']
                        })
                        tally_log_ids.append(vals)
                _logger.info('@ Number of Product Category imported: %s', categ_count)
            except ImportError as e:
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'prod_categ',
                        'sync_action': 'create',
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'sync_data': str(rec),
                        'tally_record_name': rec['name'],
                        'tally_record_id': rec['tally_id']
                    })
                    tally_log_ids.append(vals)

        for rec in popup_data['product_category']:
            product_catg_id = request.env['product.category'].sudo().search([
                ('tally_id', '=', int(rec['tally_id']))], limit=1)
            parent_id = request.env['product.category'].sudo().search([
                ('tally_id', '=', int(rec['parent_id']))], limit=1)
            parent_primary = request.env['product.category'].sudo().search([
                ('name', '=', 'All')], limit=1)

            if product_catg_id and parent_id:
                product_catg_id.sudo().update({
                    'parent_id': parent_id.id
                })
            else:
                product_catg_id.sudo().update({
                    'parent_id': parent_primary.id
                })
        status = ''
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id,
                'trans_log_line_ids': tally_log_ids
            }
            tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
            _logger.info('@ Log is created: %s', tally_log_obj_id)
            request.env.cr.commit()
            status = tally_log_obj_id.state
            # total_records_recieved = tally_log_obj_id.total_count
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : " +
                                                str(rec.tally_record_id) +
                                                " - " + "ODOO ID : " +
                                                str(rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.master_log_line_ids:
                    if rec.sync_status == 'fail':
                        failed_records.append(rec.tally_record_name)

            return {
                'status': str(status),
                'created_records': str(created_records),
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return None
