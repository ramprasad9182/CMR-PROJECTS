from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools import Query, SQL, OrderedSet


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_name = fields.Many2many('account.analytic.account', string='Project', compute='get_analytic_account')
    cmr_product_id = fields.Many2one('product.product', string='Product', copy=False, compute='get_product_inlines')
    po_ref_number = fields.Char(string='PO Number', copy=False, compute='get_purchase_number')
    po_date = fields.Date(string='PO Date', copy=False, compute='get_purchase_order_date')
    po_amount = fields.Float(string='Quotation Amount', compute='get_po_amount_total', store=True)
    paid_amount = fields.Float(string='Paid Amount', compute='get_paid_amount_total', store=True)
    payment_due = fields.Float(string='Payment Due', compute='get_payment_due_total', store=True)
    # inv_ref=fields.Char(string="Reference Number")


#######################################################
    def action_post(self):
        for record in self:
            # Check if ref is empty
            if not record.ref:
                raise ValidationError("Reference field is required. Please enter a value.")

            # Check if ref is duplicate
            duplicate = self.search([
                ('ref', '=', record.ref),
                ('id', '!=', record.id),

            ], limit=1)
            if duplicate:
                raise ValidationError(f"The reference '{record.ref}' already exists. Please enter a unique reference.")
            for invoice_line in record.invoice_line_ids:
                if invoice_line.purchase_line_id.order_id:
                    if invoice_line.quantity > invoice_line.purchase_line_id.qty_received:
                        raise ValidationError(f"You cannot give more than {invoice_line.purchase_line_id.qty_received}, given {invoice_line.quantity}")

        # Call the super after validations
        res = super(AccountMove, self).action_post()

        # Add transfer reference to analytic lines
        for record in self:
            transfer_rec = self.env['stock.picking'].search(
                [('origin', '=', record.invoice_origin)], order='create_date desc', limit=1
            ).name
            account_move_line_rec = self.env['account.move.line'].search([
                ('move_id', '=', int(record.id)),
                ('display_type', '=', 'product')
            ])
            for rec in account_move_line_rec:
                self.env['account.analytic.line'].search(
                    [('move_line_id', '=', rec.id)]
                ).update({'transfer_reference': transfer_rec})

        return res
##########################################################################################

    def get_purchase_number(self):
        for rec in self:
            if rec.line_ids.purchase_line_id.order_id:
                for line in rec.line_ids:
                    rec.po_ref_number = line.purchase_line_id.order_id.partner_ref
            else:
                rec.po_ref_number = False

    def get_paid_amount_total(self):
        for rec in self:
            payment = self.env['account.payment'].search(
                [("partner_type", "=", "supplier"), ("is_internal_transfer", "=", False)])
            for i in payment:
                bill = i.reconciled_bill_ids.filtered(lambda x: x.id == rec.id)
                if bill:
                    rec.paid_amount += i.amount
                else:
                    rec.paid_amount += 0

    def get_po_amount_total(self):
        for rec in self:
            if rec.line_ids.purchase_line_id.order_id:
                for line in rec.line_ids:
                    rec.po_amount = line.purchase_line_id.order_id.amount_total
            else:
                rec.po_amount = False

    def get_payment_due_total(self):
        for rec in self:
            if rec.amount_total and rec.paid_amount:
                rec.payment_due = rec.amount_total - rec.paid_amount
            else:
                rec.payment_due = 0

    def get_product_inlines(self):
        for rec in self:
            if rec.invoice_line_ids:
                rec.cmr_product_id = rec.invoice_line_ids[0].product_id
            else:
                rec.cmr_product_id = False

    def get_analytic_account(self):
        for rec in self:
            if rec.invoice_line_ids and rec.invoice_line_ids[0].analytic_distribution:
                project_name = rec.invoice_line_ids[0].analytic_distribution
                account_ids = []
                for k, v in project_name.items():
                    try:
                        ids = [int(i) for i in str(k).split(',')]
                        account_ids.extend(ids)
                    except ValueError:
                        continue  # skip invalid IDs
                rec.project_name = [(4, acc_id) for acc_id in account_ids]
            else:
                rec.project_name = False

    def get_purchase_order_date(self):
        for rec in self:
            if rec.line_ids.purchase_line_id.order_id:
                for line in rec.line_ids:
                    rec.po_date = line.purchase_line_id.order_id.date_planned
            else:
                rec.po_date = False






class AccountAnalyticLine(models.Model):
    """This class inherit the model account.analytic.line and add the field
    'transfer reference' to it, which shows the according transfer """
    _inherit = 'account.analytic.line'

    transfer_reference = fields.Char(string='Transfer Reference',
                                     help='shows the name of transfer')

# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     @api.constrains('quantity', 'product_id')
#     def _check_project_estimation(self):
#         for line in self:
#             project = line.move_id.project_name
#             if project:
#                 estimation = project.estimate_ids.filtered(lambda e: e.product_id == line.product_id)
#                 if estimation:
#                     estimated_qty = estimation.mapped('estimated_qty')
#                     billed_qty = sum(
#                         self.env['account.move.line'].search([('move_id.project_name', '=', project.ids),
#                             ('product_id', '=', line.product_id.id),('move_id.state', '!=', 'cancel')]).mapped('quantity'))
#                     if billed_qty > sum(estimated_qty):
#                         raise ValidationError(f"The total billed quantity for {line.product_id.display_name} exceeds "f"the project engineer's estimate.")


# class AccountAnalyticLine(models.Model):
#     _inherit = 'account.analytic.line'
#
#     nhcl_estimate_qty = fields.Float(string='Estimate Qty', compute='get_estimate_qty')
#     nhcl_estimate_value = fields.Float(string='Estimate Value', compute='get_estimate_value')
#     nhcl_balance_qty = fields.Float(string='Balance Qty',  compute='get_balance_qty')
#     nhcl_balance_value = fields.Float(string='Balance Value', compute='get_balance_value')
#     nhcl_product_category = fields.Many2one('product.category', string='Group')
#
#     @api.depends('account_id', 'product_id')
#     def get_estimate_qty(self):
#         for rec in self:
#             if rec.account_id and rec.product_id:
#                 # Find matching tasks for the analytic account and product
#                 tasks = self.env['project.task'].search([
#                     ('analytic_account_id', '=', rec.account_id.id),
#                     ('nhcl_product_id', '=', rec.product_id.id)])
#                 # Sum the quantities
#                 rec.nhcl_estimate_qty = sum(tasks.mapped('nhcl_estimate_qty'))
#             else:
#                 rec.nhcl_estimate_qty = 0
#
#     @api.depends('account_id', 'product_id')
#     def get_estimate_value(self):
#         for rec in self:
#             if rec.account_id and rec.product_id:
#                 # Find matching tasks for the analytic account and product
#                 tasks = self.env['project.task'].search([
#                     ('analytic_account_id', '=', rec.account_id.id),
#                     ('nhcl_product_id', '=', rec.product_id.id)])
#                 # Sum the values
#                 rec.nhcl_estimate_value = sum(tasks.mapped('nhcl_estimate_value'))
#             else:
#                 rec.nhcl_estimate_value = 0
#
#     @api.depends('nhcl_estimate_qty')
#     def get_balance_qty(self):
#         for rec in self:
#             rec.nhcl_balance_qty = rec.nhcl_estimate_qty - rec.unit_amount
#
#     @api.depends('nhcl_estimate_value')
#     def get_balance_value(self):
#         for rec in self:
#             rec.nhcl_balance_value = rec.nhcl_estimate_value + rec.amount


class AccountPayment(models.Model):
    """Populate factory part for account.payment."""
    _inherit = "account.payment"

    nhcl_purchase_id = fields.Many2one('purchase.order', string="Purchase Order's",
                                       domain=[('invoice_status', '!=', 'invoiced')])

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for rec in self:

            if rec.nhcl_purchase_id:
                total_paid = sum(self.env['account.payment'].search([
                    ('nhcl_purchase_id', '=', rec.nhcl_purchase_id.id), ("partner_type", "=", "supplier"),
                    ("is_internal_transfer", "=", False)
                ]).mapped('amount'))
                # Validate against the PO's total
                if total_paid > rec.nhcl_purchase_id.amount_total:
                    raise ValidationError(
                        f"Total payment exceeds the total amount for PO {rec.nhcl_purchase_id.name}."f"Total Paid: {total_paid}, PO Total: {rec.nhcl_purchase_id.amount_total}")
        return res

    @api.model
    def create(self, vals):
        """
        Override the create method to validate payment amount against payment terms.
        """
        if 'nhcl_purchase_id' in vals and 'amount' in vals and vals['nhcl_purchase_id'] != False:
            purchase_order = self.env['purchase.order'].browse(vals['nhcl_purchase_id'])
            allowed_payment = self._calculate_allowed_payment(purchase_order)
            if vals['amount'] > allowed_payment:
                raise ValidationError((
                                          "The payment amount exceeds the allocated percentage based on the payment terms.\n"
                                          "Allowed amount: {:.2f}\n"
                                          "Entered amount: {:.2f}"
                                      ).format(allowed_payment, vals['amount']))
        return super(AccountPayment, self).create(vals)

    def _calculate_allowed_payment(self, purchase_order):
        """
        Calculate the maximum allowed payment based on the Purchase Order's payment terms.
        """
        total_paid = sum(payment.amount for payment in self.env['account.payment'].search([
            ('nhcl_purchase_id', '=', purchase_order.id),
            ('state', '!=', 'cancel')
        ]))

        allowed_payment = 0.0
        today = fields.Date.today()

        for terms in purchase_order.payment_term_id.nhcl_payment_term_ids:
            due_date = None

            if terms.type == 'after_po_date':
                due_date = purchase_order.date_approve.date() + relativedelta(days=terms.days)
            elif terms.type == 'after_end_of_month':
                end_of_month = purchase_order.date_approve.date().replace(day=1) + relativedelta(months=1, days=-1)
                due_date = end_of_month + relativedelta(days=terms.days)
            elif terms.type == 'after_end_of_next_month':
                end_of_next_month = purchase_order.date_approve.date().replace(day=1) + relativedelta(months=2, days=-1)
                due_date = end_of_next_month + relativedelta(days=terms.days)

            if due_date and due_date <= today:
                allowed_payment += (terms.percentage / 100) * purchase_order.amount_total

        return max(0, allowed_payment - total_paid)


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    nhcl_payment_term_ids = fields.One2many('nhcl.account.payment.term', 'nhcl_payment_id')


class NhclAccountPayment(models.Model):
    _name = 'nhcl.account.payment.term'

    nhcl_payment_id = fields.Many2one('account.payment.term')
    percentage = fields.Float(string='Percentage(%)')
    type = fields.Selection([('after_po_date', 'After PO Date'), ('after_end_of_month', 'After End of Month')
                                , ('after_end_of_next_month', 'After End of Next Month')], string="Type")
    days = fields.Integer(string="Days")




