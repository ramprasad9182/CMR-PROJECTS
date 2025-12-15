from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
from odoo.tools import Query, SQL, OrderedSet


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    nhcl_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False)
    nhcl_purchase_type = fields.Many2one('project.task.type', string="Purchase Type", copy=False, tracking=True)
    ##########################################################################################
    street = fields.Char(related='partner_id.street', string='Street')
    street2 = fields.Char(related='partner_id.street2', string='Street2')
    city = fields.Char(related='partner_id.city', string='City')
    state_id = fields.Many2one('res.country.state', related='partner_id.state_id', string='State')
    zip = fields.Char(related='partner_id.zip', string='ZIP')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string='Country')
    vendor_gst = fields.Char(string="Vendor GST")
    ############################################################################################
    payment_status = fields.Char(string="Payment Status", compute="_compute_payment_status", store=False)

    @api.onchange('project_id')
    def _onchange_project_id_one(self):
        if self.project_id:
            self.picking_type_id = self.project_id.receipt_type_id
        else:
            self.picking_type_id = False


    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id and self.project_id.account_id:
            self.nhcl_account_id = self.project_id.account_id
        else:
            self.nhcl_account_id = False


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
    nhcl_dummy_product_id = fields.Many2many('product.product', string="Dummy Pdts.", compute='nhcl_get_filtered_products', store=True)
    purchase_many = fields.Many2many(
        comodel_name='account.analytic.account',
        string='Account Lines', compute='_get_purchase_many')
    order_name = fields.Char(string="PO", related='order_id.name', store=False)
    partner_ref = fields.Char(related='order_id.partner_ref', store=False)
    po_date_order = fields.Datetime(related='order_id.date_order', store=False)
    po_payment_status = fields.Char(related='order_id.payment_status', store=False)
    bill_price_subtotal = fields.Float(string="Bill Value", compute='_compute_bill_price_subtotal', store=True)
    receive_bill_price_subtotal = fields.Float(
        string="GRC Value",
        compute="_compute_price_subtotal",
        store=True
    )

    @api.depends('qty_received', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.receive_bill_price_subtotal = (line.qty_received or 0.0) * (line.price_unit or 0.0)

    @api.depends('qty_invoiced', 'price_unit')
    def _compute_bill_price_subtotal(self):
        for line in self:
            line.bill_price_subtotal = (line.qty_invoiced or 0.0) * (line.price_unit or 0.0)

    @api.depends('analytic_distribution')
    def _get_purchase_many(self):
        for line in self:
            analytic_ids = []
            if line.analytic_distribution:
                for analytic_key in line.analytic_distribution.keys():
                    for id_str in str(analytic_key).split(','):
                        id_str = id_str.strip()
                        if id_str.isdigit():
                            analytic_ids.append(int(id_str))
            line.purchase_many = [(6, 0, analytic_ids)]

    @api.depends('nhcl_task_id', 'nhcl_sub_task_id')
    def nhcl_get_filtered_products(self):
        for rec in self:
            product_set = set()

            if rec.nhcl_sub_task_id:
                # ✅ Use sub-task products if selected
                for line in rec.nhcl_sub_task_id.nhcl_project_product_ids:
                    if line.nhcl_product_id:
                        product_set.add(line.nhcl_product_id.id)

            elif rec.nhcl_task_id:
                # ✅ Use task-level products if sub-task not selected
                for line in rec.nhcl_task_id.nhcl_project_product_ids:
                    if line.nhcl_product_id:
                        product_set.add(line.nhcl_product_id.id)

            else:
                # ✅ No task or sub-task: return all products (or keep it empty — your choice)
                product_set = self.env['product.product'].search([]).ids

            rec.nhcl_dummy_product_id = [(6, 0, list(product_set))] if product_set else [(5, 0, 0)]


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

