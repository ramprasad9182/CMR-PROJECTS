"""Odoo16 Module: Tally Integration Tool"""
import logging
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)
CreationAlterType = [('none', 'None'), ('odoo', 'Odoo to Tally'), ('tally', 'Tally to Odoo')]

handler = logging.FileHandler('logfile.log', encoding='utf-8')
_logger.addHandler(handler)
_logger.setLevel(logging.INFO)


class mymodel(models.Model):
    _name = "ppts.tally.integration"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Auto Tally Integration Tool"

# class DbConfig(models.Model):
#     _name = 'mysql.dbconfig'
#     _description = 'MySQL Database Configuration'
#
#     company_name = fields.Char('Company Name')
#
#     def fetch_and_print_company_names(self):
#         # Fetch records from the model (You can add specific filters if needed)
#         db_configs = self.env['mysqldb.config'].sudo().search([])  # This will get all records
#
#         # Print the company names of each record
#         for db_config in db_configs:
#             print('company_name', db_config.company_name)

class PptsTallyIntegration(models.Model):
    """The connection to a Tally Server and Sends data """
    _name = "ppts.tally.integration"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Tally Integration Tool"
    _rec_name = 'created_by'
    CreationAlterType = [('none', 'None'), ('odoo', 'Odoo to Tally'), ('tally', 'Tally to Odoo')]
    created_by = fields.Many2one('res.users',
                                 default=lambda self: self.env.uid,
                                 string='Created By',tracking=True)
    created_date = fields.Date(string='Created On',
                               default=lambda self: fields.Date.today(),tracking=True)

    sync_start_date = fields.Date(string='Sync From Date',
                                  default=lambda self: fields.Date.today(),tracking=True)
    sync_end_date = fields.Date(string='Sync To Date',
                                default=lambda self: fields.Date.today(),
                                tracking=True)
    enable_auto_sync = fields.Boolean("Turn On Auto Sync",tracking=True)
    company_id = fields.Many2one('res.company',string="Base Company",
                                 default=lambda self: self.env.company,tracking=True)
    is_active = fields.Boolean('Active', help='The primary co   nfiguration of Tally Tool',
                               default=True)
    # tally_company = fields.Char('Tally Company Name', required=True, help='enter tally company name')
    tally_company = fields.Selection(
            selection=lambda self: self._get_tally_company_selection(),
            string="Tally Company Name",
            required=True,
            help='Select Tally company name'
     )

    @api.model
    def _get_tally_company_selection(self):
            """Fetch company names from mysql.dbconfig for the selection field."""
            # Fetch company names from mysql.dbconfig model
            company_names = self.env['mysqldb.config'].sudo().search([]).mapped('company_name')
            return [(name, name) for name in company_names]

    @api.onchange('tally_company')
    def _onchange_tally_company(self):
            """When `tally_company` changes, ensure the selected company is valid."""
            valid_companies = [company[0] for company in self._get_tally_company_selection()]
            if self.tally_company and self.tally_company not in valid_companies:
                raise UserError("The entered Tally Company is not in the list of available companies.")
    #mandatory
    property_recieveable = fields.Many2one('account.account', string='Account Recieveable',
                                           domain=[('account_type', '=', 'asset_receivable'),
                                                  ('deprecated', '=', False),
                                                  ],
                                           help='The field to config the default '
                                                'Partner Recieveable COA',
                                           tracking=True, required=True)
    property_payable = fields.Many2one('account.account', string='Account Payable',
                                       domain=[('account_type', '=', 'liability_payable'),
                                               ('deprecated', '=', False),
                                               ],
                                       help='The field to config the default Partner Payable COA',
                                       tracking=True, required=True)
    # Masters part

    res_coa = fields.Boolean("COA",tracking=True)
    res_coa_new = fields.Selection(CreationAlterType, default='none',
                                   string="Creation Type",tracking=True)
    res_coa_alt = fields.Selection(CreationAlterType, default='none',
                                   string="Alteration Type",tracking=True)

    is_account_group = fields.Boolean("Partner Categories",tracking=True)
    account_group_new = fields.Selection(CreationAlterType, default='none',
                                         string="Creation Type",tracking=True)
    res_partner_categ_alt = fields.Selection(CreationAlterType, default='none',
                                             string="Alteration Type",tracking=True)

    res_partner_flag = fields.Boolean("Partners",tracking=True)
    res_partner_new_mem = fields.Selection(CreationAlterType, default='none',
                                           string="Creation Type",tracking=True)
    res_partner_alt = fields.Selection(CreationAlterType, default='none',
                                       string="Alteration Type",tracking=True)

    #inventory
    products_group = fields.Boolean("Product Categories",tracking=True)
    products_group_new = fields.Selection(CreationAlterType, default='none',
                                          string="Creation Type",tracking=True)
    products_group_alt = fields.Selection(CreationAlterType, default='none',
                                          string="Alteration Type",tracking=True)

    products_uom = fields.Boolean("UOM",tracking=True)
    products_uom_new = fields.Selection(CreationAlterType, default='none',
                                        string="Creation Type",tracking=True)
    products_uom_alt = fields.Selection(CreationAlterType, default='none',
                                        string="Alteration Type",tracking=True)

    products_products = fields.Boolean("Product",tracking=True)
    products_products_new = fields.Selection(CreationAlterType, default='none',
                                             string="Creation Type",tracking=True)
    products_products_alt = fields.Selection(CreationAlterType, default='none',
                                             string="Alteration Type",tracking=True)

    products_category =  fields.Boolean('Product Category',tracking=True)
    products_category_new = fields.Selection(CreationAlterType, default='none',
                                             string="Creation Type",tracking=True)
    products_category_alt = fields.Selection(CreationAlterType, default='none',
                                             string="Alteration Type",tracking=True)

    #Voucher

    so = fields.Boolean("Sales Order",tracking=True)
    so_new = fields.Selection(CreationAlterType, default='none',
                              string="Creation Type",tracking=True)
    so_alt = fields.Selection(CreationAlterType, default='none',
                              string="Alteration Type",tracking=True)

    po = fields.Boolean("Purchase Order",tracking=True)
    po_new = fields.Selection(CreationAlterType, default='none',
                              string="Creation Type",tracking=True)
    po_alt = fields.Selection(CreationAlterType, default='none',
                              string="Alteration Type",tracking=True)

    gdn = fields.Boolean("Goods Delivery",tracking=True)
    gdn_new = fields.Selection(CreationAlterType, default='none',
                               string="Creation Type",tracking=True)
    gdn_alt = fields.Selection(CreationAlterType, default='none',
                               string="Alteration Type",tracking=True)

    grn = fields.Boolean("Goods Receipt",tracking=True)
    grn_new = fields.Selection(CreationAlterType, default='none',
                               string="Creation Type",tracking=True)
    grn_alt = fields.Selection(CreationAlterType, default='none',
                               string="Alteration Type",tracking=True)

    invoices = fields.Boolean("Customer Invoices",tracking=True)
    invoices_new = fields.Selection(CreationAlterType, default='none',
                                    string="Creation Type",tracking=True)
    invoices_alt = fields.Selection(CreationAlterType, default='none',
                                    string="Alteration Type",tracking=True)

    bills = fields.Boolean("Vendor Bills",tracking=True)
    bills_new = fields.Selection(CreationAlterType, default='none',
                                 string="Creation Type",tracking=True)
    bills_alt = fields.Selection(CreationAlterType, default='none',
                                 string="Alteration Type",tracking=True)

    cr_note = fields.Boolean("Credit Note",tracking=True)
    cr_note_new = fields.Selection(CreationAlterType, default='none',
                                   string="Creation Type",tracking=True)
    cr_note_alt = fields.Selection(CreationAlterType, default='none',
                                   string="Alteration Type",tracking=True)

    dr_note = fields.Boolean("Debit Note",tracking=True)
    dr_note_new = fields.Selection(CreationAlterType, default='none',
                                   string="Creation Type",tracking=True)
    dr_note_alt = fields.Selection(CreationAlterType, default='none',
                                   string="Alteration Type",tracking=True)

    out_payments = fields.Boolean("Vendor Payment",tracking=True)
    out_payments_new = fields.Selection(CreationAlterType, default='none',
                                        string="Creation Type",tracking=True)
    out_payments_alt = fields.Selection(CreationAlterType, default='none',
                                        string="Alteration Type",tracking=True)

    in_payments = fields.Boolean("Customer Payment",tracking=True)
    in_payments_new = fields.Selection(CreationAlterType, default='none',
                                       string="Creation Type",tracking=True)
    in_payments_alt = fields.Selection(CreationAlterType, default='none',
                                       string="Alteration Type",tracking=True)

    contra = fields.Boolean("Contra",tracking=True)
    contra_new = fields.Selection(CreationAlterType, default='none',
                                  string="Creation Type",tracking=True)
    contra_alt = fields.Selection(CreationAlterType, default='none',
                                  string="Alteration Type",tracking=True)

    journals = fields.Boolean("Journals",tracking=True)
    journals_new = fields.Selection(CreationAlterType, default='none',
                                    string="Creation Type",tracking=True)
    journals_alt = fields.Selection(CreationAlterType, default='none',
                                    string= "Alteration Type",tracking=True)

    stk_journals = fields.Boolean("Inventory Move",tracking=True)
    stk_journals_new = fields.Selection(CreationAlterType, default='none',
                                        string="Creation Type",tracking=True)
    stk_journals_alt = fields.Selection(CreationAlterType, default='none',
                                        string="Alteration Type",tracking=True)

    is_purchase = fields.Boolean("Purchase Order", tracking=True)
    purchase_order_new = fields.Selection(CreationAlterType, default='none',
                                          string="Creation Type", tracking=True)
    purchase_order_alt = fields.Selection(CreationAlterType, default='none',
                                          string="Alteration Type", tracking=True)

    is_sale = fields.Boolean("Sale Order", tracking=True)
    sale_order_new = fields.Selection(CreationAlterType, default='none',
                                      string="Creation Type", tracking=True)
    sale_order_alt = fields.Selection(CreationAlterType, default='none',
                                      string="Alteration Type", tracking=True)

    is_receipt = fields.Boolean("Stock Picking", tracking=True)
    receipt_note_new = fields.Selection(CreationAlterType, default='none',
                                        string="Creation Type", tracking=True)
    receipt_alt = fields.Selection(CreationAlterType, default='none',
                                   string="Alteration Type", tracking=True)

    is_delivery= fields.Boolean("Stock", tracking=True)
    delivery_note_new = fields.Selection(CreationAlterType, default='none',
                                         string="Creation Type", tracking=True)
    delivery_alt = fields.Selection(CreationAlterType, default='none',
                                    string="Alteration Type", tracking=True)

    is_credit = fields.Boolean("Cridet", tracking=True)
    credit_note_new = fields.Selection(CreationAlterType, default='none',
                                       string="Creation Type", tracking=True)
    credit_alt = fields.Selection(CreationAlterType, default='none',
                                  string="Alteration Type", tracking=True)

    is_debit = fields.Boolean("Cridet", tracking=True)
    debit_note_new = fields.Selection(CreationAlterType, default='none',
                                      string="Creation Type", tracking=True)
    debit_alt = fields.Selection(CreationAlterType, default='none',
                                 string="Alteration Type", tracking=True)

    @api.constrains('is_active')
    def _check_is_primary(self):
        const = self.search_count([('is_active', '=', True)])
        if const > 1:
            raise ValidationError(_('The Primary Configuration Is Active In Other Form'))



    def button_res_cridet_note_sync(self):
        """The credit note model record has been sent to the Tally server."""
        credit_note = self.env['account.move'].search([('move_type', '=', 'out_refund'),
                                                       ('state','=','posted'),
                                                       ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in credit_note:
            res = rec.sudo().action_credit_note()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'out_refund'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)


    def button_res_delivery_note_sync(self):
        """The delivery note model record has been sent to the Tally server."""
        delivery_note = self.env['stock.picking'].search([
            ('picking_type_id.name','=','Delivery Orders'),('state','=','done'),
            ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in delivery_note:
            res = rec.action_delivery_note()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'receipt'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_res_receipt_note_sync(self):
        """The receipt note model record has been sent to the Tally server."""
        receipt_note = self.env['stock.picking'].search([('picking_type_id.name','=','Receipts'),
                                                         ('state','=','done'),
                                                         ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in receipt_note:
            res = rec.action_receipt_note()
            if res and isinstance(res, dict):
                tally_log_ids += res.get('tally_log_ids',[])
                print('Odoo log id:', tally_log_ids)
            else:
                _logger.warning("res is None or not a dictionary. Skipping tally_log_ids update.")

            if isinstance(res, dict) and 'tally_log_xml_data' in res:
                tally_log_xml_data.append(res['tally_log_xml_data'])
            else:
                print('Warning MSG', tally_log_xml_data)
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'receipt'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)


    def button_res_debit_note_sync(self):
        """The debit note model record has been sent to the Tally server."""
        debit_note = self.env['account.move'].search([('move_type', '=', 'in_refund'),
                                                      ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in debit_note:
            res = rec.action_debit_note()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'in_refund'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_bills_sync(self):
        """The purchase bill model record has been sent to the Tally server."""
        bills = self.env['account.move'].sudo().search(
            [('move_type','=','in_invoice'),('state', '=', 'posted'), ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in bills:
            res = rec.sudo().action_purchase_bill_sync()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])
            tally_log_ids += res
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'in_invoice'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_purchase_order(self):
        """The purchase order model record has been sent to the Tally server."""
        # purchase_order_ids = self.env['purchase.order'].sudo().search([('state', '=', 'purchase'),
        # ('ndw_select', '!=', 'done'), ('date_order', '>=', self.sync_start_date),
        #      ('date_order', '<=', self.sync_end_date)])
        purchase_order_ids = self.env['purchase.order'].sudo().search(
            [('state', '=', 'purchase'), ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in purchase_order_ids:
            res = rec.sudo().action_purchase_order()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'purchase_order'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_sale_order(self):
        """The sale order model record has been sent to the Tally server."""
        # sale_order_ids = self.env['sale.order'].sudo().search([('state', '=', 'sale'),
        # ('ndw_select', '!=', 'done'),('validity_date', '>=', self.sync_start_date),
        #      ('validity_date', '<=', self.sync_end_date)])

        sale_order_ids = self.env['sale.order'].sudo().search(
            [('state', '=', 'sale'), ('ndw_select', '!=', 'done')])

        tally_log_ids = []
        tally_log_xml_data = []

        for rec in sale_order_ids:
            res = rec.sudo().action_sale_order()
            tally_log_ids += res.get('tally_log_ids',[])
            tally_log_xml_data.append(res['tally_log_xml_data'])

            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'master_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'sale_order'
                }

                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_res_account_group_sync(self):
        """The account group model record has been sent to the Tally server."""
        print('Account_group Start')
        accounts = self.env['account.group'].search([('ndw_select', '=', 'new')])
        # accounts = (self.env['account.group'].fields_get(['ndw_select']))
        # fields_info = self.env['account.group'].fields_get()
        # for field_name, field_meta in fields_info.items():
        #     print(f"{field_name} → {field_meta['type']}")
        groups = self.env['account.group'].search([])
        company_ids = groups.mapped('company_id.id')  # just the ID values
        print(company_ids)
        print('accgrp details', accounts)
        tally_log_ids = []
        tally_log_xml_data = []
        print('Tallylog', tally_log_xml_data)
        for rec in accounts:
            res = rec.action_sync_ac_grp()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
            print("account",tally_log_xml_data)
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_xml_data),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'group'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)
            print('final grp data', tally_log_obj_id)

        accounts = self.env['account.group'].search([('ndw_select', '=', 'write')])
        # accounts = (self.env['account.group'].fields_get(['ndw_select']))
        # fields_info = self.env['account.group'].fields_get()
        # for field_name, field_meta in fields_info.items():
        #     print(f"{field_name} → {field_meta['type']}")
        groups = self.env['account.group'].search([])
        company_ids = groups.mapped('company_id.id')  # just the ID values
        print(company_ids)
        print('accgrp details', accounts)
        tally_log_ids = []
        tally_log_xml_data = []
        print('Tallylog', tally_log_xml_data)
        for rec in accounts:
            res = rec.action_sync_ac_grp_alter()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
            print("account", tally_log_xml_data)
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_xml_data),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'group'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)
            print('final grp data', tally_log_obj_id)

    def button_res_partner_sync(self):
        """The res partner model record has been sent to the Tally server."""
        partners = self.env['res.partner'].sudo().search([('ndw_select', '=', 'new')])
        print('partner', partners)
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in partners:
            res = rec.action_sync_partner()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'partner'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

        """The res partner model record has been sent to the Tally server."""
        partners = self.env['res.partner'].sudo().search([('ndw_select', '=', 'write')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in partners:
            res = rec.action_sync_partner_alter()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'partner'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_res_coa_sync(self):
        """The chat of account model record has been sent to the Tally server."""
        accounts = self.env['account.account'].search([('ndw_select', '=', 'new'),
                                                       ('account_type', '!=', 'Bank and Cash')])
        # accounts = self.env['account.account'].search([('ndw_select', '!=', 'done'),
        #                                                ('account_type', '!=', 'Bank and Cash'),
        #                                                ('company_id', '=', 1)])
        print('newcoa', accounts)
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in accounts:
            res = rec.action_sync_coa()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'coa'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

        """The chat of account model record has been sent to the Tally server."""
        accounts = self.env['account.account'].search([('ndw_select', '=', 'write'),
                                                       ])
        # accounts = self.env['account.account'].search([('ndw_select', '!=', 'done'),
        #                                                ('account_type', '!=', 'Bank and Cash'),
        #                                                ('company_id', '=', 1)])
        print('altercoarec', accounts)
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in accounts:
            res = rec.action_sync_coa_alter()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'master_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'coa'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)


    def button_invoices_sync(self):
        """The sale invoice model record has been sent to the Tally server."""
        invoices = self.env['account.move'].sudo().search([('move_type', '=', 'out_invoice'),
                                                           ('state', '=', 'posted'),
                                                           ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in invoices:
            res = rec.sudo().action_sale_invoice_sync()
            tally_log_ids += res
            if tally_log_ids:
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'trans_log_line_ids': tally_log_ids
                }
                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'out_invoice'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                self.env['odoo.entries'].sudo().create(odoo_rec)
                _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_stock_uom(self):
        """The unit of measure category model record has been sent to the Tally server."""
        uom = self.env['uom.category'].search([('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in uom:
            res = rec.action_odoo_tally_uom_sync()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'trans_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'uom'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_product_category_sync(self):
        """The product master record has been sent to the Tally server."""
        product_template_ids = self.env['product.template'].sudo().search([
            ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in product_template_ids:
            res = rec.sudo().action_product_category()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'trans_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'products'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_products_group_sync(self):
        """The product category model record has been sent to the Tally server."""
        stock_group_ids = self.env['product.category'].search([('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in stock_group_ids:
            res = rec.sudo().action_odoo_tally_stock_categ_sync()
            tally_log_ids += res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
        if tally_log_ids:
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'trans_log_line_ids': tally_log_ids
            }
            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'prod_categ'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            self.env['odoo.entries'].sudo().create(odoo_rec)
            _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_products_products_sync(self):
        """The product master varient record has been sent to the Tally server."""
        product_ids = self.env['product.product'].search([('ndw_select', '!=', 'done')])
        for rec in product_ids:
            rec.action_odoo_tally_product_sync()

    def button_out_payment_sync(self):
        """The out payemt model record has been sent to the Tally server."""
        bill_payment = self.env['account.move'].sudo().search(
            [('payment_id', '!=', False), ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []
        for rec in bill_payment:
            account_payment = self.env['account.payment'].sudo().search(
                [('payment_type', '=', 'outbound'), ('id', '=', rec.payment_id.id)])
            for recor in self.env['account.move'].sudo().search([
                ('payment_id', '=', account_payment.id)]):
                res = recor.sudo().action_out_payment()
                tally_log_ids += res['tally_log_ids']
                tally_log_xml_data.append(res['tally_log_xml_data'])
                if tally_log_ids:
                    values = {
                        'data_from': 'odoo',
                        'company_id': self.env.company.id,
                        'trans_log_line_ids': tally_log_ids
                    }
                    odoo_rec = {
                        'number_of_odoo_entries': len(tally_log_ids),
                        'odoo_data': str(tally_log_xml_data)[1:-1],
                        'odoo_entry_type': 'out_payment'
                    }
                    tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                    self.env['odoo.entries'].sudo().create(odoo_rec)
                    _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_in_payment_sync(self):
        """The in payment model record has been sent to the Tally server."""
        bill_payment = self.env['account.move'].sudo().search(
            [('payment_id', '!=', False), ('ndw_select', '!=', 'done')])
        tally_log_ids = []
        tally_log_xml_data = []

        for rec in bill_payment:
            account_payment = self.env['account.payment'].sudo().search(
                [('payment_type', '=', 'inbound'), ('id', '=', rec.payment_id.id)])
            for recor in self.env['account.move'].sudo().search([
                ('payment_id', '=', account_payment.id)]):
                res = recor.sudo().action_in_payment()
                tally_log_ids += res['tally_log_ids']
                tally_log_xml_data.append(res['tally_log_xml_data'])
                if tally_log_ids:
                    values = {
                        'data_from': 'odoo',
                        'company_id': self.env.company.id,
                        'trans_log_line_ids': tally_log_ids
                    }
                    odoo_rec = {
                        'number_of_odoo_entries': len(tally_log_ids),
                        'odoo_data': str(tally_log_xml_data)[1:-1],
                        'odoo_entry_type': 'in_payment'
                    }
                    tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                    self.env['odoo.entries'].sudo().create(odoo_rec)
                    _logger.info('@ Log is created: %s', tally_log_obj_id)

    def button_journal_entries(self):
        """The journal entries model record has been sent to the Tally server."""
        print('Journal entry button sync start')
        tally_log_ids = []
        tally_log_xml_data = []

        journals_entry = self.env['account.move'].sudo().search([
    ('state', '=', 'posted'),
    ('ndw_select', '=', 'new'),
    ('move_type', 'in', [
        'entry',         # Journal entries, including payments
        'out_invoice',   # Customer invoice
        'in_invoice',    # Vendor bill
        'out_refund',    # Customer credit note
        'in_refund',     # Vendor credit note
        'out_receipt',   # Customer payment
        'in_receipt'     # Vendor payment
    ])
])
        print('journal list', journals_entry)
        for rec in journals_entry:
            # print('Journal Creation call')
            res = rec.sudo().action_journal_entries()
            # print(res,type(res))
            tally_log_ids = res['tally_log_ids']
            print('log id', tally_log_ids)
            tally_log_xml_data.append(res['tally_log_xml_data'])
            # print('log data', tally_log_xml_data)

            if tally_log_ids:
                print("Log")
                values = {
                    'data_from': 'odoo',
                    'company_id': self.env.company.id,
                    'trans_log_line_ids': tally_log_ids,
                }

                odoo_rec = {
                    'number_of_odoo_entries': len(tally_log_ids),
                    'odoo_data': str(tally_log_xml_data)[1:-1],
                    'odoo_entry_type': 'entry'
                }
                tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
                print("tally_log_obj_id", tally_log_obj_id)
                self.env['odoo.entries'].sudo().create(odoo_rec)

                _logger.info('@ Log is created: %s', tally_log_obj_id)

        journals_entry_alter = self.env['account.move'].sudo().search([
    ('state', '=', 'posted'),
    ('ndw_select', '=', 'write'),
    ('move_type', 'in', [
        'entry',         # Journal entries, including payments
        'out_invoice',   # Customer invoice
        'in_invoice',    # Vendor bill
        'out_refund',    # Customer credit note
        'in_refund',     # Vendor credit note
        'out_receipt',   # Customer payment
        'in_receipt'     # Vendor payment
    ])
])
        # print('jouranl alter list', journals_entry_alter)
        for rec in journals_entry_alter:
            print('Journal Alteration call')
            res = rec.sudo().action_journal_entries_alter()
            print(res,type(res))
            tally_log_ids = res['tally_log_ids']
            tally_log_xml_data.append(res['tally_log_xml_data'])
            print("tally log id", res)

        if tally_log_ids:
            print("Log")
            values = {
                'data_from': 'odoo',
                'company_id': self.env.company.id,
                'trans_log_line_ids':tally_log_ids,
            }

            odoo_rec = {
                'number_of_odoo_entries': len(tally_log_ids),
                'odoo_data': str(tally_log_xml_data)[1:-1],
                'odoo_entry_type': 'entry'
            }
            tally_log_obj_id = self.env['ppts.tally.integration.log'].sudo().create(values)
            print("tally_log_obj_id",tally_log_obj_id)
            self.env['odoo.entries'].sudo().create(odoo_rec)

            _logger.info('@ Log is created: %s', tally_log_obj_id)


    def button_invoices_sync_reset(self):
        """Reset the status of records marked as 'done' for Tally sync."""
        company_id = self.company_id.id
        query = f""" UPDATE account_move SET ndw_select='new'
            WHERE ndw_select = 'done' AND move_type='out_invoice' AND company_id={company_id};"""
        self.env.cr.execute(query)
        return True

    def button_bills_sync_reset(self):
        """Reset the status of records marked as 'done' for Tally sync."""
        company_id = self.company_id.id
        query = f""" UPDATE account_move SET ndw_select='new'
            WHERE ndw_select = 'done' AND move_type='in_invoice' AND company_id={company_id};"""
        self.env.cr.execute(query)
        return True
    @api.model
    def tally_sync_all(self):
        print("123")
        """All records push to the Tally server by one click."""
        tally_obj = self.env['ppts.tally.integration'].search([], limit=1)
        if len(tally_obj) == 1:
            # tally_obj.button_res_account_group()
            self.button_res_account_group_sync()
            tally_obj.button_res_partner_sync()
            (self.button_res_coa_sync())
            tally_obj.button_res_coa_sync_alter()
            # if self.invoices:
            #     tally_obj.button_invoices_sync()
            # if self.bills_new:
            #     tally_obj.button_bills_sync()
            # if self.products_uom:
            #     tally_obj.button_stock_uom()
            # tally_obj.button_product_category_sync()
            # tally_obj.button_products_group_sync()
            # tally_obj.button_products_products_sync()
            # tally_obj.button_out_payment_sync()
            # if self.journals:
            #     tally_obj.button_in_payment_sync()
            if self.journals:
                tally_obj.button_journal_entries()
            # if self.is_sale:
            #     tally_obj.button_sale_order()
            # if self.is_purchase:
            #     tally_obj.button_purchase_order()
            # if self.is_debit:
            #     tally_obj.button_res_debit_note_sync()
            # if self.is_credit:
            #     tally_obj.button_res_cridet_note_sync()
            # if self.is_delivery:
            #     tally_obj.button_res_delivery_note_sync()
            # if self.is_receipt:
            #     tally_obj.button_res_receipt_note_sync()

    def button_res_partner_categ_sync_reset(self):
        """Reset the status of records marked as 'done' for Tally sync."""
        return True

    def button_account_account_sync_reset(self):
        """Reset the status of records marked as 'done' for Tally sync."""
        return True

# class AuditTrialLogs(models.Model):
#     _name = 'audit.trial.logs'
#
#     name = fields.Char('Ref. No')
#     logs = fields.Text('Logs')
#     tally_id = fields.Many2one('ppts.tally.integration')
