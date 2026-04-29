from odoo import models, fields, api, _


class ProductMovementReport(models.TransientModel):
    _name = "product.movement.report"
    _description = "Product Movement Report"
    _order = "id desc"

    name = fields.Char(string="Reference", readonly=True, copy=False, default="New")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")

    line_ids = fields.One2many(
        "product.movement.report.line",
        "report_id",
        string="Product Lines"
    )

    # @api.model
    # def create(self, vals):
    #     """Assign sequence number on creation"""
    #     if vals.get("name", "New") == "New":
    #         vals["name"] = self.env["ir.sequence"].next_by_code("product.movement.report") or _("New")
    #     return super().create(vals)

    # sep1st code
    # def action_fetch_products(self):
    #     """
    #     Project-wise product movement report
    #     --------------------------------------------------
    #     - Opening Balance = Net movement before from_date for that project
    #     - Received Qty    = (supplier->internal OR customer->internal) within [from_date, to_date] for that project
    #     - Delivered Qty   = (internal->customer OR internal->supplier) within [from_date, to_date] for that project
    #     - Closing Balance = Opening + Received - Delivered
    #     - Each line corresponds to one product + project combination
    #     """
    #     self.ensure_one()
    #     self.line_ids.unlink()
    #
    #     products = self.env['product.product'].search([('type', '=', 'consu')])
    #     for product in products:
    #
    #         # 1) ALL-TIME project mapping (ignore dates)
    #         project_moves = self.env['stock.move'].search([
    #             ('product_id', '=', product.id),
    #             ('state', '=', 'done'),
    #             '|',
    #             '&', ('location_id.usage', '=', 'supplier'), ('location_dest_id.usage', '=', 'internal'),  # Receipts
    #             '&', ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'customer'),  # Deliveries
    #         ])
    #         project_ids_all_time = set()
    #         for m in project_moves:
    #             if m.picking_id and m.picking_id.project_id:
    #                 project_ids_all_time.add(m.picking_id.project_id.id)
    #
    #         # 2) If no project, use False
    #         if not project_ids_all_time:
    #             project_ids_all_time = [False]
    #
    #         # 3) Compute movements per project
    #         for project_id in project_ids_all_time:
    #             # Opening balance (before from_date)
    #             opening_moves = self.env['stock.move'].search([
    #                 ('product_id', '=', product.id),
    #                 ('state', '=', 'done'),
    #                 ('date', '<', self.from_date),
    #                 ('picking_id.project_id', '=', project_id) if project_id else ('picking_id', '=', False),
    #             ])
    #             opening_balance = 0.0
    #             for m in opening_moves:
    #                 if (m.location_id.usage == 'supplier' and m.location_dest_id.usage == 'internal') \
    #                         or (m.location_id.usage == 'customer' and m.location_dest_id.usage == 'internal'):
    #                     opening_balance += m.product_uom_qty
    #                 elif (m.location_id.usage == 'internal' and m.location_dest_id.usage in ['customer', 'supplier']):
    #                     opening_balance -= m.product_uom_qty
    #
    #             # Period movements (from_date to to_date)
    #             period_moves = self.env['stock.move'].search([
    #                 ('product_id', '=', product.id),
    #                 ('state', '=', 'done'),
    #                 ('date', '>=', self.from_date),
    #                 ('date', '<=', self.to_date),
    #                 ('picking_id.project_id', '=', project_id) if project_id else ('picking_id', '=', False),
    #             ])
    #             received = delivered = 0.0
    #             for m in period_moves:
    #                 if (m.location_id.usage == 'supplier' and m.location_dest_id.usage == 'internal') \
    #                         or (m.location_id.usage == 'customer' and m.location_dest_id.usage == 'internal'):
    #                     received += m.product_uom_qty
    #                 elif (m.location_id.usage == 'internal' and m.location_dest_id.usage in ['customer', 'supplier']):
    #                     delivered += m.product_uom_qty
    #
    #             closing_balance = opening_balance + received - delivered
    #
    #             # 4) Create report line
    #             self.env['product.movement.report.line'].create({
    #                 'report_id': self.id,
    #                 'product_id': product.id,
    #                 'opening_balance': opening_balance,
    #                 'received_qty': received,
    #                 'delivered_qty': delivered,
    #                 'closing_balance': closing_balance,
    #                 'project_id': project_id,
    #             })

    def action_fetch_products(self):
        """
        Project-wise product movement report
        --------------------------------------------------
        - Opening Balance = Net movement before from_date for that project
        - Received Qty    = (supplier->internal OR customer->internal) within [from_date, to_date] for that project
        - Delivered Qty   = (internal->customer OR internal->supplier) within [from_date, to_date] for that project
        - Closing Balance = Opening + Received - Delivered
        - Each line corresponds to one product + project combination
        """
        self.ensure_one()
        self.line_ids.unlink()

        # 🔹 Only products that appear in stock moves with state 'done'
        done_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('product_id.type', '=', 'consu'),
            ('product_id.active', '=', True),
        ])
        product_ids = done_moves.mapped('product_id')

        for product in product_ids:

            # 1) ALL-TIME project mapping (ignore dates)
            project_moves = done_moves.filtered(lambda m: m.product_id == product)
            project_ids_all_time = set(
                m.picking_id.project_id.id
                for m in project_moves
                if m.picking_id and m.picking_id.project_id
            )

            # 2) If no project, include a "no project" case
            if not project_ids_all_time:
                project_ids_all_time = [None]

            # 3) Compute movements per project
            for project_id in project_ids_all_time:

                # 🔹 Base domain for moves of this product + project
                domain_base = [
                    ('product_id', '=', product.id),
                    ('state', '=', 'done'),
                ]
                if project_id:
                    domain_base.append(('picking_id.project_id', '=', project_id))
                else:
                    domain_base.append(('picking_id.project_id', '=', False))  # no project

                # 🔹 Opening balance (before from_date)
                opening_moves = self.env['stock.move'].search(domain_base + [
                    ('date', '<', self.from_date),
                ])
                opening_balance = 0.0
                for m in opening_moves:
                    if (m.location_id.usage in ['supplier', 'customer']) and m.location_dest_id.usage == 'internal':
                        opening_balance += m.product_uom_qty
                    elif m.location_id.usage == 'internal' and m.location_dest_id.usage in ['customer', 'supplier']:
                        opening_balance -= m.product_uom_qty

                # 🔹 Period movements (from_date to to_date)
                period_moves = self.env['stock.move'].search(domain_base + [
                    ('date', '>=', self.from_date),
                    ('date', '<=', self.to_date),
                ])
                received = delivered = 0.0
                for m in period_moves:
                    if (m.location_id.usage in ['supplier', 'customer']) and m.location_dest_id.usage == 'internal':
                        received += m.product_uom_qty
                    elif m.location_id.usage == 'internal' and m.location_dest_id.usage in ['customer', 'supplier']:
                        delivered += m.product_uom_qty

                closing_balance = opening_balance + received - delivered

                # 🔹 Skip if product has no movement at all
                if opening_balance == 0 and received == 0 and delivered == 0 and closing_balance == 0:
                    continue

                # 🔹 Create report line
                self.env['product.movement.report.line'].create({
                    'report_id': self.id,
                    'product_id': product.id,
                    'opening_balance': opening_balance,
                    'received_qty': received,
                    'delivered_qty': delivered,
                    'closing_balance': closing_balance,
                    'project_id': project_id or False,  # keep False if no project
                })



    def action_open_lines(self):
        """Open report lines in separate tree view with group by"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Product Movement Lines',
            'res_model': 'product.movement.report.line',
            'view_mode': 'list',
            'domain': [('report_id', '=', self.id)],
            # 'context': {'search_default_group_product': 1},  # Auto group by product
        }


class ProductMovementReportLine(models.TransientModel):
    _name = "product.movement.report.line"
    _description = "Product Movement Report Line"

    report_id = fields.Many2one("product.movement.report", string="Report")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    received_qty = fields.Float("Received Qty", readonly=True, digits="Product Unit of Measure")
    delivered_qty = fields.Float("Delivered Qty", readonly=True, digits="Product Unit of Measure")
    vendor_return_qty = fields.Float("Vendor Return Qty", readonly=True, digits="Product Unit of Measure")
    customer_return_qty = fields.Float("Customer Return Qty", readonly=True, digits="Product Unit of Measure")
    opening_balance = fields.Float("Opening Balance", readonly=True, digits="Product Unit of Measure")
    closing_balance = fields.Float("Closing Balance", readonly=True, digits="Product Unit of Measure")
    # project_ids = fields.Many2many("project.project", string="Projects", readonly=True)
    project_id = fields.Many2one("project.project", string="Project", readonly=True)

    def action_view_stock_moves(self):
        """Open related stock moves for this product and project, filtered by report date range"""
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('state', '=', 'done'),
            ('date', '>=', self.report_id.from_date),
            ('date', '<=', self.report_id.to_date),
            ('product_id.type', '=', 'consu'),
        ]
        if self.project_id:
            domain += [('picking_id.project_id', '=', self.project_id.id)]
        return {
            'name': 'Stock Moves',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list',
            'views': [(self.env.ref('cmr_project.view_stock_move_tree_custom').id, 'list')],
            'domain': domain,
            'target': 'current',
        }
