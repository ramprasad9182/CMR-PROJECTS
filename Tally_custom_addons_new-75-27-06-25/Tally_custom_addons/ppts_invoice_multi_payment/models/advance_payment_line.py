"""# -*- coding: utf-8 -*-"""
from odoo import models, fields, api

    
class AdvancePaymentLine(models.Model):
    """ Advance Payment line for partial reconcile with invoice or Bill."""
    _name = 'advance.payment.line'
    _description = 'Advance Payment Line'

    invoice_id = fields.Many2one('account.move', string='Invoice')
    account_id = fields.Many2one('account.account', string="Account")
    date = fields.Date(string="Date")
    due_date = fields.Date(string="Due Date")
    original_amount = fields.Float(string="Original Amount")
    balance_amount = fields.Float(string="Balance Amount")
    full_reconcile = fields.Boolean(string="Full Reconclle")
    allocation = fields.Float(string="Total Allocation Amount")
    account_payment_id = fields.Many2one('account.payment')
    diff_amt = fields.Float('Remaining Amount', compute='get_diff_amount',)
    currency_id = fields.Many2one('res.currency', string='Currency')
    
    @api.depends('balance_amount', 'allocation')
    def get_diff_amount(self):
        """ Get the value of remaining amount value"""
        for line in self: 
            line.diff_amt = line.balance_amount - line.allocation

    @api.onchange('full_reconcile')
    def onchange_full_reconcile(self):
        """ Get the value of the allocation amount value."""
        if self.full_reconcile:
            self.allocation = self.balance_amount
            
    @api.onchange('allocation')
    def onchange_allocation(self):
        """Get the value of Full reconcile boolean value"""
        if self.allocation:
            if self.allocation >= self.balance_amount:
                self.full_reconcile = True
            else:
                self.full_reconcile = False
