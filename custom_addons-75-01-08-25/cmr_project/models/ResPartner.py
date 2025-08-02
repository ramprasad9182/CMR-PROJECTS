from odoo import models, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('name', 'vat')
    def _check_vendor_name_and_vat(self):
        for rec in self:
            if rec.supplier_rank <= 0:
                continue  # Only vendors

            name_clean = (rec.name or '').strip().lower()
            vat_clean = (rec.vat or '').strip().lower()

            vendors = self.env['res.partner'].search([
                ('id', '!=', rec.id),
                ('supplier_rank', '>', 0),
            ])

            # 1. VAT must be unique if present
            if vat_clean:
                for vendor in vendors:
                    vendor_vat = (vendor.vat or '').strip().lower()
                    if vendor_vat == vat_clean:
                        raise ValidationError("A vendor with the same GST already exists.")

            # 2. If VAT is empty, disallow if any vendor exists with same name and any VAT (empty or not)
            if not vat_clean:
                for vendor in vendors:
                    vendor_name = (vendor.name or '').strip().lower()
                    if vendor_name == name_clean:
                        raise ValidationError("A vendor with the same name already exists with or without GST.")
