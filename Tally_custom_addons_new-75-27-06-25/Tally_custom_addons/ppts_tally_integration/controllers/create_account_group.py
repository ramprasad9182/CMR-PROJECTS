""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ It defines routes for creating account groups and includes functions for processing
        Tally data and updating Odoo records accordingly."""
    @validate_token
    @http.route("/api/create/account_group", type="json", auth="public",
                methods=["POST"], csrf=False)
    def _api_create_account_group(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing account GROUP from tally to odoo %s',popup_data)
        config_setup_id = request.env['ppts.tally.integration'].search(
            [('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        if 'account_group' not in popup_data:
            _logger.info('@The Tally system does not contain any account group.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['account_group']),
            'tally_data': popup_data,
            'tally_entry_type': 'group'
        })
        module = request.env['ir.module.module'].sudo().search(
            [('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s',start_date)
        group_count = 0
        tally_log_ids = []
        for line in popup_data['account_group']:
            try:
                group_count += 1
                group = request.env['account.group'].sudo().search(
                    [('tally_id', '=', line['tally_id'])], limit=1)
                if not group:
                    code = '1000' + str(line['tally_id'])
                    group_id = request.env['account.group'].sudo().create(
                        {'name': line['name'],
                         'company_id': company_id,
                         'code_prefix_start': code,
                         'tally_id': line['tally_id']})
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'group',
                            'sync_action': 'create',
                            'error_data': 'The Account group has been Created from tally to Odoo ',
                            'name': group_id.name,
                            'sync_status': 'done',
                            'sync_for': 'master',
                            'sync_data': str(line),
                            'tally_record_name': line['name'],
                            'records_created_id': group_id.id,
                            'tally_record_id': line['tally_id']
                        })
                        tally_log_ids.append(vals)
                else:
                    group.sudo().update({
                        'name': line['name']
                    })
                _logger.info('@ Number of group imported: %s', group_count)
            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'group',
                        'sync_action': 'create',
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'sync_data': str(line),
                        'tally_record_name': line['name'],
                        'tally_record_id': line['tally_id']
                    })
                    tally_log_ids.append(vals)

        for line in popup_data['account_group']:
            parent_grp = request.env['account.group'].sudo().search([
                ('tally_id', '=', line['parent_id'])], limit=1)
            group = request.env['account.group'].sudo().search([
                ('tally_id', '=', line['tally_id'])], limit=1)
            parent_primary = request.env['account.group'].sudo().search([
                ('name', '=', 'All')], limit=1)
            if group and parent_grp:
                group.sudo().update({
                    'parent_id': parent_grp.id,
                    'parent_group_id': parent_grp.id
                })
            else:
                group.sudo().update({
                    'parent_id': parent_primary.id,
                    'parent_group_id': parent_primary.id
                })

        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id,
                'master_log_line_ids': tally_log_ids
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
                        created_records.append(("TALLY ID : "
                                                + str(rec.tally_record_id)
                                                + " - " + "ODOO ID : "+str(rec.records_created_id)))
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
        return None
