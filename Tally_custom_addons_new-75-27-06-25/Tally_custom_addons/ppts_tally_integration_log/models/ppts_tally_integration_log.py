from datetime import datetime
import json
import logging
from odoo.exceptions import UserError
from odoo import api, fields, models
CreationAlterType = [('none', 'None'), ('odoo', 'Odoo to Tally'), ('tally', 'Tally to Odoo')]
_logger = logging.getLogger(__name__)


class PptsTallyIntegrationLog(models.Model):
    """ PPTS Tally Integration Log File,It collects data from both
        Tally entries and Odoo entries."""
    _name = "ppts.tally.integration.log"
    _description = "Tally Integration Tool Log"
    _rec_name = 'name'

    name = fields.Char(string='Sequence', store=True,
                       readonly=True)
    created_date = fields.Date(string='Created On',
                               default=lambda self: fields.Date.today(),
                               store=True, readonly=True)
    sync_start_date = fields.Datetime(string='Sync From',
                                      default=fields.Datetime.now,
                                      readonly=True, store=True)
    sync_end_date = fields.Datetime(string='Sync To',
                                    default=fields.Datetime.now,
                                    readonly=True, store=True)
    company_id = fields.Many2one('res.company',
                                 string='Company', readonly=True)
    data_from = fields.Selection([('tally', 'Tally to Odoo'),
                                  ('odoo', 'Odoo to Tally')],
                                 string="Data From", readonly=True)
    sync_config_id = fields.Many2one('ppts.tally.integration',
                                     string='Sync Configuration',
                                     store=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User',
                              readonly=True)
    state = fields.Selection([('draft', 'No Records'), ('partial', 'Partially Done'),
                              ('fail', 'Failed'), ('done', 'Completed')],
                             string="Status", default='draft', readonly=True)
    active = fields.Boolean(default=True, readonly=True)
    fail_count = fields.Integer(compute="_compute_log_count", string='Failure',
                                copy=False, default=0, store=True, readonly=True)
    done_count = fields.Integer(compute="_compute_log_count", string='Done',
                                copy=False, default=0, store=True, readonly=True)
    total_count = fields.Integer(compute="_compute_log_count", string='Total Records',
                                 copy=False, default=0, readonly=True, store=True)
    master_log_line_ids = fields.One2many('sync.master.data.log', 'sync_log_id',
                                          domain=[('sync_for', '=', 'master')], readonly=True)
    trans_log_line_ids = fields.One2many('sync.master.data.log', 'sync_log_id',
                                         domain=[('sync_for', '=', 'trans')], readonly=True)

    @api.depends('master_log_line_ids', 'trans_log_line_ids',
                 'sync_end_date', 'master_log_line_ids.sync_status')
    def _compute_log_count(self):
        """The count of Done and Fail log entries has been calculated."""
        for logg in self:
            done = self.env['sync.master.data.log'].search(
                [('sync_log_id', '=', logg.id), ('sync_status', '=', 'done')])
            fail = self.env['sync.master.data.log'].search(
                [('sync_log_id', '=', logg.id), ('sync_status', '=', 'fail')])
            logg.done_count = len(done.ids)
            logg.fail_count = len(fail.ids)
            logg.total_count = logg.done_count + logg.fail_count
            if logg.total_count:
                if logg.fail_count == logg.total_count:
                    logg.state = 'fail'
                elif logg.done_count == logg.total_count:
                    logg.state = 'done'
                else:
                    logg.state = 'partial'
            else:
                logg.state = 'draft'

    def log_count_fail(self):
        """ The Failed Tally Entries are shown in the smart button"""
        return {
            'name': 'Odoo Sync Log',
            'view_mode': 'tree',
            'res_model': 'sync.master.data.log',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ppts_tally_integration_log.ppts_tally_integration_sync_master_log_tree').id,
            'domain': [('sync_log_id', '=', self.id), ('sync_status', '=', 'fail')],
            'context': {
                'expand': True,
                'create': 0
            }
        }

    def log_count_done(self):
        """The recorded Done Tally Entries is displayed on the smart button."""
        return {
            'name': 'Odoo Sync Log',
            'view_mode': 'tree',
            'res_model': 'sync.master.data.log',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ppts_tally_integration_log.ppts_tally_integration_sync_master_log_tree').id,
            'domain': [('sync_log_id', '=', self.id), ('sync_status', '=', 'done')],
            'context': {
                'expand': True,
                'create': 0
            }
        }

    @api.model_create_multi
    def create(self, values):
        """The sequence of recording from Tally to ODDO and from ODOO to Tally."""
        _logger.info('Values before Create:%s', values)
        res = super(PptsTallyIntegrationLog, self).create(values)
        if not res.name:
            if res.data_from == 'tally':
                res.name = self.env['ir.sequence'].next_by_code('tally.odoo.create.log.seq') or '/'
            if res.data_from == 'odoo':
                res.name = self.env['ir.sequence'].next_by_code('odoo.tally.create.log.seq') or '/'
        return res

    def show_logs_detailed_tree(self):
        """ The button displays the number of entries marked as Total Fail and Done."""
        return {
            'name': 'Odoo Sync Log',
            'view_mode': 'tree,form',
            'res_model': 'sync.master.data.log',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('ppts_tally_integration_log.ppts_tally_integration_sync_master_log_tree').id,
            'domain': [('sync_log_id', '=', self.id)],
                'group_by': 'sync_status',
                'expand': True,
                'create': 0
            }


    def show_logs_detailed_list(self):
        # Dummy implementation, you can improve this later
        return True

    # def get_value_of_created_records(self):
    #     """ Tally to Odoo Created Records are shown in the smart button."""
    #     account_group, account_coa, partners, stock_uom, product_categ, product_templ = [], [], [], [], [], []
    #     entries, internal_transfers = [], []
    #     purchase_orders, receipt_orders, in_invoices, in_refunds, in_payment = [], [], [], [], []
    #     sale_orders, delivery_orders, out_invoices, out_refunds, out_payment = [], [], [], [], []
    #     records = self.env["sync.master.data.log"].sudo().search([('sync_log_id', '=', self.id),
    #                                                               ('sync_status', '=', 'done')])
    #     for rec in records:
    #         if rec.master_type == 'group':
    #             account_group_ids = self.env['account.group'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in account_group_ids:
    #                 account_group.append(res.id)
    #         if rec.master_type == 'coa':
    #             account_ids = self.env['account.account'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in account_ids:
    #                 account_coa.append(res.id)
    #         if rec.master_type == 'partner':
    #             partner_id = self.env['res.partner'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in partner_id:
    #                 partners.append(res.id)
    #
    #         if rec.master_type == 'uom':
    #             uom_ids = self.env['uom.category'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in uom_ids:
    #                 stock_uom.append(res.id)
    #         if rec.master_type == 'prod_categ':
    #             product_categ_ids = self.env['product.category'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in product_categ_ids:
    #                 product_categ.append(res.id)
    #         if rec.master_type == 'products':
    #             product_templ_ids = self.env['product.template'].sudo().search(
    #                 [('tally_id', '=', rec.tally_record_id)])
    #             for res in product_templ_ids:
    #                 product_templ.append(res.id)
    #
    #         if rec.master_type == 'entry':
    #             journal_entry = self.env['account.move'].sudo().search(
    #                 [('tally_journal_id', '=', rec.tally_record_id), ('move_type', '=', 'entry')])
    #             for res in journal_entry:
    #                 entries.append(res.id)
    #
    #         if rec.master_type == 'stock_transfer':
    #             internal_transfer_ids = self.env['stock.picking'].sudo().search(
    #                 [('tally_receipt_no', '=', rec.tally_record_id),
    #                  ('picking_type_code', '=', 'internal')])
    #             for res in internal_transfer_ids:
    #                 internal_transfers.append(res.id)
    #
    #         if rec.master_type == 'purchase_order':
    #             purchase_order_ids = self.env['purchase.order'].sudo().search(
    #                 [('tally_po_id', '=', rec.tally_record_id)])
    #             for res in purchase_order_ids:
    #                 purchase_orders.append(res.id)
    #
    #         if rec.master_type == 'receipt':
    #             receipt_order_ids = self.env['stock.picking'].sudo().search(
    #                 [('tally_receipt_no', '=', rec.tally_record_id),
    #                  ('picking_type_code', '=', 'incoming')])
    #             for res in receipt_order_ids:
    #                 receipt_orders.append(res.id)
    #
    #         if rec.master_type == 'in_invoice':
    #             in_invoice = self.env['account.move'].sudo().search(
    #                 [('tally_bill_id', '=', rec.tally_record_id), ('move_type', '=', 'in_invoice')])
    #             for res in in_invoice:
    #                 in_invoices.append(res.id)
    #
    #         if rec.master_type == 'in_refund':
    #             in_refund = self.env['account.move'].sudo().search(
    #                 [('tally_debit_id', '=', rec.tally_record_id), ('move_type', '=', 'in_refund')])
    #             for res in in_refund:
    #                 in_refunds.append(res.id)
    #
    #         if rec.master_type == 'in_payment':
    #             in_payment_ids = self.env['account.payment'].sudo().search(
    #                 [('tally_payment_id', '=', rec.tally_record_id), ('partner_type', '=', 'supplier'),
    #                  ('is_internal_transfer', '=', False)])
    #             for res in in_payment_ids:
    #                 in_payment.append(res.id)
    #
    #         if rec.master_type == 'sale_order':
    #             sale_orders_ids = self.env['sale.order'].sudo().search(
    #                 [('tally_so_id', '=', rec.tally_record_id)])
    #             for res in sale_orders_ids:
    #                 sale_orders.append(res.id)
    #
    #         if rec.master_type == 'delievry':
    #             delivery_orders_ids = self.env['stock.picking'].sudo().search(
    #                 [('tally_receipt_no', '=', rec.tally_record_id),
    #                  ('picking_type_code', '=', 'outgoing')])
    #             for res in delivery_orders_ids:
    #                 delivery_orders.append(res.id)
    #
    #         if rec.master_type == 'out_invoice':
    #             out_invoice_ids = self.env['account.move'].sudo().search(
    #                 [('tally_invoice_id', '=', rec.tally_record_id), ('move_type', '=', 'out_invoice')])
    #             for res in out_invoice_ids:
    #                 out_invoices.append(res.id)
    #
    #         if rec.master_type == 'out_refund':
    #             out_refund = self.env['account.move'].sudo().search(
    #                 [('tally_credit_id', '=', rec.tally_record_id), ('move_type', '=', 'out_refund')])
    #             for res in out_refund:
    #                 out_refunds.append(res.id)
    #
    #         if rec.master_type == 'out_payment':
    #             in_payment_ids = self.env['account.payment'].sudo().search(
    #                 [('tally_payment_id', '=', rec.tally_record_id), ('partner_type', '=', 'customer'),
    #                  ('is_internal_transfer', '=', False)])
    #             for res in in_payment_ids:
    #                 in_payment.append(res.id)
    #     created_record_data = {
    #         'account_group': account_group,
    #         'account_coa': account_coa,
    #         'partners': partners,
    #         'stock_uom': stock_uom,
    #         'product_categ': product_categ,
    #         'product_templ': product_templ,
    #         'entries': entries,
    #         'internal_transfers': internal_transfers,
    #         'purchase_orders': purchase_orders,
    #         'receipt_orders': receipt_orders,
    #         'in_invoices': in_invoices,
    #         'in_refunds': in_refunds,
    #         'in_payment': in_payment,
    #         'sale_orders': sale_orders,
    #         'delivery_orders': delivery_orders,
    #         'out_invoices': out_invoices,
    #         'out_refunds': out_refunds,
    #         'out_payment': out_payment,
    #     }
    #     return created_record_data
    #
    #
    # def show_created_records_account_group(self):
    #     """."""
    #     account_group = self.get_value_of_created_records()['account_group']
    #     if account_group:
    #         tree_id = self.env.ref('account.view_account_group_tree').id
    #         form_id = self.env.ref('account.view_account_group_form').id
    #         return {
    #             'name': 'Account group Created in Odoo from Tally',
    #             'view_mode': 'tree',
    #             'view_type': 'form',
    #             'res_model': 'account.group',
    #             'type': 'ir.actions.act_window',
    #             'view_id': tree_id,
    #             'views': [(tree_id, 'tree'), (form_id, 'form')],
    #             'domain': [('id', 'in', account_group)],
    #             'context': {
    #                 'expand': True,
    #                 'create': 0
    #             }
    #         }
    #
    # def show_created_records_account_coa(self):
    #     """."""
    #     account_coa = self.get_value_of_created_records()['account_coa']
    #     if account_coa:
    #         tree_id = self.env.ref('account.view_account_list').id
    #         form_id = self.env.ref('account.view_account_form').id
    #         return {
    #             'name': 'Account COA Created in Odoo from Tally',
    #             'view_mode': 'tree',
    #             'view_type': 'form',
    #             'res_model': 'account.account',
    #             'type': 'ir.actions.act_window',
    #             'view_id': tree_id,
    #             'views': [(tree_id, 'tree'), (form_id, 'form')],
    #             'domain': [('id', 'in', account_coa)],
    #             'context': {
    #                 'expand': True,
    #                 'create': 0
    #             }
    #         }
    #
    # def show_created_records(self):
    #     """."""
    #     account_group = self.show_created_records_account_group()
    #     account_coa = self.show_created_records_account_coa()
    #     return account_group or account_coa

    def show_created_records(self):
        """ Tally to Odoo Created Records are shown in the smart button."""
        account_group = []
        account_coa = []
        partners = []
        stock_uom = []
        product_categ = []
        product_templ = []
        entries = []
        internal_transfers = []
        purchase_orders = []
        receipt_orders = []
        in_invoices = []
        in_refunds = []
        in_payment = []
        sale_orders = []
        delivery_orders = []
        out_invoices = []
        out_refunds = []
        out_payment = []

        records = self.env["sync.master.data.log"].sudo().search([('sync_log_id', '=', self.id),
                                                                  ('sync_status', '=', 'done')])
        for rec in records:
            if rec.master_type == 'group':
                account_group_ids = self.env['account.group'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in account_group_ids:
                    account_group.append(res.id)
            if rec.master_type == 'coa':
                account_ids = self.env['account.account'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in account_ids:
                    account_coa.append(res.id)
            if rec.master_type == 'partner':
                partner_id = self.env['res.partner'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in partner_id:
                    partners.append(res.id)

            if rec.master_type == 'uom':
                uom_ids = self.env['uom.category'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in uom_ids:
                    stock_uom.append(res.id)
            if rec.master_type == 'prod_categ':
                product_categ_ids = self.env['product.category'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in product_categ_ids:
                    product_categ.append(res.id)
            if rec.master_type == 'products':
                product_templ_ids = self.env['product.template'].sudo().search(
                    [('tally_id', '=', rec.tally_record_id)])
                for res in product_templ_ids:
                    product_templ.append(res.id)

            if rec.master_type == 'entry':
                journal_entry = self.env['account.move'].sudo().search(
                    [('tally_journal_id', '=', rec.tally_record_id), ('move_type', '=', 'entry')])
                for res in journal_entry:
                    entries.append(res.id)

            if rec.master_type == 'stock_transfer':
                internal_transfer_ids = self.env['stock.picking'].sudo().search(
                    [('tally_receipt_no', '=', rec.tally_record_id),
                     ('picking_type_code', '=', 'internal')])
                for res in internal_transfer_ids:
                    internal_transfers.append(res.id)

            if rec.master_type == 'purchase_order':
                purchase_order_ids = self.env['purchase.order'].sudo().search(
                    [('tally_po_id', '=', rec.tally_record_id)])
                for res in purchase_order_ids:
                    purchase_orders.append(res.id)

            if rec.master_type == 'receipt':
                receipt_order_ids = self.env['stock.picking'].sudo().search(
                    [('tally_receipt_no', '=', rec.tally_record_id),
                     ('picking_type_code', '=', 'incoming')])
                for res in receipt_order_ids:
                    receipt_orders.append(res.id)

            if rec.master_type == 'in_invoice':
                in_invoice = self.env['account.move'].sudo().search(
                    [('tally_bill_id', '=', rec.tally_record_id), ('move_type', '=', 'in_invoice')])
                for res in in_invoice:
                    in_invoices.append(res.id)

            if rec.master_type == 'in_refund':
                in_refund = self.env['account.move'].sudo().search(
                    [('tally_debit_id', '=', rec.tally_record_id), ('move_type', '=', 'in_refund')])
                for res in in_refund:
                    in_refunds.append(res.id)

            if rec.master_type == 'in_payment':
                in_payment_ids = self.env['account.payment'].sudo().search(
                    [('tally_payment_id', '=', rec.tally_record_id), ('partner_type', '=', 'supplier'),
                     ('is_internal_transfer', '=', False), ('payment_type', '=', 'outbound')])
                for res in in_payment_ids:
                    in_payment.append(res.id)

            if rec.master_type == 'sale_order':
                sale_orders_ids = self.env['sale.order'].sudo().search(
                    [('tally_so_id', '=', rec.tally_record_id)])
                for res in sale_orders_ids:
                    sale_orders.append(res.id)

            if rec.master_type == 'delievry':
                delivery_orders_ids = self.env['stock.picking'].sudo().search(
                    [('tally_receipt_no', '=', rec.tally_record_id),
                     ('picking_type_code', '=', 'outgoing')])
                for res in delivery_orders_ids:
                    delivery_orders.append(res.id)

            if rec.master_type == 'out_invoice':
                out_invoice_ids = self.env['account.move'].sudo().search(
                    [('tally_invoice_id', '=', rec.tally_record_id), ('move_type', '=', 'out_invoice')])
                for res in out_invoice_ids:
                    out_invoices.append(res.id)

            if rec.master_type == 'out_refund':
                out_refund = self.env['account.move'].sudo().search(
                    [('tally_credit_id', '=', rec.tally_record_id), ('move_type', '=', 'out_refund')])
                for res in out_refund:
                    out_refunds.append(res.id)

            if rec.master_type == 'out_payment':
                out_payment_ids = self.env['account.payment'].sudo().search(
                    [('tally_payment_id', '=', rec.tally_record_id), ('partner_type', '=', 'customer'),
                     ('is_internal_transfer', '=', False), ('payment_type', '=', 'inbound')])
                for res in out_payment_ids:
                    out_payment.append(res.id)

        if account_group:
            tree_id = self.env.ref('account.view_account_group_tree').id
            form_id = self.env.ref('account.view_account_group_form').id
            return {
                'name': 'Account group Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.group',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', account_group)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if account_coa:
            tree_id = self.env.ref('account.view_account_list').id
            form_id = self.env.ref('account.view_account_form').id
            return {
                'name': 'Account COA Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.account',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', account_coa)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if partners:
            tree_id = self.env.ref('base.view_partner_tree').id
            form_id = self.env.ref('base.view_partner_form').id
            kanban_id = self.env.ref('base.res_partner_kanban_view').id
            return {
                'name': 'Partner Created in Odoo from Tally',
                'view_mode': 'kanban',
                'view_type': 'form',
                'res_model': 'res.partner',
                'type': 'ir.actions.act_window',
                'view_id': kanban_id,
                'views': [(kanban_id, 'kanban'), (form_id, 'form'), (tree_id, 'tree')],
                'domain': [('id', 'in', partners)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if stock_uom:
            tree_id = self.env.ref('uom.product_uom_categ_tree_view').id
            form_id = self.env.ref('uom.product_uom_categ_form_view').id
            return {
                'name': 'UOM Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'uom.category',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', stock_uom)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if product_categ:
            tree_id = self.env.ref('product.product_category_list_view').id
            form_id = self.env.ref('product.product_category_form_view').id
            return {
                'name': 'Product Category Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'product.category',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', product_categ)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if product_templ:
            tree_id = self.env.ref('product.product_template_tree_view').id
            form_id = self.env.ref('product.product_template_only_form_view').id
            kanban_id = self.env.ref('product.product_template_kanban_view').id
            return {
                'name': 'Product is Created in Odoo from Tally',
                'view_mode': 'kanban',
                'view_type': 'form',
                'res_model': 'product.template',
                'type': 'ir.actions.act_window',
                'view_id': kanban_id,
                'views': [(kanban_id, 'kanban'), (form_id, 'form'), (tree_id, 'tree')],
                'domain': [('id', 'in', product_templ)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if entries:
            tree_id = self.env.ref('account.view_move_tree').id
            form_id = self.env.ref('account.view_move_form').id
            return {
                'name': 'journal Entries Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', entries)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if internal_transfers:
            tree_id = self.env.ref('stock.vpicktree').id
            form_id = self.env.ref('stock.view_picking_form').id
            return {
                'name': 'Stock Transfer Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', internal_transfers)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if purchase_orders:
            tree_id = self.env.ref('purchase.purchase_order_kpis_tree').id
            form_id = self.env.ref('purchase.purchase_order_form').id
            return {
                'name': 'Purchase Order has been Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', purchase_orders)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if receipt_orders:
            tree_id = self.env.ref('stock.vpicktree').id
            form_id = self.env.ref('stock.view_picking_form').id
            return {
                'name': 'Receipt Order Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', receipt_orders)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if in_invoices:
            tree_id = self.env.ref('account.view_in_invoice_bill_tree').id
            form_id = self.env.ref('account.view_move_form').id
            return {
                'name': 'Purchase Bill Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', in_invoices)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if in_refunds:
            tree_id = self.env.ref('account.view_in_invoice_refund_tree').id
            form_id = self.env.ref('account.view_move_form').id
            return {
                'name': 'Purchase Refund Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', in_refunds)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if in_payment:
            tree_id = self.env.ref('account.view_account_payment_tree').id
            form_id = self.env.ref('account.view_account_payment_form').id
            return {
                'name': 'Vendor Payments Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', in_payment)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if sale_orders:
            tree_id = self.env.ref('sale.view_quotation_tree_with_onboarding').id
            form_id = self.env.ref('sale.view_order_form').id
            return {
                'name': 'Sale Order has been Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', sale_orders)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if delivery_orders:
            tree_id = self.env.ref('stock.vpicktree').id
            form_id = self.env.ref('stock.view_picking_form').id
            return {
                'name': 'Delivery Order has been Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', delivery_orders)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if out_invoices:
            tree_id = self.env.ref('account.view_out_invoice_tree').id
            form_id = self.env.ref('account.view_move_form').id
            return {
                'name': 'Sale Invoice Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', out_invoices)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if out_refunds:
            tree_id = self.env.ref('account.view_out_credit_note_tree').id
            form_id = self.env.ref('account.view_move_form').id
            return {
                'name': 'Credit Note created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', out_refunds)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }

        if out_payment:
            tree_id = self.env.ref('account.view_account_payment_tree').id
            form_id = self.env.ref('account.view_account_payment_form').id
            return {
                'name': 'Customer Payments Created in Odoo from Tally',
                'view_mode': 'tree',
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'view_id': tree_id,
                'views': [(tree_id, 'tree'), (form_id, 'form')],
                'domain': [('id', 'in', out_payment)],
                'context': {
                    'expand': True,
                    'create': 0
                }
            }


class PptsTallyIntegtnMastLog(models.Model):
    """Tally Integration Tool Master Log"""
    _name = "sync.master.data.log"
    _description = "Tally Integration Tool Master Log"

    sync_log_id = fields.Many2one('ppts.tally.integration.log',
                                  string="Audit Trails", ondelete='cascade')
    name = fields.Char(string='Name', copy=False)
    master_type = fields.Selection([('partner', 'Partners'), ('group', 'Account Group'),
                                    ('coa', 'Chart of Accounts'), ('journals', 'Journals'),
                                    ('uom', 'Units of Measure'),
                                    ('prod_categ', 'Product Categories'),
                                    ('products', 'Products'), ('location', 'Godown'),
                                    ('out_invoice', 'Invoice'), ('in_invoice', 'Vendor Bill'),
                                    ('delievry', 'Delivery Order'), ('receipt', 'Receipt'),
                                    ('out_refund', 'Credit Note'), ('in_refund', 'Debit Note'),
                                    ('stock_transfer', 'Stock Transfer'),
                                    ('payment_transfer', 'Payment Transfer'),
                                    ('misc_journal', 'Journal Entries'),
                                    ('sale_order', 'Sale Order'),
                                    ('purchase_order', 'Purchase Order'),
                                    ('entry', 'Journal Entries'),
                                    ('in_payment', 'Vendor Payments'),
                                    ('out_payment', 'Customer Payments')], string="Model")
    sync_status = fields.Selection([('draft', 'Pending'), ('fail', 'Failed'),
                                    ('done', 'Completed')], string="Status", default='draft')
    sync_action = fields.Selection([('create', 'Creation'),
                                    ('alter', 'Alteration')], string="Sync Action")
    sync_for = fields.Selection([('master', 'Masters'),
                                 ('trans', 'Transactions')], string="Sync Action")
    sync_data = fields.Text(string="Syncing Data")
    error_data = fields.Text(string="Log Message")
    date_time = fields.Datetime(string='Sync Date', default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', string='Company', related='sync_log_id.company_id')
    tally_record_name = fields.Char(string='Tally Name',
                                    help='The field to save the record name from Tally')
    records_created_id = fields.Integer(string='Created ID')
    tally_record_id = fields.Char(string='Tally id',
                                  help='The field to save the record id from Tally')

    def create_record_from_log(self):
        """The Transaction Entries are created in the Log line"""
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'ppts_tally_integration_log')])
        if module.state == 'installed':
            start_date = datetime.today()
            _logger.info('Importing Start Date..: %s and the this record is creatd from the Odoo log', start_date)
        entries_count = 0
        _logger.info('@ Taken this record data to create journals from Tally to Odoo: %s', self.sync_data)
        tally_log_ids = []
        if self.sync_data:
            tally_data = self.sync_data.replace("'", '"')
            rec = json.loads(tally_data)
            try:
                entries_count += 1
                tally_journal_ids = self.env['account.move'].sudo().search(
                    [('tally_journal_id', '=', rec['tally_journal_id']),
                     ('move_type', 'not in',
                      ('out_refund', 'in_refund', 'out_invoice', 'in_invoice'))])
                if not tally_journal_ids:
                    line_item = []
                    for line in rec['invoice_line_ids']:
                        partner_id = None
                        account_id = None
                        if 'partner_id' in line:
                            partner_id = self.env['res.partner'].sudo().search(
                                [('tally_id', '=', line['partner_id'])],
                                limit=1)
                            default_property_account = self.env['ppts.tally.integration'].sudo().search(
                                [('is_active', '=', True)], limit=1)
                            _logger.info('@  SELECTED PARTNER FOR THE RECORD CREATION %s', line['partner_id'])
                            if not partner_id:
                                partner_id = self.env['res.partner'].sudo().create({
                                    'name': line['partner_name'],
                                    'type_partner': 'customer',
                                    'tally_id': int(line['partner_id']),
                                    'property_account_receivable_id': default_property_account.property_recieveable.id,
                                    'property_account_payable_id': default_property_account.property_payable.id,
                                    'company_id': 1
                                })
                            property_receviable_id = ''
                            property_payable_id = ''
                            if 'debit' in line:
                                property_receviable_id = partner_id.property_account_receivable_id
                                if not property_receviable_id:
                                    property_receviable_id = default_property_account.property_recieveable
                            elif 'credit' in line:
                                property_payable_id = partner_id.property_account_payable_id
                                if not property_payable_id:
                                    property_payable_id = default_property_account.property_payable
                            if property_receviable_id:
                                account_id = property_receviable_id
                                _logger.info('@  property_receviable_id %s', account_id)
                            elif property_payable_id:
                                account_id = property_payable_id
                                _logger.info('@  property_payable_id %s', account_id)
                            _logger.info('@  account_id %s', account_id)
                        else:
                            account_id = self.env['account.account'].sudo().search(
                                [('tally_id', '=', int(line['account_id']))], limit=1)
                            if not account_id:
                                account_id = self.env['account.account'].sudo().search(
                                    [('tally_id', '=', int(line['group_id']))], limit=1)
                                if not account_id:
                                    account_type = self.group_account_type(line)
                                    account_id = self.env['account.account'].sudo().create({
                                        'code': line['group_id'] + line['account_id'],
                                        'name': line['group_name'],
                                        'account_type': account_type,
                                        'tally_group_id': int(line['account_group']),
                                        'company_id': 1,
                                        'tally_id': line['group_id']
                                    })
                                    _logger.info('@  NEW ACCOUNT ID : account_id %s', account_id)

                        if account_id:
                            if 'debit' in line:
                                debit_amount = float(line['debit'])
                            else:
                                debit_amount = 0.0

                            if 'credit' in line:
                                credit_amount = float(line['credit'])
                            else:
                                credit_amount = 0.0

                            vals = (0, 0, {
                                'account_id': account_id.id,
                                'partner_id': partner_id.id if partner_id else '',
                                'name': line['name'],
                                'credit': credit_amount,
                                'debit': debit_amount
                            })
                            line_item.append(vals)
                    if line_item:
                        account_journal = self.env['account.journal'].sudo().search(
                            [('name', '=', rec['journal_name'])], limit=1)
                        date = datetime.strptime(rec['date'], '%d-%m-%Y')
                        date_val = date.strftime('%Y-%m-%d')
                        journal_entries = self.env['account.move'].sudo().create({
                            'move_type': 'entry',
                            'date': date_val,
                            'journal_id': account_journal.id,
                            'tally_journal_id': rec['tally_journal_id'],
                            'tally_journal_name': str(rec['tally_journal_name']),
                            'invoice_line_ids': line_item
                        })
                        journal_entries.action_post()
                        if module.state == 'installed':
                            self.sync_status = 'done'
                            self.name = journal_entries.name,
                            self.error_data = 'journal entries has been created'
                else:
                    raise UserError('Already the record has been created in Odoo.')
            except Exception as e:
                _logger.info('@ GETTING THE ISSUE ON THE EXCEPTION')
                if module.state == 'installed':
                    vals = (0, 0, {
                        'master_type': 'entry',
                        'sync_action': 'create',
                        'sync_data': str(rec),
                        'error_data': e,
                        'sync_status': 'fail',
                        'sync_for': 'trans',
                        'tally_record_name': rec['tally_journal_name'],
                        'tally_record_id': rec['tally_journal_id']
                    })
                    tally_log_ids.append(vals)
                    _logger.info('Log is created for the exception: %s', tally_log_ids)


class TallyEntries(models.Model):
    """The collection of all Tally Entries are shows"""
    _name = 'tally.entries'
    _description = 'Tally Entries'
    _rec_name = 'received_date'

    received_date = fields.Datetime('Received Date', copy=False, default=fields.Datetime.now())
    number_of_entries = fields.Integer('Number of Entries', copy=False)
    tally_entry_type = fields.Selection([('partner', 'Partners'), ('group', 'Account Group'),
                                         ('coa', 'Chart of Accounts'), ('journals', 'Journals'),
                                         ('uom', 'Units of Measure'),
                                         ('prod_categ', 'Product Categories'),
                                         ('products', 'Products'), ('location', 'Godown'),
                                         ('out_invoice', 'Invoice'), ('in_invoice', 'Vendor Bill'),
                                         ('delievry', 'Delivery Order'), ('receipt', 'Receipt'),
                                         ('out_refund', 'Credit Note'), ('in_refund', 'Debit Note'),
                                         ('stock_transfer', 'Stock Transfer'),
                                         ('payment_transfer', 'Payment Transfer'),
                                         ('misc_journal', 'Journal Entries'),
                                         ('sale_order', 'Sale Order'),
                                         ('purchase_order', 'Purchase Order'),
                                         ('entry', 'Journal Entries'),
                                         ('in_payment', 'Customer Payments'),
                                         ('out_payment', 'Vendor Payments')], string="Model")
    tally_data = fields.Text('Received Data from Tally before Creation', copy=False)


class OdooEntries(models.Model):
    """The collection of all Odoo Entries are shows"""
    _name = 'odoo.entries'
    _description = 'Odoo Entries'
    _rec_name = 'synchronize_date'

    synchronize_date = fields.Datetime('Synchronize Date', copy=False,
                                       default=fields.Datetime.now())
    number_of_odoo_entries = fields.Integer('Number of Entries', copy=False)
    odoo_entry_type = fields.Selection([('partner', 'Partners'), ('group', 'Account Group'),
                                        ('coa', 'Chart of Accounts'), ('journals', 'Journals'),
                                        ('uom', 'Units of Measure'),
                                        ('prod_categ', 'Product Categories'),
                                        ('products', 'Products'), ('location', 'Godown'),
                                        ('out_invoice', 'Invoice'),
                                        ('in_invoice', 'Vendor Bill'),
                                        ('delievry', 'Delivery Order'),
                                        ('receipt', 'Receipt'),
                                        ('out_refund', 'Credit Note'), ('in_refund', 'Debit Note'),
                                        ('stock_transfer', 'Stock Transfer'),
                                        ('payment_transfer', 'Payment Transfer'),
                                        ('misc_journal', 'Journal Entries'),
                                        ('sale_order', 'Sale Order'),
                                        ('purchase_order', 'Purchase Order'),
                                        ('entry', 'Journal Entries'),
                                        ('in_payment', 'Customer Payments'),
                                        ('out_payment', 'Vendor Payments')
                                        ], string="Model")
    odoo_data = fields.Text('Received Data from Tally before Creation', copy=False)
