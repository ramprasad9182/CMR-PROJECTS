# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models, api


class StockMove(models.Model):
    """This class inherits the model stock.move and add the field analytic to
     it, which shows the selected analytic distribution in sale.order.line"""
    _inherit = 'stock.move'

    analytic = fields.Json('Analytic', compute='_compute_analytic', store=False, inverse='_inverse_analytic',
                           help='Analytic Distribution')

    analytic_precision = fields.Integer(store=False,
                                        help='Define the precision of '
                                             'percentage decimal value',
                                        default=lambda self: self.env[
                                            'decimal.precision'].precision_get(
                                            "Percentage Analytic"))

    def _compute_analytic(self):
        """This function is used to show the selected analytic distribution in
        stock.move """
        for rec in self:
            if rec.sale_line_id:
                rec.analytic = rec.sale_line_id.analytic_distribution
            elif rec.purchase_line_id:
                rec.analytic = rec.purchase_line_id.analytic_distribution
            else:
                rec.analytic = False

    def _inverse_analytic(self):
        # Required for manual edits to be saved. If no extra logic, just pass.
        pass

    @api.model
    def create(self, values):
        """ Override to set analytic field when creating stock.move from sale or purchase order """
        if 'sale_line_id' in values:
            sale_line = self.env['sale.order.line'].browse(values['sale_line_id'])
            values['analytic'] = sale_line.analytic_distribution
        elif 'purchase_line_id' in values:
            purchase_line = self.env['purchase.order.line'].browse(values['purchase_line_id'])
            values['analytic'] = purchase_line.analytic_distribution

        return super(StockMove, self).create(values)




    def _generate_valuation_lines_data(
            self, partner_id, qty, debit_value, credit_value,
            debit_account_id, credit_account_id, svl_id, description
        ):
            res = super()._generate_valuation_lines_data(
                partner_id, qty, debit_value, credit_value,
                debit_account_id, credit_account_id, svl_id, description
            )

            # Inject analytic_distribution from stock.move into both journal lines
            if self.analytic:
                for line_vals in res.values():
                    line_vals['analytic_distribution'] = self.analytic

            return res
