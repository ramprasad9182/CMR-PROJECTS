from odoo import models, tools, _
from odoo.exceptions import UserError

class UoM(models.Model):
    _inherit = 'uom.uom'

    def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
        if not self or not qty:
            return qty
        self.ensure_one()

        if self != to_unit and self.category_id.id != to_unit.category_id.id:
            if not raise_if_failure:
                raise UserError(_(
                    'The unit of measure %(unit)s defined on the order line doesn\'t belong to the same category as the unit of measure %(product_unit)s defined on the product. Please correct the unit of measure defined on the order line or on the product. They should belong to the same category.',
                    unit=self.name, product_unit=to_unit.name))
            else:
                return qty

        if self == to_unit:
            amount = qty
        else:
            amount = qty / self.factor
            if to_unit:
                amount = amount * to_unit.factor

        if to_unit and round:
            amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)

        return amount
