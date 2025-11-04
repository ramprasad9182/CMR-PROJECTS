""" APIController class for handling Tally integration in Odoo."""
import json
import logging
from datetime import datetime
from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class APIController(http.Controller):
    """ This class defines an API controller with routes for creating Products.
    It includes methods for processing Tally data and updating Odoo records accordingly. """
    @validate_token
    @http.route("/api/create/product_product", type="json", auth="public",
                methods=["POST"], csrf=False)
    def _api_create_product_product(self):
        popup_data = json.loads(request.httprequest.data)
        _logger.info('Importing Product from tally to odoo %s',
                     popup_data)
        if 'product' not in popup_data:
            _logger.info('@The Tally system does not contain any product.')
            return
        request.env['tally.entries'].sudo().create({
            'number_of_entries': len(popup_data['product']),
            'tally_data': popup_data,
            'tally_entry_type': 'products'
        })
        config_setup_id = request.env['ppts.tally.integration'].search([
            ('is_active', '=', True)], limit=1)
        company_id = config_setup_id.company_id
        module = request.env['ir.module.module'].sudo().search([
            ('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            # log_line = request.env['sync.master.data.log']
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s', start_date)
        product_creation_count = 0
        tally_log_ids = []
        for rec in popup_data['product']:
            try:
                product_creation_count += 1
                product_id = request.env['product.product'].sudo().search([
                    ('tally_id', '=', int(rec['tally_id']))], limit=1)
                if int(rec['category_id']) == 0:
                    product_categ = request.env['product.category'].sudo().search(
                        [('name', '=', 'All')],
                        limit=1).id
                else:
                    product_categ = request.env['product.category'].sudo().search(
                        [('tally_id', '=', int(rec['category_id']))],
                        limit=1).id
                if float(rec['uom_id']) <= 0:
                    _logger.info('@ Missing the product Unit of Measure for %s product.',
                                 product_id.name)
                    continue
                uom_id = request.env['uom.uom'].sudo().search([
                    ('tally_id', '=', int(rec['uom_id']))], limit=1).id
                if not product_id:
                    tax_val = []
                    if 'tax_ids' in rec:
                        for tax in rec['tax_ids']:
                            tax_name = tax['name'] + ' ' + str(tax['amount']) + ' ' + '%'
                            account_tax = request.env['account.tax'].sudo().search([
                                ('name', '=', str(tax_name)),
                                ('type_tax_use', '=', 'sale')], limit=1)
                            if not account_tax:
                                account_tax = request.env['account.tax'].sudo().create({
                                    'company_id': company_id.id,
                                    'name': str(tax_name),
                                    'amount': float(tax['amount']),
                                    'country_id': company_id.country_id.id,
                                    'type_tax_use': 'sale',
                                    'amount_type': 'percent'
                                })
                                request.env.cr.commit()
                            tax_val.append(account_tax.id)
                    product_items = request.env['product.product'].sudo().create({
                        'name': rec['name'],
                        'detailed_type': 'product',
                        'categ_id': product_categ,
                        'uom_id': uom_id,
                        'uom_po_id': uom_id,
                        'list_price': rec['sale_price'],
                        'standard_price': rec['cost_price'],
                        'tally_id': int(rec['tally_id']),
                        # 'l10n_in_hsn_code': rec['hsn_code'],
                        'taxes_id': tax_val
                    })
                    product_temp_id = (request.env['product.template'].sudo().
                                       browse(product_items.product_tmpl_id.id))
                    product_temp_id.sudo().write({'tally_id': int(rec['tally_id'])})
                    _logger.info("product updated.", product_items)
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'products',
                            'sync_action': 'create',
                            'error_data': 'The Product has been created successfully',
                            'sync_data': str(rec),
                            'name': product_items.name,
                            'sync_status': 'done',
                            'sync_for': 'master',
                            'tally_record_name': rec['name'],
                            'records_created_id': product_items.id,
                            'tally_record_id': rec['tally_id']
                        })
                        tally_log_ids.append(vals)
                        _logger.info('Log line Created...')
                    _logger.info('@ Number of product imported: %s', product_creation_count)

                if product_id:
                    tax_val = []
                    if 'tax_ids' in rec:
                        for tax in rec['tax_ids']:
                            tax_name = tax['name'] + ' ' + str(tax['amount']) + ' ' + '%'
                            account_tax = request.env['account.tax'].sudo().search([
                                ('name', '=', str(tax_name)),
                                ('type_tax_use', '=', 'sale')], limit=1)
                            if not account_tax:
                                account_tax = request.env['account.tax'].sudo().create({
                                    'company_id': company_id.id,
                                    'name': str(tax_name),
                                    'amount': float(tax['amount']),
                                    'country_id': company_id.country_id.id,
                                    'type_tax_use': 'sale',
                                    'amount_type': 'percent'
                                })
                                request.env.cr.commit()
                            tax_val.append(account_tax.id)

                    product_id.sudo().update({
                        'categ_id': product_categ,
                        'uom_id': uom_id,
                        'list_price': rec['sale_price'],
                        'standard_price': rec['cost_price'],
                        # 'l10n_in_hsn_code': rec['hsn_code'],
                        'taxes_id': tax_val
                    })
                    if module.state == 'installed':
                        vals = (0, 0, {
                            'master_type': 'products',
                            'sync_action': 'alter',
                            'error_data': 'The Product has been updated successfully',
                            'sync_data': str(rec),
                            'name': product_id.name,
                            'sync_status': 'done',
                            'sync_for': 'master',
                            'tally_record_name': rec['name'],
                            'records_created_id': product_id.id,
                            'tally_record_id': rec['tally_id']
                        })
                        tally_log_ids.append(vals)
                        _logger.info('Log line Created...')
                    _logger.info('@ Number of product updated imported: %s', product_creation_count)

            except ImportError as e:
                # info = "There was a problem {}".format((e))
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'products',
                        'sync_action': 'create',
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'master',
                        'sync_data': str(rec),
                        'tally_record_name': rec['name'],
                        'tally_record_id': rec['tally_id']
                    })
                    tally_log_ids.append(vals)
        if tally_log_ids:
            values = {
                'data_from': 'tally',
                'company_id': company_id.id,
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
                'created_records': str(created_records) if created_records else "0",
                'failed_records': str(failed_records) if failed_records else "0",
                'created_count': str(done_count) or "0",
                'failed_count': str(fail_count) or "0",
                'message': "Valid Access Token"
            }
        return None
