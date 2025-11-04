""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.tests import Form
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating Internal Transfer.
        It includes methods for processing Tally data and updating Odoo records accordingly. """
    def create_stock_location(self, rec, company_id):
        """create the source and destination location for stock internal transfer order """
        location_id = request.env['stock.location'].sudo().search(
            [('name', '=', 'WH'), ('usage', '=', 'view')])
        source_location_id = request.env['stock.location'].sudo().search(
            [('tally_id', '=', int(rec['source_location_id'])), ('usage', '=', 'internal')])
        destination_location_id = request.env['stock.location'].sudo().search(
            [('tally_id', '=', int(rec['destination_location_id'])), ('usage', '=', 'internal')])
        if not source_location_id:
            source_location_id = request.env['stock.location'].sudo().create({
                'name': str(rec['source_location_name']),
                'tally_id': int(rec['source_location_id']),
                'usage': 'internal',
                'location_id': location_id.id,
                'company_id': company_id,
            })
        if not destination_location_id:
            destination_location_id = request.env['stock.location'].sudo().create({
                'name': str(rec['destination_location_name']),
                'tally_id': int(rec['destination_location_id']),
                'usage': 'internal',
                'location_id': location_id.id,
                'company_id': company_id,
            })
        location_id = {
            'destination_location_id': destination_location_id,
            'source_location_id': source_location_id
        }
        return location_id

    def search_stock_location(self, rec, company_id):
        """Search the source and destination location for stock internal transfer order """
        location_id = self.create_stock_location(rec, company_id)
        location_name = location_id['source_location_id'].name + ' -> ' + location_id[
            'destination_location_id'].name
        location_code = (location_id['source_location_id'].name[:2] +
                         location_id['destination_location_id'].name[:2])
        picking_code_id = request.env['stock.picking.type'].sudo().search(
            [('sequence_code', 'ilike', location_code.upper())])
        picking_type_id = request.env['stock.picking.type'].sudo().search(
            [('code', '=', 'internal'), ('company_id', '=', company_id),
             ('default_location_dest_id.company_id', '=', company_id),
             ('default_location_src_id.company_id', '=', company_id),
             ('default_location_dest_id', '=', location_id['destination_location_id'].id),
             ('default_location_src_id', '=', location_id['source_location_id'].id)])
        if not picking_type_id:
            if picking_code_id.sequence_code == location_code.upper():
                location_code = (location_id['source_location_id'].name[-2:] +
                                 location_id['destination_location_id'].name[-2:])
            picking_type_id = request.env['stock.picking.type'].sudo().create({
                'name': location_name,
                'code': 'internal',
                'company_id': company_id,
                'sequence_code': location_code.upper(),
                'default_location_src_id': location_id['source_location_id'].id,
                'default_location_dest_id': location_id['destination_location_id'].id
            })
        return picking_type_id

    # def create_order_partner(self, rec, company_id):
    #     """create the partner for stock internal transfer order """
    #     if 'partner_id' in rec:
    #         partner_id = request.env['res.partner'].sudo().search(
    #             [('tally_id', '=', rec['partner_id'])], limit=1)
    #         if not partner_id:
    #             country_id = request.env['res.country'].sudo().search([
    #                 ('name', '=', str(rec['country']))], limit=1)
    #             state_id = request.env['res.country.state'].sudo().search([
    #                 ('name', '=', str(rec['state']))], limit=1)
    #             partner_id = request.env['res.partner'].sudo().create({
    #                 'name': rec['partner_name'],
    #                 'type_partner': 'supplier',
    #                 'tally_id': int(rec['partner_id']),
    #                 'street': rec['street'],
    #                 'email': rec['email'],
    #                 'state_id': state_id.id or '',
    #                 'country_id': country_id.id or '',
    #                 'company_id': company_id
    #             })
    #         return partner_id


    @validate_token
    @http.route("/api/create/stock_internal_transfer", type="json", auth="public",
                methods=["POST"], csrf=False)
    def _api_create_stock_internal_transfer(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Data Received from tally to create stock transfer %s', popup_data)
        if 'stock_transfer' not in popup_data:
            _logger.info('@The Tally system does not contain any stock transfer.')
            return
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id.id
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['stock_transfer']),
            'tally_data': popup_data,
            'tally_entry_type': 'stock_transfer'
        })
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        _logger.info('@ Total Received data to create stock transfer from Tally to Odoo: %s',
                     popup_data['stock_transfer'])
        tally_log_ids = []
        for rec in popup_data['stock_transfer']:
            try:
                stock_picking_id = request.env['stock.picking'].sudo().search(
                    [('tally_receipt_no', '=', rec['internal_trans_id'])])
                if not stock_picking_id:
                    # partner_id = self.create_order_partner(rec, company_id)
                    picking_type_id = self.search_stock_location(rec, company_id)
                    date = datetime.strptime(rec['date'], '%d-%m-%Y')
                    date_val = date.strftime('%Y-%m-%d')
                    internal_line = []
                    for line in rec['tally_internal_line']:
                        product_id = request.env['product.product'].sudo().search([
                            ('tally_id', '=', int(line['product_id']))], limit=1)
                        if product_id:
                            vals = (0, 0, {
                                'name': product_id.name,
                                'product_id': product_id.id,
                                'quantity_done': float(line['quantity_done']),
                                'product_uom_qty': float(line['product_demand_qty']),
                                'location_id': picking_type_id.default_location_src_id.id,
                                'location_dest_id': picking_type_id.default_location_dest_id.id,
                            })
                            internal_line.append(vals)
                    if internal_line:
                        stock_internal_id = request.env['stock.picking'].sudo().create({
                            'partner_id': False,
                            'tally_receipt_name': rec['internal_trans_name'],
                            'tally_receipt_no': rec['internal_trans_id'],
                            'picking_type_id': picking_type_id.id,
                            'scheduled_date': date_val,
                            'location_id': picking_type_id.default_location_src_id.id,
                            'location_dest_id': picking_type_id.default_location_dest_id.id,
                            'move_ids_without_package': internal_line
                        })
                        # stock_internal_id.action_set_quantities_to_reservation()
                        action = stock_internal_id.button_validate()
                        if action:
                            wizard = Form(request.env[action['res_model']].with_context
                                          (action['context']))
                            wizard.save().process_cancel_backorder()
                        stock_internal_id.date_done = date_val
                        if module.state == 'installed':
                            vals = (0, 0, {
                                'master_type': 'stock_transfer',
                                'sync_action': 'create',
                                'sync_data': str(rec),
                                'error_data': 'Stock Transfer created successfully',
                                'name': stock_internal_id.name,
                                'sync_status': 'done',
                                'sync_for': 'trans',
                                'tally_record_name': rec['internal_trans_name'],
                                'records_created_id': stock_internal_id.id,
                                'tally_record_id': rec['internal_trans_id']
                            })
                            tally_log_ids.append(vals)
            except ImportError as e:
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'stock_transfer',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['internal_trans_name'],
                        'tally_record_id': rec['internal_trans_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)
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
            done_count = tally_log_obj_id.done_count
            fail_count = tally_log_obj_id.fail_count
            created_records = []
            if done_count:
                for rec in tally_log_obj_id.trans_log_line_ids:
                    if rec.sync_status == 'done':
                        created_records.append(("TALLY ID : " +
                                                str(rec.tally_record_id) +
                                                " - " + "ODOO ID : " +
                                                str(rec.records_created_id)))
            failed_records = []
            if fail_count:
                for rec in tally_log_obj_id.trans_log_line_ids:
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
