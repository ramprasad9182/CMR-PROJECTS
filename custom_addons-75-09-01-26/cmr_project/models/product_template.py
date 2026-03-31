from odoo import models, fields, api, exceptions,_
from odoo.exceptions import ValidationError
from odoo import models, fields, api
import json

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('name')
    def _check_duplicate_name_case_insensitive(self):
        for rec in self:
            if rec.name:
                normalized_name = rec.name.strip().lower()
                duplicates = self.env['product.template'].search([
                    ('id', '!=', rec.id),
                ])
                for dup in duplicates:
                    if dup.name and dup.name.strip().lower() == normalized_name:
                        raise ValidationError(
                            f"A product named '{rec.name}' already exists (matched with '{dup.name}')."
                        )

    @api.onchange("type")
    def _onchange_type(self):
        # Update instantly on form view
        if self.type == "consu":
            self.is_storable = True
        else:
            self.is_storable = False

    @api.onchange('attribute_line_ids')
    def _onchange_attribute_line_ids(self):
        if not self.attribute_line_ids:
            return

        unique = self.env['product.template.attribute.line']
        seen = set()
        duplicate_found = False
        duplicate_name = ""

        for line in self.attribute_line_ids:
            attr_id = line.attribute_id.id
            attr_name = line.attribute_id.name

            # duplicate attribute found
            if attr_id in seen:
                duplicate_found = True
                duplicate_name = attr_name
                continue

            seen.add(attr_id)
            unique += line

        # Keep only unique lines
        self.attribute_line_ids = unique

        # If duplicate was added → show warning message
        if duplicate_found:
            return {
                'warning': {
                    'title': "Duplicate Attribute",
                    'message': f"The attribute '{duplicate_name}' is already added. Duplicate entries are not allowed."
                }
            }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    x_receipt_analytic_ids = fields.Many2many(
        'account.analytic.account',
        string='Receipt Analytic Projects',
        compute='_compute_receipt_analytic_ids',
        store=False,
    )
    analytic_tags = fields.Char(string='Analytic Tags', compute='_get_analytic_tags', store=True, index=True)

    @api.depends('x_receipt_analytic_ids')
    def _get_analytic_tags(self):
        for rec in self:
            if rec.x_receipt_analytic_ids:
                rec.analytic_tags = ', '.join(rec.x_receipt_analytic_ids.mapped('name'))
            else:
                rec.analytic_tags = ''

    @api.depends('stock_quant_ids')
    def _compute_receipt_analytic_ids(self):
        StockMove = self.env['stock.move']
        for product in self:
            moves = StockMove.search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('picking_code', '=', 'incoming'),
                ('analytic', '!=', False)
            ])
            analytic_ids = set()

            for move in moves:
                analytic_data = move.analytic
                try:
                    if isinstance(analytic_data, str):
                        import json
                        analytic_data = json.loads(analytic_data)
                    elif not isinstance(analytic_data, dict):
                        continue
                except Exception:
                    continue

                for key in analytic_data.keys():
                    try:
                        analytic_ids.add(int(key))
                    except ValueError:
                        continue

            product.x_receipt_analytic_ids = [(6, 0, list(analytic_ids))]


# class ProductTemplateAttributeLine(models.Model):
#     _inherit = 'product.template.attribute.line'
#
#     @api.constrains('attribute_id', 'product_tmpl_id')
#     def _check_duplicate_attribute(self):
#         for line in self:
#             duplicates = line.product_tmpl_id.attribute_line_ids.filtered(
#                 lambda l: l.attribute_id == line.attribute_id
#             )
#             if len(duplicates) > 1:
#                 raise exceptions.ValidationError(
#                     _("Attribute '%s' is already added. You cannot select it twice!")
#                     % line.attribute_id.name
#                 )
