# import json
# import logging
# from datetime import datetime
# # from odoo.addons.ppts_tally_integration.controllers.api_user import validate_token
# from odoo import http
# from odoo.tests import Form
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
#
# class APIController(http.Controller):
#     @validate_token
#     @http.route("/api/create/purchase_receipt", type="json", auth="public", methods=["POST"], csrf=False)
#     def _api_create_purchase_receipt(self):
#         popup_data = json.loads(request.httprequest.data)
#         _logger.info('Importing Purchase Receipt %s' % popup_data)
#         if 'purchase_receipt' not in popup_data:
#             _logger.info('@The Tally system does not contain any purchase receipt.')
#             return
#         request.env['tally.entries'].sudo().create({
#             'number_of_entries': len(popup_data['purchase_receipt']),
#             'tally_data': popup_data,
#             'tally_entry_type': 'receipt'
#         })
#         config_setup_id = request.env['ppts.tally.integration'].search([('is_active', '=', True)], limit=1)
#         company_id = config_setup_id.company_id
#
#         module = request.env['ir.module.module'].sudo().search([('name', '=', 'ppts_tally_integration_log')])
#         if module.state == 'installed':
#             log_line = request.env['sync.master.data.log']
#             start_date = datetime.today()
#             _logger.info('Importing Start Date..: %s' % start_date)
#         bill_count = 0
#         _logger.info('@ Total Received data to create Recept from Tally to Odoo: %s' % popup_data['purchase_receipt'])
#         tally_log_ids = []
#         for rec in popup_data['purchase_receipt']:
#             try:
#                 purchase_id = request.env['purchase.order'].sudo().search([('tally_po_name', '=', rec['tally_po_name'])])
#                 if not purchase_id.picking_ids:
#                     order_line = []
#                     for line in rec['tally_receipt_line']:
#                         product_id = request.env['product.product'].sudo().search(
#                             [('tally_id', '=', line['product_id'])],
#                             limit=1)
#                         tax_val = []
#                         if 'tax_ids' in line:
#                             for tax in line['tax_ids']:
#                                 tax_name = tax['name'] + ' ' + str(tax['amount']) + ' ' + '%'
#                                 account_tax = request.env['account.tax'].sudo().search(
#                                     [('name', '=', str(tax_name)), ('type_tax_use', '=', 'purchase')], limit=1)
#                                 if not account_tax:
#                                     tax_id = request.env['account.tax'].sudo().create({
#                                         'name': str(tax_name),
#                                         'amount': float(tax['amount']),
#                                         'country_id': company_id.country_id.id,
#                                         'type_tax_use': 'purchase',
#                                         'amount_type': 'percent'
#                                     })
#                                     request.env.cr.commit()
#                                     tax_val.append(tax_id.id)
#                                 if account_tax:
#                                     tax_val.append(account_tax.id)
#                         for line_item in purchase_id.order_line:
#                             if line_item.product_id.id == product_id.id:
#                                 line_item.sudo().update({
#                                     'product_qty': line['product_qty'],
#                                     'price_unit': line['price_unit'],
#                                     'taxes_id': tax_val
#                                 })
#                             # if line_item.product_id.id != product_id.id :
#                             #     line = {
#                             #         'product_id': product_id.id,
#                             #         'product_qty': line['product_qty'],
#                             #         'price_unit': line['price_unit'],
#                             #         'taxes_id': tax_val
#                             #     }
#                             #     order_line.append((0, 0, line))
#                     purchase_id.sudo().write({
#                         'order_line': order_line
#                     })
#
#                     if not purchase_id.picking_ids:
#                         purchase_id.sudo().button_confirm()
#                 if purchase_id.picking_ids:
#                     picking_names = []
#                     for vals in purchase_id.picking_ids:
#                         if vals.state == 'assigned':
#                             vals.sudo().update({
#                                 'tally_receipt_no': rec['receipt_id'],
#                                 'tally_receipt_name': rec['receipt_name']
#                             })
#                             move_product = 0
#                             done_qty_product = 0
#                             picking_names.append(vals.name)
#                             for line in rec['tally_receipt_line']:
#                                 product_id = request.env['product.product'].sudo().search(
#                                     [('tally_id', '=', line['product_id'])],
#                                     limit=1)
#                                 for move in vals.move_ids_without_package:
#                                     move_product += 1
#                                     if move.product_id.id == product_id.id:
#                                         move.sudo().write({
#                                             'quantity': line['quantity_done']  #quantity to quantity done
#                                         })
#                                     if move.product_uom_qty == line['quantity_done']:
#                                         done_qty_product += 1
#                             # vals.button_validate()
#                             if move_product != done_qty_product:
#                                 wiz_act = vals.button_validate()
#                                 if wiz_act:
#                                     wiz = request.env[wiz_act['res_model']].sudo().with_context(
#                                         wiz_act['context'])
#                                     wiz.process()
#                             else:
#                                 vals.button_validate()
#                     if module.state == 'installed':
#                         vals = (0, 0, {
#                             'master_type': 'receipt',
#                             'sync_action': 'create',
#                             'sync_data': str(rec),
#                             'error_data': 'Purchase receipt created successfully',
#                             'name': picking_names[-1],
#                             'sync_status': 'done',
#                             'sync_for': 'trans',
#                             'tally_record_name': rec['tally_po_name'],
#                             # 'records_created_id': purchase_id.picking_ids.id,
#                             'tally_record_id': rec['receipt_id']
#                         })
#                         tally_log_ids.append(vals)
#             except Exception as e:
#                 info = "There was a problem {}".format((e))
#                 error = "Something went wrong"
#
#                 if module.state == 'installed':
#                     vals = (0, 0, {
#                         'master_type': 'receipt',
#                         'sync_action': 'create',
#                         'sync_data': str(rec),
#                         'error_data': e,
#                         'sync_status': 'fail',
#                         'sync_for': 'trans',
#                         'tally_record_name': rec['receipt_id'],
#                         # 'tally_record_id': rec['recepit_id']
#                     })
#                     tally_log_ids.append(vals)
#                     _logger.info('Log is created for the exception: %s' % tally_log_ids)
#         if tally_log_ids:
#             values = {
#                 'data_from': 'tally',
#                 'company_id': company_id.id,
#                 'trans_log_line_ids': tally_log_ids
#             }
#             tally_log_obj_id = request.env['ppts.tally.integration.log'].sudo().create(values)
#             _logger.info('@ Log is created: %s' % tally_log_obj_id)
#             request.env.cr.commit()
#             status = tally_log_obj_id.state
#             total_records_recieved = tally_log_obj_id.total_count
#             done_count = tally_log_obj_id.done_count
#             fail_count = tally_log_obj_id.fail_count
#             created_records = []
#             if done_count:
#                 for rec in tally_log_obj_id.trans_log_line_ids:
#                     if rec.sync_status == 'done':
#                         created_records.append(("TALLY ID : " + str(rec.tally_record_id) + " - " + "ODOO ID : " + str(
#                             rec.records_created_id)))
#             failed_records = []
#             if fail_count:
#                 for rec in tally_log_obj_id.trans_log_line_ids:
#                     if rec.sync_status == 'fail':
#                         failed_records.append(rec.tally_record_name)
#             return {
#                 'status': str(status),
#                 'created_records': str(created_records) if created_records else "0",
#                 'failed_records': str(failed_records) if failed_records else "0",
#                 'created_count': str(done_count) or "0",
#                 'failed_count': str(fail_count) or "0",
#                 'message': "Valid Access Token"
#             }