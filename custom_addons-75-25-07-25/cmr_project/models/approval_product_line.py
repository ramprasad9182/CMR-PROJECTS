from odoo import fields, models, api, _


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    nhcl_analytic_account_id = fields.Many2one('account.analytic.account', domain="[('company_id', '=?', company_id)]",
                                               ondelete='set null', compute='_compute_analytic_account_id', store=True,
                                               readonly=False, string="Analtyic Account")
    nhcl_task_approval_id = fields.Many2one(
        'project.task', string="Task",
        copy=False, domain="[('parent_id','=',False)]")
    nhcl_sub_task_approval_id = fields.Many2one(
        'project.task', string="Sub Task",
        copy=False, domain="[('parent_id','=',nhcl_task_approval_id)]")
    nhcl_dummy_product_approval_id = fields.Many2many(
        'product.product', string="Filtered Products", compute="nhcl_get_approval_filtered_products")
    estimate_value = fields.Float(string='Estimate Value', copy=False)
    unit_price = fields.Float(string="Unit Price")
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'purchase')],
                                context={'active_test': False})
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal(Tax Exclu)', aggregator=None, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total(Tax Inclu)', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    @api.depends('quantity', 'unit_price', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            base_line = line._prepare_base_line_for_taxes_computation()
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
            line.price_subtotal = base_line['tax_details']['raw_total_excluded_currency']
            line.price_total = base_line['tax_details']['raw_total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

    def _prepare_base_line_for_taxes_computation(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.taxes_id,
            quantity=self.quantity,
            partner_id=self.approval_request_id.partner_id,
            currency_id=self.approval_request_id.currency_id or self.approval_request_id.company_id.currency_id,
            rate=self.approval_request_id.currency_rate,
            price_unit=self.unit_price,
        )

    # def write(self, vals):
    #     for record in self:
    #         if 'unit_price' in vals:
    #             if not (
    #                     record.approval_request_id.request_status == 'pending'
    #                     and record.approval_request_id.request_owner_id.id == self.env.user.id
    #             ):
    #                 raise exceptions.UserError(_("You are not allowed to modify the unit price."))
    #     return super().write(vals)

    @api.model
    def create(self, vals):
        # Optional: apply similar logic during creation if needed
        return super().create(vals)


    # analytic = fields.Json(string='Analytic', compute="_compute_analytic", readonly=False, store=True)
    # analytic_precision = fields.Integer(string='precision')
    # @api.depends('product_id', 'approval_request_id.nhcl_project_id')
    # def _compute_analytic(self):
    #     for line in self:
    #         if line.analytic:
    #             continue
    #         else:
    #             project = line.approval_request_id.nhcl_project_id
    #             if project:
    #                 line.analytic = project._get_analytic_distribution()
    #             else:
    #                 line.analytic = False

    @api.depends('nhcl_task_approval_id', 'nhcl_sub_task_approval_id')
    def nhcl_get_approval_filtered_products(self):
        for rec in self:
            product_set = set()

            if rec.nhcl_sub_task_approval_id:
                for line in rec.nhcl_sub_task_approval_id.nhcl_project_product_ids:
                    if line.nhcl_product_id:
                        product_set.add(line.nhcl_product_id.id)
            elif rec.nhcl_task_approval_id:
                for line in rec.nhcl_task_approval_id.nhcl_project_product_ids:
                    if line.nhcl_product_id:
                        product_set.add(line.nhcl_product_id.id)
            else:
                product_set = self.env['product.product'].search([]).ids

            rec.nhcl_dummy_product_approval_id = [(6, 0, list(product_set))] if product_set else [(5, 0, 0)]

    @api.onchange('nhcl_task_approval_id')
    def _onchange_nhcl_task_approval_id(self):
        """ Clear sub task when task changes """
        self.nhcl_sub_task_approval_id = False

    @api.onchange('nhcl_sub_task_approval_id')
    def _onchange_nhcl_sub_task_approval_id(self):
        """Prevent selecting sub task before selecting the main task."""
        if self.nhcl_sub_task_approval_id and not self.nhcl_task_approval_id:
            self.nhcl_sub_task_approval_id = False
            return {
                'warning': {
                    'title': "Task Selection Required",
                    'message': "Please select a Task before selecting a Sub Task."
                }
            }

    @api.depends('approval_request_id.nhcl_project_id')
    def _compute_analytic_account_id(self):
        for task in self:
            if task.approval_request_id.nhcl_project_id:
                task.nhcl_analytic_account_id = task.approval_request_id.nhcl_project_id.account_id
            else:
                task.nhcl_analytic_account_id = False
