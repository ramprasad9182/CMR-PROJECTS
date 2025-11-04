""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating res partner.
       It includes methods for processing Tally data and updating Odoo records accordingly."""
    @validate_token
    @http.route("/api/create/partner", type="json", auth="public", methods=["POST"], csrf=False)
    def _api_create_res_partner(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing Partner from tally to odoo %s', popup_data)
        if 'partner' not in popup_data:
            _logger.info('@The Tally system does not contain any partner.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['partner']),
            'tally_data': popup_data,
            'tally_entry_type': 'partner'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        sync_start_date = datetime.now()

        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s',start_date)
        partner_count = 0
        _logger.info('@ Total Received data to create partner from Tally to Odoo: %s',
                     popup_data['partner'])
        tally_log_ids = []
        for rec in popup_data['partner']:
            try:
                partner_count += 1
                partner_tally_id = request.env['res.partner'].sudo().search([
                    ('tally_id', '=', rec['tally_id'])])
                if not partner_tally_id:
                    country_id = request.env['res.country'].sudo().search([
                        ('name', '=', str(rec['country']))], limit=1)
                    state_id = request.env['res.country.state'].sudo().search([
                        ('name', '=', str(rec['state']))], limit=1)
                    property_account_receivable_id = ''
                    property_account_payable_id = ''
                    if rec['partner_type'] == 'customer':
                        property_account_receivable_id = request.env['account.account'].sudo().search([
                            ('tally_id', '=', int(rec['property_account_id']))], limit=1).id
                    if not property_account_receivable_id:
                        property_account_receivable_id = (request.env['ppts.tally.integration']
                                                          .sudo().search([
                            ('is_active', '=', True)], limit=1).property_recieveable.id)
                    if rec['partner_type'] == 'supplier':
                        property_account_payable_id = request.env['account.account'].sudo().search(
                            [('tally_id', '=', int(rec['property_account_id']))], limit=1).id
                    if not property_account_payable_id:
                        property_account_payable_id = (request.env['ppts.tally.integration']
                                                       .sudo().search([
                            ('is_active', '=', True)], limit=1).property_payable.id)
                    partner_type = ''
                    if rec['partner_type'] == 'other':
                        partner_type = ''
                    else:
                        partner_type = rec['partner_type']
                    partner_id = request.env['res.partner'].sudo().create({
                        'name': rec['partner_name'],
                        'type_partner': partner_type,
                        'tally_id': int(rec['tally_id']),
                        'street': rec['street'] if rec['street'] != 'NULL' else '',
                        'email': rec['email'] if rec['email'] != 'NULL' else '',
                        'zip': rec['zip'] if rec['zip'] != 'NULL' else '',
                        # 'vat': rec['vat'] if rec['vat'] != 'NULL' else '',
                        'mobile': rec['mobile'] if rec['mobile'] != 'NULL' else '',
                        'state_id': state_id.id if state_id else False,
                        'country_id': country_id.id or '',
                        'company_id': company_id,
                        'property_account_receivable_id': property_account_receivable_id,
                        'property_account_payable_id': property_account_payable_id
                    })

                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'partner',
                            'sync_action': 'create',
                            'error_data': 'The Partner has been Created from tally to Odoo ',
                            'name': partner_id.name,
                            'sync_status': 'done',
                            'sync_data': str(rec),
                            'sync_for': 'master',
                            'tally_record_name': str(rec['partner_name']),
                            'records_created_id': partner_id.id,
                            'tally_record_id': int(rec['tally_id'])
                        })
                        tally_log_ids.append(vals)
                if partner_tally_id:
                    property_account_receivable_id = ''
                    property_account_payable_id = ''
                    if rec['partner_type'] == 'customer':
                        property_account_receivable_id = (request.env['account.account'].
                                                          sudo().search([
                            ('tally_id', '=', int(rec['property_account_id']))], limit=1).id)
                    if not property_account_receivable_id:
                        property_account_receivable_id = (request.env['ppts.tally.integration'].
                                                          sudo().search([
                            ('is_active', '=', True)], limit=1).property_recieveable.id)
                    if rec['partner_type'] == 'supplier':
                        property_account_payable_id = request.env['account.account'].sudo().search(
                            [('tally_id', '=', int(rec['property_account_id']))], limit=1).id
                    if not property_account_payable_id:
                        property_account_payable_id = (request.env['ppts.tally.integration'].
                                                       sudo().search(
                            [('is_active', '=', True)], limit=1).property_payable.id)
                    country_id = (request.env['res.country'].
                                  sudo().search([
                        ('name', '=', str(rec['country']))], limit=1))
                    state_id = request.env['res.country.state'].sudo().search([
                        ('name', '=', str(rec['state']))], limit=1)
                    # if rec['partner_type'] == 'other':
                    #     partner_type = ''
                    # else:
                    #     partner_type = rec['partner_type']
                    partner_tally_id.sudo().update({
                        # 'type_partner': partner_type,
                        'street': rec['street'] if rec['street'] != 'NULL' else '',
                        'email': rec['email'] if rec['email'] != 'NULL' else '',
                        'zip': rec['zip'] if rec['zip'] != 'NULL' else '',
                        'mobile': rec['mobile'] if rec['mobile'] != 'NULL' else '',
                        'state_id': state_id.id if state_id else False,
                        'country_id': country_id.id or '',
                        # 'vat': rec['vat'],
                        'property_account_receivable_id': property_account_receivable_id,
                        'property_account_payable_id': property_account_payable_id
                    })
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'partner',
                            'sync_action': 'alter',
                            'error_data': 'The Partner has been altered from tally to Odoo ',
                            'name': partner_tally_id.name,
                            'sync_status': 'done',
                            'sync_data': str(rec),
                            'sync_for': 'master',
                            'tally_record_name': str(rec['partner_name']),
                            'records_created_id': partner_tally_id.id,
                            'tally_record_id': int(rec['tally_id'])
                        })
                        tally_log_ids.append(vals)

            except ImportError as e:
                # info = "There was a problem {}".format((e))
                # error = "Something went wrong"
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'partner',
                        'sync_action': 'create',
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'sync_data': str(rec),
                        'tally_record_name': str(rec['partner_name']),
                        'tally_record_id': int(rec['tally_id'])
                    })
                    tally_log_ids.append(vals)
        status = ''
        if tally_log_ids:
            values = {
                'sync_start_date': sync_start_date,
                'data_from': 'tally',
                'company_id': company_id,
                'trans_log_line_ids': tally_log_ids
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
                'created_records': str(created_records),
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return None
