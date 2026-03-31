from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import format_amount, format_date, format_list, formatLang, groupby


class Project(models.Model):
    _inherit = "project.project"

    receipt_type_id = fields.Many2one('stock.picking.type', string='Receipt Operation Type')
    delivery_type_id = fields.Many2one('stock.picking.type', string='Delivery Operation Type')
    internal_type_id = fields.Many2one('stock.picking.type', string='Internal Transfer Type')
    manufacturing_type_id = fields.Many2one('stock.picking.type', string='Manufacturing Type')
    repair_type_id = fields.Many2one('stock.picking.type', string='Repair Type')
    is_stock_setup_missing = fields.Boolean(string="Stock Setup Missing", compute="_compute_is_stock_setup_missing")

    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street 2")
    city = fields.Char(string="City")
    state_id = fields.Many2one('res.country.state', string="State", domain="[('country_id', '=?', country_id)]")
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

    @api.constrains('street', 'city', 'state_id', 'zip', 'country_id', 'l10n_in_gst_treatment', 'l10n_in_gstin', 'pan')
    def _check_required_fields(self):
        for rec in self:
            missing_fields = []
            if not rec.street:
                missing_fields.append("Street")
            if not rec.city:
                missing_fields.append("City")
            if not rec.state_id:
                missing_fields.append("State")
            if not rec.zip:
                missing_fields.append("ZIP")
            if not rec.country_id:
                missing_fields.append("Country")
            if not rec.l10n_in_gst_treatment:
                missing_fields.append("GST Treatment")
            if not rec.l10n_in_gstin:
                missing_fields.append("GSTIN")
            if not rec.pan:
                missing_fields.append("PAN")

            if missing_fields:
                raise ValidationError(
                    f"The following fields are required: {', '.join(missing_fields)}"
                )

    @api.onchange('l10n_in_gstin')
    def _onchange_gstin(self):
        """Auto-fill PAN, State, Country, GST Treatment based on GSTIN"""
        if self.l10n_in_gstin:
            gstin = self.l10n_in_gstin.strip().upper()

            # Auto PAN from GSTIN
            if len(gstin) == 15:
                self.pan = gstin[2:12]  # GSTIN contains PAN in positions 3-12

                # First 2 digits = State code
                state_code = gstin[:2]
                state = self.env['res.country.state'].search([
                    ('l10n_in_tin', '=', state_code)
                ], limit=1)

                if state:
                    self.state_id = state.id
                    self.country_id = state.country_id.id

                # GST Treatment default
                self.l10n_in_gst_treatment = 'regular'

    @api.onchange('state_id')
    def _onchange_state_id(self):
        """Auto-fill country based on selected state"""
        if self.state_id:
            self.country_id = self.state_id.country_id.id
        else:
            self.country_id = False

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if len(res.tag_ids) > 1:
            raise ValidationError("You can select only one value for Tags.")
        res.action_generate_stock_setup()  # Auto-generate stock setup on project creation
        return res

    def write(self, vals):
        res = super(Project, self).write(vals)

        # For all updated projects, update corresponding stock.location
        for project in self:
            # Find stock.location(s) with name matching project name
            locations = self.env['stock.location'].sudo().search(
                [('name', '=', project.name), ('usage', '=', 'internal')])
            for loc in locations:
                loc.write({
                    'street': project.street or '',
                    'street2': project.street2 or '',
                    'city': project.city or '',
                    'state_id': project.state_id.id or False,
                    'zip': project.zip or '',
                    'country_id': project.country_id.id or False,
                    'pan': project.pan or '',
                    'l10n_in_gstin': project.l10n_in_gstin or '',
                    'l10n_in_gst_treatment': project.l10n_in_gst_treatment or False,
                })
        return res

    @api.depends('receipt_type_id', 'delivery_type_id', 'internal_type_id', 'manufacturing_type_id', 'repair_type_id',
                 'name')
    def _compute_is_stock_setup_missing(self):
        for rec in self:
            location_exists = self.env['stock.location'].sudo().search_count([
                ('name', '=', rec.name),
                ('usage', '=', 'internal')
            ]) > 0

            rec.is_stock_setup_missing = not all([
                rec.receipt_type_id,
                rec.delivery_type_id,
                rec.internal_type_id,
                rec.manufacturing_type_id,
                rec.repair_type_id,
                location_exists,
            ])

    def action_generate_stock_setup(self):
        for rec in self:
            location_exists = self.env['stock.location'].sudo().search_count([
                ('name', '=', rec.name),
                ('usage', '=', 'internal')
            ]) > 0

            if all([
                rec.receipt_type_id,
                rec.delivery_type_id,
                rec.internal_type_id,
                rec.manufacturing_type_id,
                rec.repair_type_id,
                location_exists,
            ]):
                raise ValidationError("Stock setup already exists for this project.")

            location = self.env['stock.location'].sudo().search([
                ('name', '=', rec.name),
                ('usage', '=', 'internal')
            ], limit=1)
            if not location:
                location = self.env['stock.location'].sudo().create({
                    'name': rec.name,
                    'usage': 'internal',
                    'street': rec.street,
                    'street2': rec.street2,
                    'city': rec.city,
                    'state_id': rec.state_id.id,
                    'zip': rec.zip,
                    'country_id': rec.country_id.id,
                    'l10n_in_gst_treatment': rec.l10n_in_gst_treatment,
                    'l10n_in_gstin': rec.l10n_in_gstin,
                    'pan': rec.pan,
                })

            def _create_sequence(name, code):
                return self.env['ir.sequence'].create({
                    'name': name,
                    'code': code,
                    'prefix': code.upper() + '/',
                    'padding': 4,
                    'number_next': 1,
                })

            picking_obj = self.env['stock.picking.type']
            name_clean = rec.name.lower().replace(" ", "_")

            if not rec.receipt_type_id:
                rec.receipt_type_id = picking_obj.create({
                    'name': f'{rec.name}: Receipts',
                    'code': 'incoming',
                    'sequence_code': f'{name_clean}_incoming',
                    'default_location_src_id': self.env.ref('stock.stock_location_suppliers').id,
                    'default_location_dest_id': location.id,
                    'sequence_id': _create_sequence(f'{rec.name} Incoming', f'{name_clean}_incoming').id,
                })

            if not rec.delivery_type_id:
                rec.delivery_type_id = picking_obj.create({
                    'name': f'{rec.name}: Delivery',
                    'code': 'outgoing',
                    'sequence_code': f'{name_clean}_outgoing',
                    'default_location_src_id': location.id,
                    'default_location_dest_id': self.env.ref('stock.stock_location_customers').id,
                    'sequence_id': _create_sequence(f'{rec.name} Outgoing', f'{name_clean}_outgoing').id,
                })

            if not rec.internal_type_id:
                rec.internal_type_id = picking_obj.create({
                    'name': f'{rec.name}: Internal Transfer',
                    'code': 'internal',
                    'sequence_code': f'{name_clean}_internal',
                    'default_location_src_id': location.id,
                    'default_location_dest_id': location.id,
                    'sequence_id': _create_sequence(f'{rec.name} Internal', f'{name_clean}_internal').id,
                })

            if not rec.manufacturing_type_id:
                rec.manufacturing_type_id = picking_obj.create({
                    'name': f'{rec.name}: Manufacturing',
                    'code': 'mrp_operation',
                    'sequence_code': f'{name_clean}_manufacturing',
                    'default_location_src_id': location.id,
                    'default_location_dest_id': location.id,
                    'sequence_id': _create_sequence(f'{rec.name} Manufacturing', f'{name_clean}_manufacturing').id,
                })

            if not rec.repair_type_id:
                rec.repair_type_id = picking_obj.create({
                    'name': f'{rec.name}: Repairs',
                    'code': 'repair_operation',
                    'sequence_code': f'{name_clean}_repairs',
                    'default_location_src_id': location.id,
                    'default_location_dest_id': location.id,
                    'sequence_id': _create_sequence(f'{rec.name} Repairs', f'{name_clean}_repairs').id,
                })

    # @api.model
    # def create(self, vals_list):
    #     res = super(Project, self).create(vals_list)
    #     if len(self.tag_ids) > 1:
    #         raise ValidationError("You can select, only one value for Tags")
    #     return res

    # @api.onchange('project_estimate_value', 'task_ids')
    # def _check_project_estimate_value(self):
    #     for project in self:
    #         if project.task_ids:
    #             total_task_estimate = sum(project.task_ids.mapped('nhcl_estimate_value'))
    #             if project.project_estimate_value < total_task_estimate:
    #                 raise ValidationError(
    #                     "The project's estimated value is less than the total estimated value of its tasks. "
    #                     "Please adjust the project's estimated value.")


class Task(models.Model):
    _inherit = "project.task"

    nhcl_estimate_qty = fields.Float(string="Estimate Qty", tracking=True)
    nhcl_estimate_value = fields.Float(string="Estimate Value", tracking=True)
    nhcl_product_id = fields.Many2one('product.product', string='Product')
    nhcl_project_product_ids = fields.One2many('nhcl.project.product', 'nhcl_task_id')


    def open_multi_product_wizard(self):
        return {
            'name': 'Select Products',
            'type': 'ir.actions.act_window',
            'res_model': 'nhcl.multi.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_select_products(self):
        return {
            'name': 'Select Products',
            'type': 'ir.actions.act_window',
            'res_model': 'project.product.select.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
            }
        }


    @api.onchange('nhcl_project_product_ids')
    def _onchange_nhcl_project_product_ids(self):
        if not self.nhcl_project_product_ids:
            return

        unique = self.env['nhcl.project.product']
        seen = set()
        duplicate_found = False
        duplicate_name = ""

        for line in self.nhcl_project_product_ids:
            attr_id = line.nhcl_product_id.id
            attr_name = line.nhcl_product_id.name

            # duplicate attribute found
            if attr_id in seen:
                duplicate_found = True
                duplicate_name = attr_name
                continue

            seen.add(attr_id)
            unique += line

        # Keep only unique lines
        self.nhcl_project_product_ids = unique

        # If duplicate was added → show warning message
        if duplicate_found:
            return {
                'warning': {
                    'title': "Duplicate Attribute",
                    'message': f"The product '{duplicate_name}' is already added. Duplicate entries are not allowed."
                }
            }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'user_ids' in fields_list:
            user = self.env.uid
            manager_user = self.env['hr.employee'].search([
                ('user_id', '=', user)
            ], limit=1).parent_id.user_id.id or False
            res['user_ids'] = [(6, 0, [user, manager_user])] if manager_user else [(6, 0, [user])]
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        # Let Odoo behave normally if context requests to skip filtering
        if self.env.context.get('skip_group_expand'):
            return stages

        # ✅ If user is in group → use Odoo’s default (no filtering)
        if self.env.user.has_group('cmr_project.group_see_all_stages'):
            return super()._read_group_stage_ids(stages, domain)

        # ❌ Otherwise → only show stages that have tasks
        task_domain = domain + [('stage_id', 'in', stages.ids)]
        grouped_stages = self.with_context(skip_group_expand=True).read_group(
            task_domain, ['stage_id'], ['stage_id']
        )

        stage_ids_with_tasks = [group['stage_id'][0] for group in grouped_stages if group.get('stage_id')]
        if not stage_ids_with_tasks:
            return stages.browse([])

        return stages.browse(stage_ids_with_tasks).sorted(key=lambda r: r.sequence)
    # stages visible when the tasks are available otherwise not
    # @api.model
    # def _read_group_stage_ids(self, stages, domain):
    #     if self.env.context.get('skip_group_expand'):
    #         return stages
    #
    #     # Find stages that have tasks
    #     task_domain = domain + [('stage_id', 'in', stages.ids)]
    #     grouped_stages = self.with_context(skip_group_expand=True).read_group(
    #         task_domain, ['stage_id'], ['stage_id']
    #     )
    #     stage_ids_with_tasks = [group['stage_id'][0] for group in grouped_stages if group.get('stage_id')]
    #
    #     # If no stages have tasks, return empty
    #     if not stage_ids_with_tasks:
    #         return stages.browse([])
    #
    #     # Base domain to restrict only to stages with tasks
    #     search_domain = [('id', 'in', stage_ids_with_tasks)]
    #
    #     # If fallback conditions apply, add restriction but using AND (&)
    #     if (
    #             'default_project_id' in self.env.context and
    #             not self.env.context.get('subtask_action') and
    #             'project_kanban' in self.env.context
    #     ):
    #         search_domain = ['&', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain
    #
    #     final_stage_ids = stages.sudo()._search(search_domain, order=stages._order)
    #
    #     return stages.browse(final_stage_ids).sorted(key=lambda r: r.sequence)

    ###############################################################
    @api.constrains('name', 'project_id')
    def _check_unique_task_name_in_project(self):
        for task in self:
            normalized_name = task.name.strip().lower()
            duplicate = self.env['project.task'].search([
                ('id', '!=', task.id),
                ('project_id', '=', task.project_id.id)
            ])
            for other_task in duplicate:
                if other_task.name.strip().lower() == normalized_name:
                    raise ValidationError("Task name must be unique (case-insensitive) within the same project.")

    ######################################################################################

    def _check_estimated_values(self):
        """ Validate estimated values for subtasks and project budget """
        for task in self:
            # Validation for subtasks
            if task.parent_id and task.parent_id.nhcl_project_product_ids:
                task_parent_estimate_value = sum(
                    task.parent_id.nhcl_project_product_ids.mapped('nhcl_product_estimate_value'))
                total_subtask_estimate = sum(
                    task.parent_id.child_ids.mapped('nhcl_project_product_ids.nhcl_product_estimate_value'))
                if total_subtask_estimate > task_parent_estimate_value:
                    raise ValidationError(
                        "The total estimated value of subtasks exceeds the parent task's estimated value. "
                        "Please adjust the parent task's estimated value."
                    )
            # Validation for project and tasks
            if task.project_id and task.project_id.total_budget_amount:
                total_task_estimate = sum(
                    task.project_id.task_ids.mapped('nhcl_project_product_ids.nhcl_product_estimate_value'))
                if total_task_estimate > task.project_id.total_budget_amount:
                    raise ValidationError(
                        "The total estimated value of tasks exceeds the project's estimated value. "
                        "Please adjust the project's estimated value."
                    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super(Task, self).create(vals_list)
        for record in res:
            if record.project_id:
                record.tag_ids = [(6, 0, record.project_id.tag_ids.ids)]
        self._check_estimated_values()
        return res

    def write(self, vals):
        res = super(Task, self).write(vals)
        if len(self.tag_ids) > 1:
            raise ValidationError("You can select, only one value for Project Type")
        self._check_estimated_values()
        return res




class ProjectProduct(models.Model):
    _name = 'nhcl.project.product'

    nhcl_product_id = fields.Many2one('product.product', string="Product", copy=False)
    nhcl_product_categ_id = fields.Many2one('product.category', string="Product Category", copy=False,
                                            related='nhcl_product_id.categ_id', store=True)
    nhcl_product_estimate_qty = fields.Float(string="Estimate Qty", copy=False, digits=(16, 3),)
    nhcl_product_estimate_value = fields.Float(string="Estimate Value", tracking=True)
    nhcl_product_dummy_qty = fields.Float(string="D.Actual Qty", tracking=True, compute='_compute_actuals',store=True)
    nhcl_product_dummy_value = fields.Float(string="D.Actual Value", tracking=True, compute='_compute_actuals', store=True)
    nhcl_product_actual_qty = fields.Float(string="Actual Qty", tracking=True, copy=False,compute='_compute_actuals',store=True, digits=(16, 3),)
    nhcl_product_actual_value = fields.Float(string="Actual Value", tracking=True, copy=False,compute='_compute_actuals',store=True)
    nhcl_product_balance_qty = fields.Float(string="Balance Qty", tracking=True, copy=False,
                                            compute='nhcl_get_balance_qty')
    nhcl_product_balance_value = fields.Float(string="Balance Value", tracking=True, copy=False,
                                              compute='nhcl_get_balance_value')
    nhcl_task_id = fields.Many2one('project.task', string="Task")
    nhcl_project_id = fields.Many2one('project.project', string="Project", related='nhcl_task_id.project_id',
                                      store=True)
    nhcl_task_stage_id = fields.Many2one('project.task.type', string="Stage", related='nhcl_task_id.stage_id',
                                         store=True)
    nhcl_product_account_id = fields.Many2one('account.analytic.account', string="Account", copy=False,
                                              related='nhcl_task_id.project_id.account_id', store=True)

    s_no = fields.Integer(string="S.No", compute="_compute_s_no")

    @api.depends('nhcl_task_id', 'nhcl_task_id.nhcl_project_product_ids')
    def _compute_s_no(self):
        for rec in self:
            task = rec.nhcl_task_id
            if not task:
                rec.s_no = 1
                continue

            # No sorting with id → break NewId issue
            lines = task.nhcl_project_product_ids

            # Assign serial number according to natural order
            for idx, line in enumerate(lines, start=1):
                if line == rec:
                    rec.s_no = idx
                    break


    # @api.constrains('nhcl_product_id', 'nhcl_task_id')
    # def _check_duplicate_variant(self):
    #     """Disallow exact variant duplicates (same product.product) in a task."""
    #     for rec in self:
    #         if rec.nhcl_task_id:
    #             product_ids = []
    #             duplicate_names = []
    #
    #             # Loop through all lines of the task
    #             for line in rec.nhcl_task_id.nhcl_project_product_ids:
    #                 if line.id != rec.id and line.nhcl_product_id:
    #                     prod_id = line.nhcl_product_id.id
    #                     if prod_id in product_ids:
    #                         duplicate_names.append(line.nhcl_product_id.display_name)
    #                     else:
    #                         product_ids.append(prod_id)
    #
    #             # Also check current record's product
    #             if rec.nhcl_product_id and rec.nhcl_product_id.id in product_ids:
    #                 duplicate_names.append(rec.nhcl_product_id.display_name)
    #
    #             # If any duplicates found, raise error
    #             if duplicate_names:
    #                 names = ", ".join(set(duplicate_names))
    #                 raise ValidationError(
    #                     f"The following product variant(s) are added multiple times: {names}. Please select different products."
    #                 )

    def nhcl_get_bills(self):
        return {
            'name': _('Detail Operation'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('account.view_move_line_tree').id,
            'domain': [('product_id', '=', self.nhcl_product_id.id),
                       ('analytic_line_ids.auto_account_id', '=', self.nhcl_product_account_id.id)]
        }

    def nhcl_get_balance_qty(self):
        for rec in self:
            rec.nhcl_product_balance_qty = rec.nhcl_product_estimate_qty - rec.nhcl_product_actual_qty

    def nhcl_get_balance_value(self):
        for rec in self:
            rec.nhcl_product_balance_value = rec.nhcl_product_estimate_value - rec.nhcl_product_actual_value

    # @api.depends('nhcl_task_id.project_id','nhcl_task_id', 'nhcl_project_id')
    # def _compute_actuals(self):
    #     for task in self:
    #         if task.nhcl_product_account_id:
    #             purchase_line = self.env['purchase.order.line'].search([
    #                 ('product_id', '=', task.nhcl_product_id.id),
    #                 ('order_id.state', 'in', ['purchase','done'] )
    #             ])
    #
    #             # print('found data',purchase_line,"///",purchase_line.filtered(lambda line: task.nhcl_product_account_id in line.purchase_many[0]))
    #             filtered_lines = purchase_line.filtered(
    #                 #     lambda line: line.analytic_distribution and
    #                 #                  task.nhcl_product_account_id.id == (line._get_analytic_account_ids() or [None])[0]
    #                 # )
    #                 lambda line: line.analytic_distribution and
    #                              task.nhcl_product_account_id in [r for r in line.purchase_project_ids])
    #
    #
    #             if not filtered_lines:
    #
    #                 # No valid move lines found
    #                 task.nhcl_product_dummy_qty = 0.0
    #                 task.nhcl_product_actual_qty = 0.0
    #                 task.nhcl_product_dummy_value = 0.0
    #                 task.nhcl_product_actual_value = 0.0
    #             else:
    #                 task.nhcl_product_dummy_qty = sum(filtered_lines.mapped('product_qty'))
    #                 task.nhcl_product_actual_qty = sum(filtered_lines.mapped('product_qty'))
    #                 task.nhcl_product_dummy_value = sum(filtered_lines.mapped('price_subtotal'))
    #                 task.nhcl_product_actual_value = sum(filtered_lines.mapped('price_subtotal'))
    #         else:
    #             task.nhcl_product_dummy_qty = 0.0
    #             task.nhcl_product_actual_qty = 0.0
    #             task.nhcl_product_dummy_value = 0.0
    #             task.nhcl_product_actual_value = 0.0
    @api.depends('nhcl_task_id.project_id', 'nhcl_task_id', 'nhcl_project_id', 'nhcl_task_id.child_ids')
    def _compute_actuals(self):
        for task in self:
            if task.nhcl_product_account_id:

                domain = [
                    ('product_id', '=', task.nhcl_product_id.id),
                    ('order_id.state', 'in', ['purchase', 'done']),
                    '|',
                    ('nhcl_task_id', '=', task.nhcl_task_id.id),
                    ('nhcl_sub_task_id', '=', task.nhcl_task_id.id)
                ]
                purchase_line = self.env['purchase.order.line'].search(domain)

                filtered_lines = purchase_line.filtered(
                    lambda line: line.analytic_distribution and
                                 task.nhcl_product_account_id in [r for r in line.purchase_project_ids])
                if not filtered_lines:
                    task.nhcl_product_dummy_qty = 0.0
                    task.nhcl_product_actual_qty = 0.0
                    task.nhcl_product_dummy_value = 0.0
                    task.nhcl_product_actual_value = 0.0
                else:
                    task.nhcl_product_dummy_qty = sum(filtered_lines.mapped('product_qty'))
                    task.nhcl_product_actual_qty = sum(filtered_lines.mapped('product_qty'))
                    task.nhcl_product_dummy_value = sum(filtered_lines.mapped('price_subtotal'))
                    task.nhcl_product_actual_value = sum(filtered_lines.mapped('price_subtotal'))
            else:
                task.nhcl_product_dummy_qty = 0.0
                task.nhcl_product_actual_qty = 0.0
                task.nhcl_product_dummy_value = 0.0
                task.nhcl_product_actual_value = 0.0


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(ProjectProduct, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                     orderby=orderby,
                                                     lazy=lazy)
        if 'nhcl_product_estimate_value' in fields:
            for line in res:
                if '__domain' in line:
                    lines = self.search(line['__domain'])
                    for record in line:
                        if record == 'nhcl_project_id':
                            project = self.env['project.project'].search([('id', '=', line['nhcl_project_id'][0])])
                            line['nhcl_product_estimate_value'] = project.total_planned_amount

        return res
