from odoo import models, fields, api
from psycopg2.sql import SQL
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _inherit = "account.move"

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Tally Update Flag',
                                   default='no_update', copy=False)
    tally_record_id = fields.Char(string="Tally Id")

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        if res and ('ref' in vals or 'narration' in vals):
            self.update_flag = 'update'
        return res


class AccountAccount(models.Model):
    _inherit = "account.account"

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    sequence = fields.Char(
        string="Sequence",
        default='New', readonly=True
    )
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag',
                                   default='no_update', copy=False)
    tally_record_id = fields.Char(string="Tally Id")
    name = fields.Char(string="Account Name", required=True, index='trigram', tracking=True, translate=False)

    @api.constrains('name')
    def _check_unique_account_name(self):
        for rec in self:
            if rec.name:
                trimmed_name = rec.name.strip()
                domain = [('name', 'ilike', trimmed_name), ('id', '!=', rec.id)]
                # domain = [('name', '=', rec.name.strip()),('id', '!=', rec.id)]
                existing = self.search(domain, limit=1)
                if existing:
                    raise ValidationError(f"The account name '{rec.name}' is already in use. It must be unique.")

    def write(self, vals):
        res = super(AccountAccount, self).write(vals)
        if res and ('name' in vals or 'code' in vals or 'group_id' in vals) :
            self.update_flag = 'update'
        return res


    @api.depends_context('company')
    @api.depends('code')
    def _compute_account_group(self):
        accounts_with_code = self.filtered(lambda a: a.code)

        (self - accounts_with_code).group_id = False
        if not accounts_with_code:
            return

        codes = accounts_with_code.mapped('code')
        values_placeholder = ', '.join(['(%s)'] * len(codes))
        params = codes + [self.env.company.root_id.id]

        query = f"""
            SELECT DISTINCT ON (account_code.code)
                   account_code.code,
                   agroup.id AS group_id
              FROM (VALUES {values_placeholder}) AS account_code (code)
         LEFT JOIN account_group agroup
                ON agroup.code_prefix_start <= LEFT(account_code.code, char_length(agroup.code_prefix_start))
                   AND agroup.code_prefix_end >= LEFT(account_code.code, char_length(agroup.code_prefix_end))
                   AND agroup.company_id = %s
          ORDER BY account_code.code, char_length(agroup.code_prefix_start) DESC, agroup.id
        """

        self.env.cr.execute(query, params)
        results = self.env.cr.fetchall()
        group_by_code = dict(results)

        for account in accounts_with_code:
            group_id = group_by_code.get(account.code)
            account.group_id = group_id

            # Auto-assign sequence from group
            if group_id:
                group = self.env['account.group'].browse(group_id)
                if group.sequence and (account.sequence == 'New' or not account.sequence):
                    account.sequence = group.sequence


class AccountGroup(models.Model):
    _inherit = "account.group"

    type = fields.Selection([
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expenditure', 'Expenditure'),
        ('others', 'Others'),
    ], string="Type", required=True)
    # flag_type = fields.Boolean('Flag')
    sequence = fields.Char('Sequence', default='New',readonly= True)

    asset_sub_type = fields.Selection([
        ('receivable', 'Receivable'),
        ('bank_cash', 'Bank & Cash'),
        ('current_assets', 'Current Assets'),
        ('non_current_assets', 'Non Current Assets'),
        ('prepayments', 'Prepayments'),
        ('fixed_assets', 'Fixed Assets'),
    ], string="Sub Type")
    liability_sub_type = fields.Selection([
        ('payable', 'Payable'),
        ('credit_card', 'Credit Card'),
        ('current_liabilities', 'Current Liabilities'),
        ('non_current_liabilities', 'Non Current Liabilities'),
    ], string="Sub Type")
    equity_sub_type = fields.Selection([
        ('equity', 'Equity'),
        ('current_year_earnings', 'Current Year Earnings'),
    ], string="Sub Type")
    revenue_sub_type = fields.Selection([
        ('income', 'Income'),
        ('other_income', 'Other Income'),
    ], string="Sub Type")
    expense_sub_type = fields.Selection([
        ('expenses', 'Expenses'),
        ('depreciation', 'Depreciation'),
        ('cost_of_revenue', 'Cost of Revenue'),
    ], string="Sub Type")
    other_sub_type = fields.Selection([
        ('off_balance', 'Off Balance'),
    ], string="Sub Type")
    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag', default='no_update', copy=False)
    tally_record_id = fields.Char(string="Tally Id")
    name = fields.Char(required=True, translate=False)
    nhcl_parent_id = fields.Many2one('account.group', string="NHCL Parent")

    def action_generate_missing_sequences(self):
        for rec in self:
            if rec.sequence == 'New' and rec.type:
                seq_code = self._sequence_code_map.get(rec.type)
                if seq_code:
                    rec.sequence = self.env['ir.sequence'].next_by_code(seq_code)

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            if rec.name:
                trimmed_name = rec.name.strip()
                # Perform a case-insensitive search using ilike
                domain = [('name', 'ilike', trimmed_name), ('id', '!=', rec.id)]
                existing = self.search(domain)
                if existing:
                    raise ValidationError(f"The account group name '{rec.name}' is already in use. It must be unique.")

    def write(self,vals):
        res = super(AccountGroup, self).write(vals)
        if res and 'name' in vals:
            self.update_flag = 'update'
        if 'code_prefix_start' in vals or 'code_prefix_end' in vals:
            for group in self:
                domain = [
                    ('code', '>=', group.code_prefix_start),
                    ('code', '<=', group.code_prefix_end),
                    ('company_ids', '=', group.company_id.id),
                ]
                accounts = self.env['account.account'].search(domain)
                accounts._compute_account_group()
        return res


    _sequence_code_map = {
        'asset': 'account.group.asset',
        'liability': 'account.group.liability',
        'equity': 'account.group.equity',
        'revenue': 'account.group.revenue',
        'expenditure': 'account.group.expenditure',
        'others': 'account.group.others',
    }

    @api.model
    def create(self, vals):
        if vals.get('sequence', 'New') == 'New' and vals.get('type'):
            type_code = vals['type']
            seq_code = self._sequence_code_map.get(type_code)
            if seq_code:
                vals['sequence'] = self.env['ir.sequence'].next_by_code(seq_code)
        return super(AccountGroup, self).create(vals)


class ResPartner(models.Model):
    _inherit = "res.partner"

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag',
                                   default='no_update', copy=False)
    contact_sequence = fields.Char(string="Sequence", default=lambda self: 'New')
    tally_record_id = fields.Char(string="Tally Id")
    partner_type = fields.Selection([('customer', 'Customer'), ('supplier', 'Supplier'),('others', 'Others')],
                                    string='Partner Type', copy=False, required=True)
    _sequence_code_map = {
        'customer': 'res.partner.customer',
        'supplier': 'res.partner.supplier',
        'others': 'res.partner.others',
    }

    @api.model
    def create(self, vals):
        if vals.get('contact_sequence', 'New') == 'New' and vals.get('partner_type'):
            partner_type_code = vals['partner_type']
            seq_code = self._sequence_code_map.get(partner_type_code)
            if seq_code:
                vals['contact_sequence'] = self.env['ir.sequence'].next_by_code(seq_code)
            # vals['contact_sequence'] = self.env['ir.sequence'].next_by_code('res.partner.contact')
        return super(ResPartner, self).create(vals)

    # @api.model
    # def create(self, vals):
    #     if vals.get('contact_sequence', 'New') == 'New' and vals.get('partner_type'):
    #         partner_type_code = vals['partner_type']
    #         seq_code = self._sequence_code_map.get(partner_type_code)
    #         if seq_code:
    #             sequence = self.env['ir.sequence'].next_by_code(seq_code)
    #             vals['contact_sequence'] = sequence
    #
    #             # Add sequence to name
    #             name = vals.get('name', '')
    #             vals['name'] = f"{name}-{sequence}" if name else sequence
    #
    #     return super(ResPartner, self).create(vals)

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if res and ('name' in vals or 'property_supplier_payment_term_id' in vals or 'comment' in vals):
            self.update_flag = 'update'
        return res

    # @api.constrains('name','vat')
    # def _check_customer_name(self):
    #     for rec in self:
    #         print("customer")
    #         if rec.customer_rank <= 0:
    #             continue  # Only CUSTOMER
    #
    #         name_clean = (rec.name or '').strip().lower()
    #         vat_clean = (rec.vat or '').strip().lower()
    #
    #         customers = self.env['res.partner'].search([
    #             ('id', '!=', rec.id),
    #             ('customer_rank', '>', 0),
    #         ])
    #
    #         # 1. VAT must be unique if present
    #         if vat_clean:
    #             for customer in customers:
    #                 customer_vat = (customer.vat or '').strip().lower()
    #                 if customer_vat == vat_clean:
    #                     raise ValidationError("A customer with the same GST already exists.")
    #
    #         # 2. If VAT is empty, disallow if any customer exists with same name and any VAT (empty or not)
    #         if not vat_clean:
    #             for customer in customers:
    #                 customer_name = (customer.name or '').strip().lower()
    #                 if customer_name == name_clean:
    #                     raise ValidationError("A customer with the same name already exists with or without GST.")

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals, force_balance)

        payment_name = res[0].get('name') or ''
        payment_ref = self.memo or ''

        vendor_bill = False

        # First, try to extract from payment name if it contains "BILL/"
        # if "BILL/" in payment_name:
        #     bill_name = payment_name.split("BILL/")[-1].strip()
        #     full_bill_name = f"BILL/{bill_name}"
        #
        #     vendor_bill = self.env['account.move'].search([
        #         ('name', '=', full_bill_name),
        #         ('move_type', '=', 'in_invoice')
        #     ])
        if "BILL/" in payment_ref or "INV/" in payment_ref:
            vendor_bill = self.env['account.move'].search([
                ('name', '=', payment_ref)
            ])

        # If not found by name, fallback to ref (memo)
        if not vendor_bill and payment_ref:
            vendor_bill = self.env['account.move'].search([
                ('ref', '=', payment_ref)
            ])

        if not vendor_bill:
            return res  # No vendor bill found

        # Get analytic distribution from bill lines
        analytic_distribution = {}
        for line in vendor_bill.line_ids:
            if line.analytic_distribution:
                analytic_distribution = line.analytic_distribution
                break  # Use the first found

        if not analytic_distribution:
            return res  # No analytic info found

        # Apply analytic_distribution to debit lines
        for line in res:
            if line.get('debit', 0.0) >= 0:
                line['analytic_distribution'] = analytic_distribution

        return res

class Company(models.Model):
    _inherit = 'res.company'

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag',
                                   default='no_update', copy=False)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag',
                                   default='no_update', copy=False)

class Location(models.Model):
    _inherit = "stock.location"

    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Update Flag',
                                   default='no_update', copy=False)