"""# -*- coding: utf-8 -*-"""
from odoo.exceptions import ValidationError
from odoo import models, fields, api


class AccountPayment(models.Model):
    """Calculate the advance payment model total balance, remaining amount."""
    _inherit = 'account.payment'
    # is_internal_transfer = fields.Boolean(string="Transfer")
    payment_for = fields.Selection([('multi_payment', 'AP Payment')], default='multi_payment',
                                   string='Payment Mode')
    dev_invoice_line_ids = fields.One2many('advance.payment.line', 'account_payment_id')
    full_reco = fields.Boolean('Full Reconcile')
    allocation_amount = fields.Float('Total Amount', compute='get_allocation_amount')
    total_original_amount = fields.Float('Total Original Amount', compute='get_original_amount')
    total_balance_amount = fields.Float('Total Balance Amount', compute='get_balance_amount')
    total_remaining_amount = fields.Float('Total Remaining Amount', compute='get_remaining_amount')
    excess_amount = fields.Float('Excess Amount', compute='get_excess_amount')
    amount_company_currency_signed = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_amount_company_currency_signed', store=True,
        string='Amount Company Currency')
    amount_signed = fields.Monetary(
        currency_field='currency_id', compute='_compute_amount_signed',
        tracking=True, string='Amount',
        help='Negative value of amount field if payment_type is outbound')


    def action_post(self):
        """ The payment reconcile create with the advance payment invoice record."""
        move_lines = self.env['account.move.line']
        # move_lines.update({'partial_pay': True})
        rec_lines = self.dev_invoice_line_ids.filtered(lambda x: x.allocation > 0)
        if rec_lines:
            for line in rec_lines:
                invoice_move = line.invoice_id.line_ids.filtered(
                    lambda r: not r.reconciled and r.account_id.account_type in (
                    'liability_payable', 'asset_receivable'))
                payment_move = line.account_payment_id.move_id.line_ids.filtered(
                    lambda r: not r.reconciled and r.account_id.account_type in (
                    'liability_payable', 'asset_receivable'))
                move_lines |= (invoice_move + payment_move)
                if invoice_move and payment_move and len(rec_lines) > 0:
                    if self.partner_type == 'customer':
                        self.env['account.partial.reconcile'].create({
                            'amount': abs(line.allocation),
                            'debit_amount_currency': abs(line.allocation),
                            'credit_amount_currency': abs(line.allocation),
                            'debit_move_id': invoice_move.id,
                            'credit_move_id': payment_move.id,
                        })
                    else:
                        self.env['account.partial.reconcile'].create({
                            'amount': abs(line.allocation),
                            'debit_amount_currency': abs(line.allocation),
                            'credit_amount_currency': abs(line.allocation),
                            'debit_move_id': payment_move.id,
                            'credit_move_id': invoice_move.id,
                        })
            # reconcile = move_lines.filtered(lambda x: not x.reconciled).reconcile()
        if self.move_type == 'entry' and self.partner_id.id:
            for rec in self.line_ids:
                if rec.account_id.account_type == 'asset_current':
                    rec.name = self.journal_id.name
                if rec.account_id.account_type == 'asset_receivable':
                    rec.name = self.partner_id.name + ' - ' + self.name
                if rec.account_id.account_type == 'liability_payable':
                    rec.name = self.partner_id.name + ' - ' + self.name
        return super().action_post()

    @api.depends('amount', 'allocation_amount')
    def get_excess_amount(self):
        """Calculate the excess amount of payment"""
        for payment in self:
            payment.excess_amount = 0
            payment.excess_amount = self.amount - self.allocation_amount

    @api.depends('dev_invoice_line_ids', 'dev_invoice_line_ids.original_amount')
    def get_original_amount(self):
        """Calculate the original amount of payment"""
        for payment in self:
            original_amount = 0
            payment.total_original_amount = 0
            for line in payment.dev_invoice_line_ids:
                original_amount += line.original_amount
            payment.total_original_amount = original_amount

    @api.depends('dev_invoice_line_ids', 'dev_invoice_line_ids.balance_amount')
    def get_balance_amount(self):
        """Calculate the balance amount of payment"""
        for payment in self:
            balance_amount = 0
            payment.total_balance_amount = 0
            for line in payment.dev_invoice_line_ids:
                balance_amount += line.balance_amount
            payment.total_balance_amount = balance_amount

    @api.depends('dev_invoice_line_ids', 'dev_invoice_line_ids.diff_amt')
    def get_remaining_amount(self):
        """ Calculate the remaining amount of payment"""
        for payment in self:
            diff_amount = 0
            payment.total_remaining_amount = 0
            for line in payment.dev_invoice_line_ids:
                diff_amt = line.balance_amount - line.allocation
                diff_amount += diff_amt
            payment.total_remaining_amount = diff_amount

    @api.depends('dev_invoice_line_ids', 'dev_invoice_line_ids.allocation')
    def get_allocation_amount(self):
        """ Calculate the allocation amount (reconcile amount) of payment"""
        for payment in self:
            amount = 0
            payment.allocation_amount = 0
            for line in payment.dev_invoice_line_ids:
                amount += line.allocation
            payment.allocation_amount = amount

    @api.onchange('payment_for')
    def onchange_payment_for(self):
        """ advance payment visible for only the multi payment action."""
        if self.payment_for != 'multi_payment':
            for line in self.dev_invoice_line_ids:
                line.unlink()

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        """Get the value of partner id and advance payment model values."""
        partner_id = self.partner_id
        self.dev_invoice_line_ids = [(5,)]
        move_type = {'outbound': 'in_invoice', 'inbound': 'out_invoice'}
        moves = self.env['account.move'].sudo().search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),
             ('payment_state', 'not in', ['paid', 'reversed', 'in_payment']),
             ('company_id', '=', self.company_id.id),
             ('move_type', '=', move_type[self.payment_type])])
        vals = []
        for move in moves:
            curr_pool = self.env['res.currency']
            account_id = False
            if self.partner_type == 'customer':
                account_id = (move.partner_id and
                              move.partner_id.property_account_receivable_id.id or False)
            else:
                account_id = (move.partner_id and
                              move.partner_id.property_account_payable_id.id or False)

            original_amount = move.amount_total
            balance_amount = move.amount_residual
            allocation = move.amount_residual
            if move.currency_id.id != self.currency_id.id:
                original_amount = move.amount_total
                balance_amount = move.amount_residual
                allocation = move.amount_residual
                if move.currency_id.id != self.currency_id.id:
                    currency_id = self.currency_id.with_context(date=self.date)
                    original_amount = curr_pool._compute(move.currency_id, currency_id,
                                                         original_amount, round=True)
                    balance_amount = curr_pool._compute(move.currency_id, currency_id,
                                                        balance_amount, round=True)
                    allocation = curr_pool._compute(move.currency_id, currency_id,
                                                    allocation, round=True)
            vals.append((0, 0, {
                'invoice_id': move.id,
                'account_id': account_id,
                'date': move.invoice_date,
                'due_date': move.invoice_date_due,
                'original_amount': original_amount,
                'balance_amount': balance_amount,
                'currency_id': self.currency_id.id,
                'account_payment_id': self.id,
            }))
        self.dev_invoice_line_ids = vals
        self.partner_id = partner_id.id

    @api.onchange('currency_id')
    def onchange_currency(self):
        """ Get value of amount in the payment."""
        curr_pool = self.env['res.currency']
        if self.currency_id and self.dev_invoice_line_ids:
            for line in self.dev_invoice_line_ids:
                if line.currency_id.id != self.currency_id.id:
                    currency_id = self.currency_id.with_context(date=self.date)
                    line.original_amount = curr_pool._compute(line.currency_id, currency_id,
                                                              line.original_amount, round=True)
                    line.balance_amount = curr_pool._compute(line.currency_id, currency_id,
                                                             line.balance_amount, round=True)
                    line.allocation = curr_pool._compute(line.currency_id, currency_id,
                                                         line.allocation, round=True)
                    line.currency_id = self.currency_id and self.currency_id.id or False
        self.amount = 0.0

    def remove_lines(self):
        """ The invoice line details by click to remove."""
        for line in self.dev_invoice_line_ids:
            if line.allocation <= 0:
                line.unlink()

    def _synchronize_from_moves(self, changed_fields):
        """ #overwrite for multi payment."""
        for payment in self:
            if payment.payment_for == 'multi_payment':
                return True
        return super(AccountPayment, self)._synchronize_from_moves(changed_fields)

    def load_payment_lines(self):
        """ Get the collection of invoice record for payment partner."""
        if self.payment_for == 'multi_payment':
            self.dev_invoice_line_ids.unlink()
            account_inv_obj = self.env['account.move']
            invoice_ids = []
            partner_ids = self.env['res.partner'].search([
                ('parent_id', '=', self.partner_id.id)]).ids
            if not self.partner_id:
                raise ValidationError(("Please select the Customer/Vendor"))
            partner_ids.append(self.partner_id.id)
            query = """ select id from account_move where partner_id in %s and state = %s and
             move_type in %s and company_id = %s and payment_state != %s"""
            if self.partner_type == 'customer':
                params = (tuple(partner_ids), 'posted', ('out_invoice', 'out_refund'),
                          self.company_id.id, 'in_payment')
            else:
                params = (tuple(partner_ids), 'posted', ('in_invoice', 'in_refund'),
                          self.company_id.id, 'in_payment')
            self.env.cr.execute(query, params)
            result = self.env.cr.dictfetchall()
            invoice_ids = [inv.get('id') for inv in result]
            invoice_ids = account_inv_obj.browse(invoice_ids)
            curr_pool = self.env['res.currency']
            for vals in invoice_ids:
                account_id = False
                if self.partner_type == 'customer':
                    account_id = (vals.partner_id and
                                  vals.partner_id.property_account_receivable_id.id
                                  or False)
                else:
                    account_id = (vals.partner_id and
                                  vals.partner_id.property_account_payable_id.id
                                  or False)
                original_amount = vals.amount_total
                balance_amount = vals.amount_residual
                if vals.currency_id.id != self.currency_id.id:
                    original_amount = vals.amount_total
                    balance_amount = vals.amount_residual
                    if vals.currency_id.id != self.currency_id.id:
                        currency_id = self.currency_id.with_context(date=self.date)
                        original_amount = curr_pool._compute(vals.currency_id, currency_id,
                                                             original_amount, round=True)
                        balance_amount = curr_pool._compute(vals.currency_id, currency_id,
                                                            balance_amount, round=True)
                query = """INSERT INTO advance_payment_line (invoice_id, account_id, date, due_date, 
                original_amount, balance_amount, currency_id, account_payment_id) VALUES
                 (%s,%s,%s,%s,%s,%s,%s,%s)"""
                params = (vals.id, account_id, vals.invoice_date, vals.invoice_date_due,
                          original_amount, balance_amount, self.currency_id.id, self.id)
                self.env.cr.execute(query, params)
            return invoice_ids
