from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    """Enable Stock Pickings Feature From Customer Invoice and Supplier Bills"""
    _inherit = 'res.config.settings'

    stock_picking = fields.Boolean("Stock Picking From Invoice", related='company_id.stock_picking',
                                   readonly=False, help="Enable Stock Pickings Feature From Customer Invoice")

    stock_picking_bill = fields.Boolean("Stock Picking From Bills", related='company_id.stock_picking_bill',
                                        readonly=False, help="Enable Stock Pickings Feature From Supplier Bills")


class ResCompany(models.Model):
    """Stock picking invoice and bill flog to get"""
    _inherit = 'res.company'

    stock_picking = fields.Boolean("Stock Picking From Invoice")
    stock_picking_bill = fields.Boolean("Stock Picking From Bills")


class StockPicking(models.Model):
    """new field insert in stock.picking for Invoice to stock update"""
    _inherit = 'stock.picking'

    invoice_id = fields.Many2one('account.move', string="Invoice")