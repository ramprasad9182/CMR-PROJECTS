from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
from odoo.tools import Query, SQL, OrderedSet


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    nhcl_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    nhcl_purchase_type = fields.Many2one('project.task.type', string="Purchase Type", copy=False, tracking=True)
    street = fields.Char(related='partner_id.street', string='Street')
    street2 = fields.Char(related='partner_id.street2', string='Street2')
    city = fields.Char(related='partner_id.city', string='City')
    state_id = fields.Many2one('res.country.state', related='partner_id.state_id', string='State')
    zip = fields.Char(related='partner_id.zip', string='ZIP')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string='Country')
    vendor_gst = fields.Char(string="Vendor GST")
    payment_status = fields.Char(string="Payment Status", compute="_compute_payment_status", store=False)
    nhcl_type = fields.Selection([('civil','Civil'),('interior','Interior')],string="Type")
    project_street = fields.Char(string="Street")
    project_street2 = fields.Char(string="Street 2")
    project_city = fields.Char(string="City")
    project_state_id = fields.Many2one('res.country.state', string="State", domain="[('country_id', '=?', country_id)]")
    project_zip = fields.Char(string="ZIP")
    project_country_id = fields.Many2one('res.country', string="Country")
    project_l10n_in_gst_treatment = fields.Selection([
        ('regular', 'Registered Business - Regular'),
        ('composition', 'Registered Business - Composition'),
        ('unregistered', 'Unregistered Business'),
        ('consumer', 'Consumer'),
        ('overseas', 'Overseas'),
        ('special_economic_zone', 'Special Economic Zone'),
        ('deemed_export', 'Deemed Export'),
        ('uin_holders', 'UIN Holders'),
    ], string="GST Treatment", default="regular")
    project_l10n_in_gstin = fields.Char(string="GSTIN")
    project_pan = fields.Char(string="PAN")
    nhcl_task_ids = fields.Many2many(
        comodel_name="project.task",
        relation="task1",
        string="Task",
        compute="_compute_nhcl_task_ids",
        store=True
    )
    nhcl_sub_task_ids = fields.Many2many(
        comodel_name="project.task",
        relation="subtask1",
        string="Sub Task",
        compute="_compute_nhcl_sub_task_ids",
        store=True
    )

    @api.depends('order_line.nhcl_task_id')
    def _compute_nhcl_task_ids(self):
        for order in self:
            order.nhcl_task_ids = order.order_line.mapped('nhcl_task_id')

    @api.depends('order_line.nhcl_sub_task_id')
    def _compute_nhcl_sub_task_ids(self):
        for order in self:
            order.nhcl_sub_task_ids = order.order_line.mapped('nhcl_sub_task_id')

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            # Address & GST fields from project
            self.project_street = self.project_id.street or ''
            self.project_street2 = self.project_id.street2 or ''
            self.project_city = self.project_id.city or ''
            self.project_state_id = self.project_id.state_id.id or False
            self.project_zip = self.project_id.zip or ''
            self.project_country_id = self.project_id.country_id.id or False
            self.project_l10n_in_gst_treatment = self.project_id.l10n_in_gst_treatment or 'regular'
            self.project_l10n_in_gstin = self.project_id.l10n_in_gstin or ''
            self.project_pan = self.project_id.pan or ''

            # Picking type from project
            self.picking_type_id = self.project_id.receipt_type_id

            # Account from project
            if self.project_id.account_id:
                self.nhcl_account_id = self.project_id.account_id
            else:
                self.nhcl_account_id = False
        else:
            # Clear all fields if no project selected
            self.project_street = ''
            self.project_street2 = ''
            self.project_city = ''
            self.project_state_id = False
            self.project_zip = ''
            self.project_country_id = False
            self.project_l10n_in_gst_treatment = 'regular'
            self.project_l10n_in_gstin = ''
            self.project_pan = ''
            self.picking_type_id = False
            self.nhcl_account_id = False

    # @api.onchange('project_id')
    # def _onchange_project_id_one(self):
    #     if self.project_id:
    #         self.picking_type_id = self.project_id.receipt_type_id
    #     else:
    #         self.picking_type_id = False
    #
    #
    # @api.onchange('project_id')
    # def _onchange_project_id(self):
    #     if self.project_id and self.project_id.account_id:
    #         self.nhcl_account_id = self.project_id.account_id
    #     else:
    #         self.nhcl_account_id = False


    @api.depends('invoice_ids.payment_state')
    def _compute_payment_status(self):
        for order in self:
            if order.invoice_ids:
                states = order.invoice_ids.mapped('payment_state')
                if all(state == 'paid' for state in states):
                    order.payment_status = 'Paid'
                elif any(state == 'not_paid' for state in states):
                    order.payment_status = 'Not Paid'
                elif any(state == 'partial' for state in states):
                    order.payment_status = 'Partially Paid'
                else:
                    order.payment_status = ', '.join(states)
            else:
                order.payment_status = 'No Bill'


    def default_get(self, fields_list):
        res = super(PurchaseOrder, self).default_get(fields_list)
        if 'notes' in fields_list:
            res['notes'] = ("<b>Terms & Conditions </b><br/>"
                            "1. GST &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : <b>18% </b> Extra As Applicable. <br/>"
                            "2. Packing &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : Included with Polythene Sheet. <br/>"
                            "3. Payment Terms for Supply &nbsp;&nbsp; : 50% advance with PO, 50 % Agreement. <br/>"
                            "4. Doors Installation &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : Included. <br/>"
                            "5. Transportation &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : Extra. <br/>"
                            "6. Delivery period &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : in 40 days. <br/>"
                            "7. Warranty &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; : One year. <br/>"
                            "<b>For CMR Textiles and Jewellers Pvt Ltd. </b><br/>"
                            "<b>Authorized Signatory </b>")
        return res

    @api.onchange('nhcl_account_id')
    def onchange_nhcl_purchase_type(self):
        self.nhcl_purchase_type = False



    def notify_due_payment_terms(self):
        """
        Check purchase orders with due payment terms and send alerts.
        """
        today = fields.Date.today()
        due_orders = self.env['purchase.order'].search([
            ('state', '=', 'purchase'),
            ('invoice_status', '!=', 'invoiced'),('payment_term_id', '!=', False)])
        for order in due_orders:
            for term in order.payment_term_id.nhcl_payment_term_ids:
                due_date = None
                if term.payment_type == 'after_po_date':
                    due_date = order.date_approve + relativedelta(days=term.days)
                elif term.payment_type == 'after_end_of_month':
                    end_of_month = order.date_approve.replace(day=1) + relativedelta(months=1, days=-1)
                    due_date = end_of_month + relativedelta(days=term.days)
                elif term.payment_type == 'after_end_of_next_month':
                    end_of_next_month = order.date_approve.replace(day=1) + relativedelta(months=2, days=-1)
                    due_date = end_of_next_month + relativedelta(days=term.days)

                if due_date and due_date == today:
                    order.send_alert_to_responsible_user()

    def send_alert_to_responsible_user(self):
        """Send an alert to the responsible user of the purchase order."""
        odoobot_id = self.env['ir.model.data']._xmlid_to_res_id('base.partner_root')
        author = self.env['res.users'].sudo().browse(odoobot_id).partner_id
        purchase_notification_ids = []
        body = _("Purchase Order " + self._get_html_link()+" has payment terms that are due.")
        if self.user_id:
            purchase_notification_ids.append(self.user_id.partner_id.id)
        if purchase_notification_ids:
            name = "Payment Due Alert"
            self.send_msg_to_responsible_user(purchase_notification_ids, author.id, body, name)

    def send_msg_to_responsible_user(self, user_ids, author_id, body, name):
        """
        Helper method to send a message to a channel or create a new one.
        """
        mail_channel = self.env['discuss.channel'].search(
            [('name', '=', name), ('channel_type', '=', 'group'), ('channel_partner_ids', 'in', user_ids)], limit=1
        )
        if not mail_channel:
            mail_channel = self.env['discuss.channel'].create({
                'channel_partner_ids': [(4, user_id) for user_id in user_ids],
                'channel_type': 'group',
                'name': name,
            })
        mail_channel.message_post(
            author_id=author_id,
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )


    def get_payment_alert(self):
        alert_date = fields.Date.today()
        for rec in self:
            if rec.payment_term_id:
                for terms in rec.payment_term_id.nhcl_payment_term_ids:
                    due_date = None
                    # Condition: After PO Date
                    if terms.type == 'after_po_date':
                        due_date = rec.date_approve.date() + relativedelta(days=terms.days)
                    # Condition: After End of Month
                    elif terms.type == 'after_end_of_month':
                        end_of_month = rec.date_approve.date().replace(day=1) + relativedelta(months=1, days=-1)
                        due_date = end_of_month + relativedelta(days=terms.days)
                    # Condition: After End of Next Month
                    elif terms.type == 'after_end_of_next_month':
                        end_of_next_month = rec.date_approve.date().replace(day=1) + relativedelta(months=2, days=-1)
                        due_date = end_of_next_month + relativedelta(days=terms.days)

                    # Trigger an alert 2 days before the due date
                    if due_date and due_date - timedelta(days=2) == alert_date:
                        self.notify_due_payment_terms()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    nhcl_account_line_id = fields.Many2one('account.analytic.account', string="Account", compute='get_analytic_account')
    nhcl_task_id = fields.Many2one(
        'project.task', string="Task",
        copy=False, domain="[('parent_id','=',False)]")
    nhcl_sub_task_id = fields.Many2one(
        'project.task',string="Sub Task",
        copy=False,domain="[('parent_id','=',nhcl_task_id)]")
    nhcl_dummy_product_id = fields.Many2many('product.product', string="Dummy Pdts.", compute='nhcl_get_filtered_products', store=False)
    # purchase_many = fields.Many2many('account.analytic.account',compute='_get_purchase_many',store=True,
    #     string='Prjct')
    purchase_project_ids = fields.Many2many('account.analytic.account', 'project_1',compute='_get_purchase_many',store=True,
                                     string='Project')
    order_name = fields.Char(string="PO", related='order_id.name', store=False)
    partner_ref = fields.Char(related='order_id.partner_ref', store=False)
    po_date_order = fields.Datetime(related='order_id.date_order', store=False)
    po_payment_status = fields.Char(related='order_id.payment_status', store=False)
    # bill_price_subtotal = fields.Float(string="Bill Value", compute='_compute_bill_price_subtotal', store=False)
    # receive_bill_price_subtotal = fields.Float(
    #     string="GRC Value",
    #     compute="_compute_price_subtotal",
    #     store=True
    # )
    # nhcl_type = fields.Selection(
    #     related='order_id.nhcl_type',
    #     string="NHCL Type",
    #     store=False  # No need to store, used only for domain
    # )
    # unit_price_qty = fields.Float(
    #     string="PO Amount cal",
    #     compute="_compute_unit_price_qty",
    #     store=True
    # )
    # pending_po_qty = fields.Float(string="Pending PO Qty", compute="_compute_pending_fields", store=False)
    # pending_po_value = fields.Float(string="Pending PO Value", compute="_compute_pending_fields", store=False)
    # pending_grc_qty = fields.Float(string="Pending GRC Qty", compute="_compute_pending_fields", store=False)
    # pending_grc_value = fields.Float(string="Pending GRC Value", compute="_compute_pending_fields", store=False)
    # bill_qty_posted = fields.Float(
    #     string="Bill Qty",
    #     compute="_compute_bill_qty_posted",
    #     store=True
    # )

    # @api.depends('qty_invoiced', 'order_id.invoice_ids.state')
    # def _compute_bill_qty_posted(self):
    #     for line in self:
    #         is_bill_posted = any(inv.state == 'posted' for inv in line.order_id.invoice_ids)
    #         line.bill_qty_posted = line.qty_invoiced if is_bill_posted else 0.0
    #
    #
    # @api.depends('product_qty', 'price_unit')
    # def _compute_unit_price_qty(self):
    #     for line in self:
    #         line.unit_price_qty = line.price_unit * line.product_qty
    #
    # @api.depends('product_qty', 'qty_received', 'unit_price_qty', 'receive_bill_price_subtotal', 'bill_qty_posted','bill_price_subtotal', 'product_id')
    # def _compute_pending_fields(self):
    #     for line in self:
    #         product_type = line.product_id.type or 'consu'
    #         if product_type == 'consu':
    #             line.pending_po_qty = line.product_qty - line.qty_received
    #             line.pending_po_value = line.unit_price_qty - line.receive_bill_price_subtotal
    #             line.pending_grc_qty = line.qty_received - line.bill_qty_posted
    #             line.pending_grc_value = line.receive_bill_price_subtotal - line.bill_price_subtotal
    #         else:
    #             line.pending_po_qty = line.product_qty - line.bill_qty_posted
    #             line.pending_po_value = line.unit_price_qty - line.bill_price_subtotal
    #             line.pending_grc_qty = 0
    #             line.pending_grc_value = 0
    #
    #
    # @api.depends('qty_received', 'price_unit')
    # def _compute_price_subtotal(self):
    #     for line in self:
    #         line.receive_bill_price_subtotal = (line.qty_received or 0.0) * (line.price_unit or 0.0)
    #
    # @api.depends('qty_invoiced', 'price_unit')
    # def _compute_bill_price_subtotal(self):
    #     for line in self:
    #         line.bill_price_subtotal = (line.bill_qty_posted or 0.0) * (line.price_unit or 0.0)

    po_untaxed = fields.Float(string="Total PO Value", compute="_compute_po_values", store=True)
    grc_value = fields.Float(string="Total GRC Value", compute="_compute_po_values", store=True)
    billed_qty = fields.Float(string="Total Bill Qty", compute="_compute_po_values", store=True)
    bill_value = fields.Float(string="Total Bill Value", compute="_compute_po_values", store=True)

    pending_po_qty = fields.Float(string="Pending PO Qty", compute="_compute_po_values", store=True)
    pending_po_value = fields.Float(string="Pending PO Value", compute="_compute_po_values", store=True)
    pending_grc_qty = fields.Float(string="Pending GRC Qty", compute="_compute_po_values", store=True)
    pending_grc_value = fields.Float(string="Pending GRC Value", compute="_compute_po_values", store=True)
    s_no = fields.Integer(string="S.No", compute="_compute_s_no")

    @api.depends('order_id')
    def _compute_s_no(self):
        for rec in self.order_id:
            for index, line in enumerate(rec.order_line, start=1):
                line.s_no = index

    def write(self, vals):
        project_products = (self.mapped('nhcl_task_id') | self.mapped('nhcl_sub_task_id')).mapped('nhcl_project_product_ids')
        res = super().write(vals)
        if vals or 'state' in vals:
            project_products._compute_actuals()
        return res

    @api.depends(
        'price_unit',
        'product_qty',
        'qty_received',
        'product_id.type',
        'invoice_lines.quantity',
        'invoice_lines.price_unit',
        'invoice_lines.move_id.state',
        'invoice_lines.move_id.move_type'
    )
    def _compute_po_values(self):
        for rec in self:
            rec.po_untaxed = rec.price_unit * rec.product_qty
            rec.grc_value = rec.price_unit * rec.qty_received

            posted_lines = rec.invoice_lines.filtered(
                lambda l: l.move_id.state == 'posted' and l.move_id.move_type == 'in_invoice'
            )

            rec.billed_qty = sum(posted_lines.mapped('quantity'))
            rec.bill_value = sum(l.quantity * l.price_unit for l in posted_lines)
            product_type = rec.product_id.type
            if product_type == 'consu':
                rec.pending_po_qty = rec.product_qty - rec.qty_received
                rec.pending_po_value = rec.po_untaxed - rec.grc_value
                rec.pending_grc_qty = rec.qty_received - rec.billed_qty
                rec.pending_grc_value = rec.grc_value - rec.bill_value
            else:
                rec.pending_po_qty = rec.product_qty - rec.billed_qty
                rec.pending_po_value = rec.po_untaxed - rec.bill_value
                rec.pending_grc_qty = 0.0
                rec.pending_grc_value = 0.0

    # server action
    def action_force_recompute_po_values(self):
        for rec in self.search([]):
            rec._compute_po_values()

    @api.depends('analytic_distribution')
    def _get_purchase_many(self):
        Project = self.env['project.project']
        # Collect all analytic account IDs that are linked to a project (via account_id)
        project_analytic_ids = set(Project.search([]).mapped('account_id.id'))
        for line in self:
            analytic_ids = []
            if line.analytic_distribution:
                for analytic_key in line.analytic_distribution.keys():
                    for id_str in str(analytic_key).split(','):
                        id_str = id_str.strip()
                        if id_str.isdigit():
                            analytic_ids.append(int(id_str))
            # Filter only those IDs that are linked to projects
            only_project_ids = list(set(analytic_ids) & project_analytic_ids)
            # line.purchase_many = [(6, 0, only_project_ids)]
            line.purchase_project_ids = [(6, 0, only_project_ids)]

    @api.depends('nhcl_task_id', 'nhcl_sub_task_id')
    def nhcl_get_filtered_products(self):
        for rec in self:
            if rec.nhcl_sub_task_id:
                rec.nhcl_dummy_product_id = rec.nhcl_sub_task_id \
                    .nhcl_project_product_ids \
                    .mapped('nhcl_product_id')

            elif rec.nhcl_task_id:
                rec.nhcl_dummy_product_id = rec.nhcl_task_id \
                    .nhcl_project_product_ids \
                    .mapped('nhcl_product_id')

            else:
                rec.nhcl_dummy_product_id = [(5, 0, 0)]

    # @api.depends('nhcl_task_id', 'nhcl_sub_task_id')
    # def nhcl_get_filtered_products(self):
    #     for rec in self:
    #         product_set = set()
    #
    #         if rec.nhcl_sub_task_id:
    #             # ✅ Use sub-task products if selected
    #             for line in rec.nhcl_sub_task_id.nhcl_project_product_ids:
    #                 if line.nhcl_product_id:
    #                     product_set.add(line.nhcl_product_id.id)
    #
    #         elif rec.nhcl_task_id:
    #             # ✅ Use task-level products if sub-task not selected
    #             for line in rec.nhcl_task_id.nhcl_project_product_ids:
    #                 if line.nhcl_product_id:
    #                     product_set.add(line.nhcl_product_id.id)
    #
    #         else:
    #             # ✅ No task or sub-task: return all products (or keep it empty — your choice)
    #             product_set = self.env['product.product'].search([]).ids
    #
    #         rec.nhcl_dummy_product_id = [(6, 0, list(product_set))] if product_set else [(5, 0, 0)]


    @api.depends('order_id')
    def get_analytic_account(self):
        for rec in self:
            if rec.order_id and rec.order_id.nhcl_account_id:
                rec.nhcl_account_line_id = rec.order_id.nhcl_account_id
            else:
                rec.nhcl_account_line_id = False

    @api.onchange('nhcl_task_id')
    def _onchange_nhcl_task_id(self):
        """ Clear sub task when task changes """
        self.nhcl_sub_task_id = False

    @api.onchange('nhcl_sub_task_id')
    def _onchange_nhcl_sub_task_id(self):
        """Prevent selecting sub task before selecting the main task."""
        if self.nhcl_sub_task_id and not self.nhcl_task_id:
            self.nhcl_sub_task_id = False
            return {
                'warning': {
                    'title': "Task Selection Required",
                    'message': "Please select a Task before selecting a Sub Task."
                }
            }

