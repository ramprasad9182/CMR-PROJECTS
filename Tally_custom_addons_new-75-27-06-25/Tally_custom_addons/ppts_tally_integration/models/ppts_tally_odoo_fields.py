"""Odoo16 Module: Add In New Fields"""
from odoo import fields, models


class ProductCategory(models.Model):
    """In product category model to include additional fields related to Tally integration"""
    _inherit = 'product.category'

    tally_id = fields.Integer(string='Tally ID', copy=False, readonly=True)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)


class ProductProduct(models.Model):
    """In product template model to include additional fields related to Tally integration"""
    _inherit = 'product.template'

    tally_id = fields.Integer(string='Tally ID', copy=False, readonly=True)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'), ('write', 'Write')],
                                  string='NDW Select', default='new', copy=False)


class UomCategory(models.Model):
    """In uom category model to include additional fields related to Tally integration"""
    _inherit = 'uom.category'

    tally_id = fields.Integer(string='Tally ID', copy=False, readonly=True)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)


class ProductUom(models.Model):
    """In uom model to include additional fields related to Tally integration"""
    _inherit = 'uom.uom'

    tally_id = fields.Integer(string="Tally ID", copy=False)


class StockLocation(models.Model):
    """In stock location model to include additional fields related to Tally integration"""
    _inherit = 'stock.location'

    tally_id = fields.Integer(string='Tally ID', copy=False, readonly=True)


class PurchaseOrder(models.Model):
    """In purchase order model to include additional fields related to Tally integration"""
    _inherit = 'purchase.order'

    tally_po_id = fields.Char(string='Tally PO ID', copy=False, readonly=True)
    tally_po_name = fields.Char(string='Tally PO Name', copy=False, readonly=True)
    tally_order_no = fields.Integer(string='Tally Order No', copy=False, readonly=True)

    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)


class PurchaseAccountMove(models.Model):
    """In account move model to include additional fields related to Tally integration"""
    _inherit = 'account.move'

    tally_id = fields.Integer(string='Tally ID', copy=False)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)

    # sync_to_tally = fields.Boolean(string='Sync Journal Transactions to Tally', copy=False,
    #                                related='journal_id.sync_to_tally')

    tally_bill_id = fields.Integer(string='Tally Bill No', copy=False)
    tally_bill_name = fields.Char(string='Tally Bill Name', copy=False)
    tally_po_id = fields.Char(string='Tally PO Name', copy=False)

    tally_invoice_id = fields.Integer(string='Tally Invoice No', copy=False)
    tally_invoice_name = fields.Char(string='Tally Invoice Name', copy=False)
    tally_so_id = fields.Char(string='Tally SO Name', copy=False)

    tally_credit_id = fields.Integer(string='Tally Credit No',copy=False)
    tally_credit_name = fields.Char(string='Tally Credit Name',copy=False)

    tally_debit_id = fields.Integer(string='Tally Debit No', copy=False)
    tally_debit_name = fields.Char(string='Tally Debit Name',copy=False)

    tally_journal_id = fields.Integer(string='Tally Journal Id',copy=False)
    tally_journal_name = fields.Char(string='Tally Journal Name',copy=False)

    purchase_tally_id = fields.Integer(string='Purchase Tally ID', copy=False, readonly=True)
    balance_id = fields.Integer(string='Tally opening Bal ID', copy=False, readonly=True)

    bt_no = fields.Char(string='Transaction No', copy=False, readonly=True)
    bt_name = fields.Char(string='Transaction Name', copy=False, readonly=True)
    bt_type = fields.Char(string='Transaction Type', copy=False, readonly=True)
    bt_date = fields.Char(string='Transaction Date', copy=False, readonly=True)

    picking_id = fields.Many2one('stock.picking', 'Picking')
    sale_id = fields.Many2one('sale.order', 'SO')
    state_id = fields.Many2one('sale.order', 'SO')
    country_id = fields.Many2one('sale.order', 'SO')
    street = fields.Char('SO')
    street2 = fields.Char('SO')


class SaleOrder(models.Model):
    """In sale order model to include additional fields related to Tally integration"""
    _inherit = 'sale.order'

    tally_id = fields.Integer(string='Tally_id', copy=False, readonly=True)
    reference_no = fields.Char(string='Reference Number', copy=False, readonly=True)
    tally_so_id = fields.Integer(string='Tally SO ID', copy=False, readonly=True)
    tally_so_name = fields.Char(string='Tally SO Name', copy=False, readonly=True)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)


class AccountPayment(models.Model):
    """In account payment model to include additional fields related to Tally integration"""
    _inherit = 'account.payment'

    tally_payment_id = fields.Integer(string='Tally Payment Id', copy=False, readonly=True)
    tally_payment_name = fields.Char(string='Tally Payment Name', copy=False, readonly=True)
    check_date = fields.Date(string='Check Date', copy=False)
    is_check = fields.Boolean(string='Is Check', copy=False)


class StockPicking(models.Model):
    """In stock picking model to include additional fields related to Tally integration"""
    _inherit = 'stock.picking'

    is_tally_flag = fields.Boolean(string="Is Tally Flag")
    tally_receipt_no = fields.Char(string="Tally Id")
    tally_receipt_name = fields.Char(string="Tally Name")
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)


class ResPartner(models.Model):
    """In res partner model to include additional fields related to Tally integration"""
    _inherit = "res.partner"
    tally_id = fields.Integer(string='Tally ID', copy=False)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    type_partner = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier')],
                                  string='Partner Type', copy=False,required=True)

    customer = fields.Boolean(string='customer',copy=False)
    supplier = fields.Boolean(string='supplier',copy=False)
    billwise = fields.Boolean(string='billwise',copy=False)

    account_group_id = fields.Many2one('account.group',string='account group Name',copy=False)
    ndw_select = fields.Selection([('new','New'),('done','Done'),('write','Write')],
                                  string='NDW Select',default='new',copy=False)
    contact_person = fields.Char(string='Contact Person',copy=False)
    pan_no = fields.Char("PAN")
    old_name = fields.Char(string="Old Name", readonly=True)

class AccountGroup(models.Model):
    """In account group model to include additional fields related to Tally integration"""
    _inherit = "account.group"

    parent_group_id = fields.Many2one('account.group', index=True,string='Parent Group')

    tally_id = fields.Integer(string='Tally ID', copy=False)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False, tracking=True)
    ndw_select = fields.Selection([('new','New'),('done','Done'),('write','Write')],
                                  string='NDW Select',default='new',copy=False, tracking=True)
    old_name = fields.Char(string="Old Name", readonly=True)


class ProductTallySync(models.Model):
    """In product model to include additional fields related to Tally integration"""
    _inherit = 'product.product'

    tally_flag = fields.Boolean(string='Tally Flag', copy=False)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'),
                                   ('write', 'Write')], string='NDW Select',
                                  default='new', copy=False)
    tally_id = fields.Char(string='Tally ID', copy=False)


class Account(models.Model):
    """In account model to include additional fields related to Tally integration"""
    _inherit = "account.account"


    group_id = fields.Many2one('account.group', store=True, readonly=True,
                               help="Account prefixes can determine account groups.")
    is_tax = fields.Boolean(string='Is Tax', copy=False)
    types_tax = fields.Selection([('gst', 'GST'), ('tcs', 'TCS'), ('tds', 'TDS'),
                                  ('vat', 'VAT'), ('others', 'Others')],
                                  string ='Type of Duty/ Tax', copy=False, tracking=True)
    types_gst = fields.Selection([('cgst', 'Central Tax'), ('sgst', 'State Tax'),
                                  ('igst', 'Integrated Tax'), ('cess', 'Cess')],
                                  string ='Tax Type', copy=False, tracking=True)
    gst = fields.Boolean(string='customer', copy=False, tracking=True)
    tcs = fields.Boolean(string='TCS', copy=False, tracking=True)
    tally_id = fields.Integer(string='Tally ID', copy=False)
    tally_flag = fields.Boolean(string='Tally Flag', copy=False, tracking=True)
    ndw_select = fields.Selection([('new', 'New'), ('done', 'Done'), ('write', 'Write')],
                                  string='NDW Select', default='new', copy=False, tracking=True)
    tally_group_id = fields.Char(string='Tally Group', store=True,
                                     help="To map the Tally Account Group in COA")

    old_name = fields.Char(string="Old Name", readonly=True)
