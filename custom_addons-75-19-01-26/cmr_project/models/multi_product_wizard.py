from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class MultiProductWizard(models.TransientModel):
    _name = "nhcl.multi.product.wizard"
    _description = "Select Multiple Products for Task"

    task_id = fields.Many2one('project.task', string="Task")
    product_ids = fields.Many2many('product.product', string="Products")

    def action_add_products(self):
        for product in self.product_ids:
            self.env['nhcl.project.product'].create({
                'nhcl_task_id': self.task_id.id,
                'nhcl_product_id': product.id,
                'nhcl_product_estimate_qty': 1,
                'nhcl_product_estimate_value': product.standard_price,
            })
        return {'type': 'ir.actions.act_window_close'}





class ProjectProductSelectWizard(models.TransientModel):
    _name = 'project.product.select.wizard'
    _description = 'Wizard to select multiple products for a project task'

    product_name_id = fields.Many2many(
        'product.template',
        string="Product Template",
    )


    available_attribute_value_ids = fields.Many2many(
        'product.attribute.value',
        compute='_compute_available_attribute_value_ids',
        store=False
    )

    attribute_value_ids = fields.Many2many(
        'product.attribute.value',
        string="Attributes",
        domain="[('id', 'in', available_attribute_value_ids)]"
    )

    task_id = fields.Many2one('project.task', string="Task")
    categ_ids = fields.Many2many('product.category', string="Allowed Categories")

    @api.depends('product_name_id')
    def _compute_available_attribute_value_ids(self):
        for wiz in self:
            if wiz.product_name_id:
                wiz.available_attribute_value_ids = wiz.product_name_id.attribute_line_ids.mapped('value_ids')
            else:
                wiz.available_attribute_value_ids = self.env['product.attribute.value']

    def select_attribute_product_ids(self):
        allowed_product_ids = []

        #  products already added to task
        existing_product_ids = self.task_id.nhcl_project_product_ids.mapped(
            'nhcl_product_id'
        ).ids

        for tmpl in self.product_name_id:
            for attr_value in self.attribute_value_ids:
                exists = tmpl.attribute_line_ids.value_ids.filtered(
                    lambda v: v.id == attr_value.id
                )

                if exists:
                    for variant in tmpl.product_variant_ids:
                        match = variant.product_template_attribute_value_ids.filtered(
                            lambda v: v.product_attribute_value_id.id == attr_value.id
                        )

                        if match:
                            #  EXCLUDE already-added products
                            if variant.id not in existing_product_ids and variant.id not in allowed_product_ids:
                                allowed_product_ids.append(variant.id)

        return {
            'name': 'Select Product Variants',
            'type': 'ir.actions.act_window',
            'res_model': 'project.product.variant.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_available_product_ids': allowed_product_ids,
                'default_task_id': self.task_id.id,
            }
        }



    # def select_attribute_product_ids(self):
    #     """Open second wizard with matching product variants"""
    #     allowed_product_ids = []
    #
    #     for tmpl in self.product_name_id:
    #         for attr_value in self.attribute_value_ids:
    #
    #             # Check template attribute lines
    #             exists = tmpl.attribute_line_ids.value_ids.filtered(lambda v: v.id == attr_value.id)
    #
    #             if exists:
    #                 for variant in tmpl.product_variant_ids:
    #
    #                     match = variant.product_template_attribute_value_ids.filtered(
    #                         lambda v: v.name == attr_value.name
    #                     )
    #
    #                     if match and match.attribute_id.name == attr_value.attribute_id.name:
    #                         if variant.id not in allowed_product_ids:
    #                             allowed_product_ids.append(variant.id)
    #
    #     return {
    #         'name': 'Select Product Variants',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'project.product.variant.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_available_product_ids': allowed_product_ids,
    #             'default_task_id': self.task_id.id,
    #         }
    #     }


# ------------------------------------------------------------
#  WIZARD 2 — SELECT PRODUCT VARIANTS
# ------------------------------------------------------------
class ProjectProductVariantWizard(models.TransientModel):
    _name = 'project.product.variant.wizard'
    _description = 'Wizard to select product variants for project task'

    available_product_ids = fields.Many2many(
        'product.product',
        'project_product_variant_wizard_rel',
        'wizard_id',
        'product_id',
        string="Available Products"
    )

    product_ids = fields.Many2many(
        'product.product',
        string="Select Products",
        domain="[('id', 'in', available_product_ids)]"
    )

    task_id = fields.Many2one('project.task', string="Task")

    def action_add_products(self):
        """Add Products to the Task"""
        if not self.task_id:
            raise ValidationError(_("Task reference is missing."))

        duplicates = []

        for product in self.product_ids:
            exists = self.task_id.nhcl_project_product_ids.filtered(
                lambda l: l.nhcl_product_id.id == product.id
            )

            if exists:
                duplicates.append(product.display_name)
            else:
                self.env['nhcl.project.product'].create({
                    'nhcl_product_id': product.id,
                    'nhcl_task_id': self.task_id.id,
                })

        if duplicates:
            raise UserError(
                _("The following products are already added:\n%s") % "\n".join(duplicates)
            )

    # @api.onchange('product_ids')
    # def _onchange_product_ids(self):
    #     if self.product_ids and self.task_id:
    #         for product in self.product_ids:
    #             line = self.task_id.nhcl_project_product_ids.filtered(
    #                 lambda l: l.nhcl_product_id.id == product.id
    #             )
    #             if line:
    #                 return {
    #                     'warning': {
    #                         'title': "Duplicate Product",
    #                         'message': _("Product %s is already in the task.") % product.display_name,
    #                     }
    #                 }