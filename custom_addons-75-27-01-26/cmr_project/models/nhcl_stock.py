from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Picking(models.Model):
    _inherit = "stock.picking"

    security_check = fields.Char(string="Security Inward", tracking=True, copy=False)
    grc_qty = fields.Float(string="GRC Qty", copy=False, compute="get_move_qty")
    bill_reference = fields.Char(string="Bill Reference")
    project_id = fields.Many2one('project.project', string="Project")

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if not self.project_id:
            return

        picking_code = (self.picking_type_id.code or
                        self.env.context.get('default_picking_type_code') or
                        self.env.context.get('restricted_picking_type_code'))

        # Determine the new picking_type_id based on project and code
        picking_type = False
        if picking_code == 'incoming':
            picking_type = self.project_id.receipt_type_id
        elif picking_code == 'outgoing':
            picking_type = self.project_id.delivery_type_id
        elif picking_code == 'internal':
            picking_type = self.project_id.internal_type_id
        elif picking_code == 'mrp_operation':
            picking_type = self.project_id.manufacturing_type_id
        elif picking_code == 'repair_operation':
            picking_type = self.project_id.repair_type_id

        # Update only if the project has a valid picking_type
        if picking_type:
            self.picking_type_id = picking_type
        else:
            raise ValidationError("This project has no operation type for the selected operation.")

    # @api.onchange('project_id')
    # def _onchange_project_id(self):
    #     if not self.project_id:
    #         self.picking_type_id = False
    #         return
    #
    #     # Use context to find the operation type
    #     picking_code = self.env.context.get('restricted_picking_type_code')
    #
    #     if picking_code == 'incoming':
    #         self.picking_type_id = self.project_id.receipt_type_id
    #     elif picking_code == 'outgoing':
    #         self.picking_type_id = self.project_id.delivery_type_id
    #     elif picking_code == 'internal':
    #         self.picking_type_id = self.project_id.internal_type_id
    #     elif picking_code == 'mrp_operation':
    #         self.picking_type_id = self.project_id.manufacturing_type_id
    #     elif picking_code == 'repair_operation':
    #         self.picking_type_id = self.project_id.repair_type_id
    #     else:
    #         self.picking_type_id = False

    @api.constrains('security_check', 'picking_type_id', 'purchase_id')
    def _check_security_inward(self):
        for picking in self:
            if picking.picking_type_id.code == 'incoming' and picking.purchase_id and not picking.security_check:
                raise ValidationError("Security Inward field is mandatory for receipts linked to a Purchase Order.")


    @api.constrains('grc_qty')
    def _check_grc_qty_vs_po_qty(self):
        for picking in self:
            for move in picking.move_ids_without_package:
                po_line = move.purchase_line_id
                if po_line and picking.grc_qty > po_line.product_qty:
                    raise ValidationError(
                        f"GRC Qty ({picking.grc_qty}) cannot exceed PO Qty ({po_line.product_qty}) for product {move.product_id.display_name}."
                    )


    def get_move_qty(self):
            for rec in self:
                if rec.picking_type_id.code == 'incoming':
                    if rec.move_ids_without_package:
                        count = sum(rec.move_ids_without_package.mapped('quantity'))
                        rec.grc_qty = count
                    else:
                        rec.grc_qty = 0.0
                else:
                    rec.grc_qty = 0.0

    @api.model
    def chat_notification(self):
        if not self.purchase_id or not self.purchase_id.user_id:
            raise ValidationError("No user is assigned to the related Purchase Order.")
        employee = self.purchase_id.user_id.employee_id
        manager = employee.parent_id if employee else False
        if not manager:
            raise ValidationError("No manager (parent) is assigned to the employee of the Purchase Order user.")
        related_partner = manager.related_partner_id
        if not related_partner:
            raise ValidationError("The manager of the employee does not have a related partner.")
        # Get or create the channel
        channel = self.env['discuss.channel'].search([('name', '=', 'Removal GRC')], limit=1)
        if not channel:
            user_ids = self.env['res.users'].search([]).ids
            channel = self.env['discuss.channel'].create({
                'name': 'Removal GRC',
                'channel_type': 'group',
                'channel_partner_ids': [(4, related_partner.id)],
            })
        # Post the message
        channel.message_post(
            body=f"The Line value Deleted for the Receipt {self.name}.",
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    def button_validate(self):
        res = super(Picking, self).button_validate()
        for picking in self:
            # Only for receipts
            if picking.picking_type_id.code == 'incoming':

                # Require bill reference
                if not picking.bill_reference:
                    raise ValidationError("Bill Reference is required")

                # ✅ If return → bill ref must match original
                if picking.return_id:
                    original_ref = picking.return_id.bill_reference
                    if picking.bill_reference != original_ref:
                        raise ValidationError(
                            f"Return Receipt must use the same Bill Reference as the original "
                            f"Receipt {picking.return_id.name} ({original_ref})."
                        )
                elif picking.return_ids:
                    # In case of multiple returns, still enforce original ref
                    original_ref = picking.return_ids[0].bill_reference
                    if picking.bill_reference != original_ref:
                        raise ValidationError(
                            f"Return Receipt must use the same Bill Reference as the original "
                            f"Receipt {picking.return_ids[0].name} ({original_ref})."
                        )
                else:
                    # ✅ Normal receipt → check uniqueness per vendor
                    duplicate = self.search([
                        ('bill_reference', '=', picking.bill_reference),
                        ('id', '!=', picking.id),
                        ('state', '=', 'done'),
                        ('picking_type_id.code', '=', 'incoming'),
                        ('partner_id', '=', picking.partner_id.id),
                    ], limit=1)

                    if duplicate:
                        raise ValidationError(
                            f"The Bill Reference '{picking.bill_reference}' already exists "
                            f"for another validated Receipt. Please enter a unique value."
                        )

            # ✅ Quantity check with PO
            if picking.picking_type_id.code == 'incoming' and picking.purchase_id:
                for move in picking.move_ids_without_package:
                    if move.product_uom_qty < move.quantity:
                        raise ValidationError(
                            _("You cannot receive more quantity (%s) than ordered (%s) for product %s." % (
                                move.quantity, move.product_uom_qty, move.product_id.display_name)))

                receipt_product_ids = {line.product_id.id for line in picking.move_ids_without_package}
                po_product_ids = {
                    line.product_id.id for line in picking.purchase_id.order_line
                    if line.product_id.type == 'consu'}
                if po_product_ids != receipt_product_ids:
                    picking.chat_notification()

        return res
#     def button_validate(self):
#         res = super(Picking, self).button_validate()
# ###################################################################
#         for picking in self:
#             # Only for receipts
#             if picking.picking_type_id.code == 'incoming':
#
#                 # Require bill reference
#                 if not picking.bill_reference:
#                     raise ValidationError(
#                         "Bill Reference is required")
#
#                 # Skip duplicate check if bill_reference is still empty (avoid False error)
#                 if picking.bill_reference:
#                     duplicate = self.search([
#                         ('bill_reference', '=', picking.bill_reference),
#                         ('id', '!=', picking.id),
#                         ('state', '=', 'done'),
#                         ('picking_type_id.code', '=', 'incoming'),
#                     ], limit=1)
#
#                     if duplicate:
#                         raise ValidationError(
#                             f"The Bill Reference '{picking.bill_reference}' already exists for another validated Receipt. Please enter a unique value.")
# ################################################################################
#             if picking.picking_type_id.code == 'incoming' and picking.purchase_id:
#                 for move in picking.move_ids_without_package:
#                     if move.product_uom_qty < move.quantity:
#                         raise ValidationError(_("You cannot receive more quantity (%s) than ordered (%s) for product %s." % (
#                             move.quantity, move.product_uom_qty, move.product_id.display_name)))
#                 receipt_product_ids = {line.product_id.id for line in picking.move_ids_without_package}
#                 po_product_ids = {
#                     line.product_id.id for line in picking.purchase_id.order_line
#                     if line.product_id.type == 'consu'}
#                 if po_product_ids != receipt_product_ids:
#                     picking.chat_notification()
#         return res



class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    project_id = fields.Many2one('project.project', string="Project")







class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic = fields.Json(
        string='Analytic',
        help='Analytic Distribution',
        compute="_compute_analytic_distribution",
        readonly=False,
        store=True,
    )

    analytic_precision = fields.Integer(
        store=False,
        help='Define the precision of percentage decimal value',
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic")
    )
    stock_on_project = fields.Float(
        string='Stock on Project',
        compute='_compute_stock_on_project',
        store=True
    )
    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products',
        store=False
    )
    s_no = fields.Integer(string="S.No", compute="_compute_s_no")

    @api.depends('picking_id', 'picking_id.move_ids_without_package')
    def _compute_s_no(self):
        for move in self:
            picking = move.picking_id
            if not picking:
                move.s_no = 1
                continue

            moves = picking.move_ids_without_package

            for index, line in enumerate(moves, start=1):
                if line == move:  # <<< IMPORTANT FIX
                    move.s_no = index
                    break
            else:
                move.s_no = 1  # fallback (never missing)

    # @api.depends('picking_id', 'picking_id.move_ids_without_package')
    # def _compute_s_no(self):
    #     for move in self:
    #         if move.picking_id:
    #             moves = move.picking_id.move_ids_without_package
    #             # Assign row number based on list position
    #             for index, line in enumerate(moves, start=1):
    #                 if line.id == move.id:
    #                     move.s_no = index
    #         else:
    #             move.s_no = 1

    @api.depends('picking_id.location_id', 'picking_id.picking_type_code')
    def _compute_allowed_products(self):
        Quant = self.env['stock.quant']
        Product = self.env['product.product']

        for rec in self:
            picking = rec.picking_id

            # Only restrict for Delivery Orders
            if picking and picking.picking_type_code == "outgoing" and picking.location_id:
                quants = Quant.search([
                    ('location_id', '=', picking.location_id.id),
                    ('quantity', '>', 0)
                ])
                rec.allowed_product_ids = quants.mapped('product_id')
            else:
                rec.allowed_product_ids = Product.search([])

    @api.depends('product_id', 'picking_id.project_id')
    def _compute_stock_on_project(self):
        for move in self:
            project = getattr(move.picking_id, 'project_id', False)
            product = move.product_id
            if not product:
                move.stock_on_project = 0.0
                continue
            # 🔹 All done moves for this product + project
            done_moves = self.env['stock.move'].search([
                ('state', '=', 'done'),
                ('product_id', '=', product.id),
                ('picking_id.project_id', '=', project.id if project else False)
            ])

            stock_qty = 0.0
            for m in done_moves:
                src = m.location_id.usage
                dest = m.location_dest_id.usage

                # 🔹 Received into project (incoming)
                if src in ['supplier', 'customer'] and dest == 'internal':
                    stock_qty += m.product_uom_qty

                # 🔹 Delivered from project (outgoing)
                elif src == 'internal' and dest in ['customer', 'supplier']:
                    stock_qty -= m.product_uom_qty

            move.stock_on_project = stock_qty

    @api.depends('product_id', 'picking_id.project_id')
    def _compute_analytic_distribution(self):
        ProjectProject = self.env['project.project']
        for line in self:
            if line.analytic:
                continue
            project_id = line._context.get('project_id')
            project = ProjectProject.browse(project_id) if project_id else line.picking_id.project_id
            if project:
                line.analytic = project._get_analytic_distribution()

    # @api.depends('product_id', 'picking_id.project_id')
    # def _compute_analytic_distribution(self):
    #     for line in self:
    #         # Skip recomputing if already set
    #         if line.analytic:
    #             continue
    #         # Use context project_id if available
    #         project_id = line._context.get('project_id')
    #         project = (
    #             self.env['project.project'].browse(project_id)
    #             if project_id else line.picking_id.project_id
    #         )
    #         # If a valid project is found, compute and assign
    #         if project:
    #             line.analytic = project._get_analytic_distribution()
    #         else:
    #             line.analytic = False

    @api.model
    def create(self, values):
        """Set analytic from sale or purchase line if not manually provided."""
        if not values.get('analytic'):
            if values.get('sale_line_id'):
                sale_line = self.env['sale.order.line'].browse(values['sale_line_id'])
                values['analytic'] = sale_line.analytic_distribution
            elif values.get('purchase_line_id'):
                purchase_line = self.env['purchase.order.line'].browse(values['purchase_line_id'])
                values['analytic'] = purchase_line.analytic_distribution
        return super().create(values)

    def _generate_valuation_lines_data(
        self, partner_id, qty, debit_value, credit_value,
        debit_account_id, credit_account_id, svl_id, description
    ):
        res = super()._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value,
            debit_account_id, credit_account_id, svl_id, description
        )

        # Add analytic_distribution to both lines if available
        if self.analytic:
            for line_vals in res.values():
                line_vals['analytic_distribution'] = self.analytic

        return res




class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    project_id = fields.Many2one('project.project', string='Project', related='picking_id.project_id', store=True)
    s_no = fields.Integer(string="S.No", compute="_compute_s_no")

    @api.depends('picking_id', 'picking_id.move_line_ids')
    def _compute_s_no(self):
        for rec in self:
            picking = rec.picking_id
            if not picking:
                rec.s_no = 1
                continue

            lines = picking.move_line_ids

            # SAFE enumeration (no sorting, no id compare)
            for idx, line in enumerate(lines, start=1):
                if line == rec:  # << VERY IMPORTANT (works for NewId)
                    rec.s_no = idx
                    break
            else:
                rec.s_no = 1  # safety fallback
    # @api.depends('picking_id.move_line_ids')
    # def _compute_s_no(self):
    #     for rec in self:
    #         picking = rec.picking_id
    #         if not picking:
    #             rec.s_no = 1
    #             continue
    #
    #         # ALL move lines of the receipt / delivery
    #         lines = picking.move_line_ids.sorted(lambda l: (l.id))
    #
    #         for idx, line in enumerate(lines, start=1):
    #             if line.id == rec.id:
    #                 rec.s_no = idx
    #                 break


class StockLocation(models.Model):
    _inherit = 'stock.location'

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one(
        'res.country.state',
        string="State",
        domain="[('country_id', '=?', country_id)]"
    )
    zip = fields.Char(string="ZIP")
    country_id = fields.Many2one('res.country', string="Country")
    l10n_in_gst_treatment = fields.Selection([
        ('regular', 'Registered Business - Regular'),
        ('composition', 'Registered Business - Composition'),
        ('unregistered', 'Unregistered Business'),
        ('consumer', 'Consumer'),
        ('overseas', 'Overseas'),
        ('special_economic_zone', 'Special Economic Zone'),
        ('deemed_export', 'Deemed Export'),
        ('uin_holders', 'UIN Holders'),
    ], string="GST Treatment", default="regular")
    l10n_in_gstin = fields.Char(string="GSTIN")
    pan = fields.Char(string="PAN")

    @api.onchange('l10n_in_gstin')
    def _onchange_gstin(self):
        """Auto-fill PAN, State, Country, GST Treatment based on GSTIN"""
        if self.l10n_in_gstin:
            gstin = self.l10n_in_gstin.strip().upper()
            if len(gstin) == 15:
                # PAN from GSTIN (chars 3-12)
                self.pan = gstin[2:12]

                # State from first 2 digits
                state_code = gstin[:2]
                state = self.env['res.country.state'].search([
                    ('l10n_in_tin', '=', state_code)
                ], limit=1)
                if state:
                    self.state_id = state.id
                    self.country_id = state.country_id.id

                # Default GST treatment
                self.l10n_in_gst_treatment = 'regular'

    @api.onchange('state_id')
    def _onchange_state_id(self):
        """Auto-fill country based on selected state"""
        if self.state_id:
            self.country_id = self.state_id.country_id.id
        else:
            self.country_id = False