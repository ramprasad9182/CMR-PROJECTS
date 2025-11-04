"""# -*- coding: utf-8 -*-"""
from textwrap import shorten
from odoo import models, fields, _


class AccountMoveLine(models.Model):
    """.."""
    _inherit = 'account.move.line'

    adv_payment_id = fields.Many2one('advance.payment.line', string='Multi Payment Id')
    partial_pay = fields.Boolean(string="Partial Reconcile", default=False)


class AccountMove(models.Model):
    """.."""
    _inherit = 'account.move'

    inv_id = fields.Many2one('account.move', string='Invoice')
    amount_untaxed_signed = fields.Monetary(
        string='Taxable Amount',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_tax_signed = fields.Monetary(
        string='Tax',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_total_signed = fields.Monetary(
        string='Total',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='company_currency_id',
    )
    amount_total_in_currency_signed = fields.Monetary(
        string='Total in Currency',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='currency_id',
    )
    amount_residual_signed = fields.Monetary(
        string='Amount Due',
        compute='_compute_amount', store=True,
        currency_field='company_currency_id',
    )
    invoice_partner_display_name = fields.Char(store=True,
                                               compute='_compute_invoice_partner_display_info',
                                               string='Partner Name')
    invoice_date = fields.Date(
        string='Date',
        readonly=True,
        # states='draft',
        index=True,
        copy=False,)
    # states = {'draft': [('readonly', False)]},

    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not
         the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        name = ''
        if self.state == 'draft':
            name += {
                'out_invoice': _('Draft Invoice'),
                'out_refund': _('Draft Credit Note'),
                'in_invoice': _('Draft Bill'),
                'in_refund': _('Draft Vendor Debit Note'),
                'out_receipt': _('Draft Sales Receipt'),
                'in_receipt': _('Draft Purchase Receipt'),
                'entry': _('Draft Entry'),
            }[self.move_type]
            name += ' '
        if not self.name or self.name == '/':
            name += '(* %s)' % str(self.id)
        else:
            name += self.name
            if self.env.context.get('input_full_display_name'):
                if self.partner_id:
                    name += f', {self.partner_id.name}'
                if self.date:
                    name += f', {format_date(self.env, self.date)}'
        return name + (f" ({shorten(self.ref, width=50)})" if show_ref and self.ref else '')
