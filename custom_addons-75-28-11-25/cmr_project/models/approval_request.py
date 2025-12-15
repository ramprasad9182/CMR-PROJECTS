from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_amount, format_date, format_list, formatLang, groupby


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    nhcl_project_id = fields.Many2one('project.project', 'Project', required=True, readonly=True, copy=False,
                                      domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id)]",
                                      index=True, change_default=True)

    #########################################################################################
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    street = fields.Char(related='vendor_id.street', string='Street')
    street2 = fields.Char(related='vendor_id.street2', string='Street2')
    city = fields.Char(related='vendor_id.city', string='City')
    state_id = fields.Many2one('res.country.state', related='vendor_id.state_id', string='State')
    zip = fields.Char(related='vendor_id.zip', string='ZIP')
    country_id = fields.Many2one('res.country', related='vendor_id.country_id', string='Country')
    gst_no = fields.Char(related='vendor_id.vat', string='Vendor GST Number')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    nhcl_account_approval_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    nhcl_purchase_approval_type = fields.Many2one('project.task.type', string="Purchase Type", copy=False)

    can_edit_vendor = fields.Boolean(
        string="Can Edit Vendor",
        compute="_compute_can_edit_vendor",
        store=False
    )
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_total_cc = fields.Monetary(string="Company Total", store=True, readonly=True, compute="_amount_all",
                                      currency_field="company_currency_id")
    company_currency_id = fields.Many2one(related="company_id.currency_id", string="Company Currency")
    currency_rate = fields.Float(
        string="Currency Rate",
        compute='_compute_currency_rate',
        digits=0,
        store=True,
        precompute=True,
    )

    @api.depends('currency_id', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=(fields.Datetime.now()).date(),
            )

    @api.depends('product_line_ids.price_subtotal', 'company_id')
    def _amount_all(self):
        AccountTax = self.env['account.tax']
        for request in self:
            order_lines = request.product_line_ids
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, request.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, request.company_id)
            tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=request.currency_id or request.company_id.currency_id,
                company=request.company_id,
            )
            request.amount_untaxed = tax_totals['base_amount_currency']
            request.amount_tax = tax_totals['tax_amount_currency']
            request.amount_total = tax_totals['total_amount_currency']
            request.amount_total_cc = tax_totals['total_amount']

    @api.depends_context('lang')
    @api.depends('product_line_ids.price_subtotal', 'currency_id', 'company_id')
    def _compute_tax_totals(self):
        AccountTax = self.env['account.tax']
        for request in self:
            if not request.company_id:
                request.tax_totals = False
                continue
            order_lines = request.product_line_ids
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            print("base_lines", base_lines)
            AccountTax._add_tax_details_in_base_lines(base_lines, request.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, request.company_id)
            request.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=request.currency_id or request.company_id.currency_id,
                company=request.company_id,
            )
            if request.currency_id != request.company_currency_id:
                request.tax_totals['amount_total_cc'] = f"({formatLang(self.env, request.amount_total_cc, currency_obj=self.company_currency_id)})"


    @api.onchange('nhcl_account_approval_id')
    def onchange_nhcl_purchase_approval_type(self):
        self.nhcl_purchase_approval_type = False

    @api.onchange('vendor_id', 'company_id')
    def _onchange_vendor_id(self):
        self = self.with_company(self.company_id)
        if self.vendor_id:
            self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.vendor_id)
        else:
            self.fiscal_position_id = False

    @api.depends('approver_ids')
    def _compute_can_edit_vendor(self):
        for record in self:
            current_user_id = self.env.uid
            approver_user_ids = []
            for approver in record.approver_ids:
                approver_user_ids.append(approver.user_id.id)
            if current_user_id in approver_user_ids:
                record.can_edit_vendor = True
            else:
                record.can_edit_vendor = False


    def action_approve(self, approver=None):
        for request in self:
            for line in request.product_line_ids:
                if not line.unit_price or line.unit_price == 0.00:
                    raise ValidationError(_("Unit price is required for all product lines."))
                if not request.vendor_id:
                    raise ValidationError(_("Select vendor."))
        res = super(ApprovalRequest, self).action_approve(approver=approver)
        return res

    @api.onchange('nhcl_project_id')
    def _onchange_nhcl_project_id(self):
        if self.nhcl_project_id and self.nhcl_project_id.account_id:
            self.nhcl_account_approval_id = self.nhcl_project_id.account_id
        else:
            self.nhcl_account_approval_id = False

    def action_create_purchase_orders(self):
        self.ensure_one()
        if not self.vendor_id:
            raise UserError("Please select a vendor for this approval request.")

        for line in self.product_line_ids:
            if line.purchase_order_line_id:
                continue

            seller = line.product_id.with_company(line.company_id)._select_seller(
                quantity=line.po_uom_qty,
                uom_id=line.product_id.uom_po_id,
                partner_id=self.vendor_id,
            )

            po_domain = [
                ('partner_id', '=', self.vendor_id.id),
                ('state', '=', 'draft'),
                ('origin', 'ilike', self.name),
            ]
            existing_po = self.env['purchase.order'].search(po_domain, limit=1)

            if existing_po:
                po = existing_po
            else:
                po_vals = line._get_purchase_order_values(self.vendor_id)
                po_vals['origin'] = self.name
                po_vals['project_id'] = self.nhcl_project_id.id
                po_vals['nhcl_account_id'] = self.nhcl_account_approval_id.id if self.nhcl_account_approval_id else False
                po_vals['nhcl_purchase_type'] = self.nhcl_purchase_approval_type.id if self.nhcl_purchase_approval_type else False


                po = self.env['purchase.order'].create(po_vals)
                po._onchange_project_id_one()

            po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                line.product_id,
                line.po_uom_qty,
                line.product_uom_id,
                line.company_id,
                seller,
                po,
            )
            po_line_vals['price_unit'] = line.unit_price
            po_line_vals['taxes_id'] = [(6, 0, line.taxes_id.ids)]
            po_line_vals['nhcl_task_id'] = line.nhcl_task_approval_id.id if line.nhcl_task_approval_id else False
            po_line_vals['nhcl_sub_task_id'] = line.nhcl_sub_task_approval_id.id if line.nhcl_sub_task_approval_id else False
            # po_line_vals['analytic_distribution'] = line.analytic
            new_line = self.env['purchase.order.line'].create(po_line_vals)
            line.purchase_order_line_id = new_line.id
            po.order_line = [(4, new_line.id)]

############################################################################################
