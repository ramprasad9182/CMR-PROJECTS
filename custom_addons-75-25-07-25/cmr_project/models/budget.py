from odoo import fields, models, api, _


class BudgetAnalytic(models.Model):
    _inherit = "budget.analytic"
    _description = "Budget"

    nhcl_user_id = fields.Many2one('res.users', string="Manager", related="user_id.employee_parent_id.user_id")

    # def revise_the_budget(self):
    #     for rec in self.budget_line_ids:
    #         rec.write({'previous_planned_amount' : rec.planned_amount})
    #     self.write({'state': 'draft'})
    #
    # def action_budget_cancel(self):
    #     for rec in self.budget_line_ids:
    #         rec.write({'planned_amount': rec.previous_planned_amount})
    #     self.write({'state': 'cancel'})
    #
    # def send_msg_to_user(self, user_ids, author_id, body, name):
    #     """Send a message to users."""
    #     # Search for the existing channel, using the mail thread model
    #     mail_channel = self.env['discuss.channel'].search(
    #         [('name', '=', name), ('channel_partner_ids', 'in', user_ids)], limit=1)
    #
    #     if not mail_channel:
    #         # If no existing channel is found, create a new one
    #         mail_channel = self.env['discuss.channel'].create({
    #             'name': name,
    #             'channel_partner_ids': [(4, user_id) for user_id in user_ids],
    #             'channel_type': 'group',  # 'group' for discussion-based channel
    #         })
    #
    #     # Post the message in the channel using the mail.thread model
    #     mail_channel.message_post(
    #         author_id=author_id,
    #         body=body,
    #         message_type='comment',
    #         subtype_xmlid='mail.mt_comment'
    #     )
    #
    # def create_revised_budget(self):
    #     """Create a revised budget record and send notification to the assigned user."""
    #     for record in self:
    #         # Create the revised budget record
    #         self.env['nhcl.revised.budgets'].create({
    #             'project_name': record.name,  # Assuming 'name' field is the project name in crossovered.budget
    #             'planned_amount_revised': sum(line.planned_amount for line in record.budget_line_ids),
    #             'approver': record.nhcl_user_id.id,
    #         })
    #
    #         # Check if nhcl_user_id is set
    #         if not record.nhcl_user_id:
    #             raise ValidationError(_("You must assign a user before creating the revised budget."))
    #         # Prepare the message body
    #         body = _("The revised budget for project '%s' is waiting for your approval.") % (record.name)
    #         # Prepare the partner ID of the assigned user (from nhcl_user_id)
    #         partner_id = record.nhcl_user_id.partner_id.id
    #         # Send the notification to the assigned user
    #         self.send_msg_to_user([partner_id], self.env.user.partner_id.id, body, "Revised Budget")


class BudgetLine(models.Model):
    _inherit = 'budget.line'
    _description = "Budget Line"

    previous_planned_amount = fields.Monetary('Previous Planned Amount')


# class Nhclrevisedbudget(models.Model):
#     _name = "nhcl.revised.budgets"
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#
#     state = fields.Selection([('draft', 'Draft'),('approved', 'Approved'), ('cancel','Cancel')],
#                              string='State', default='draft', tracking=True)
#     project_name = fields.Char('Project Name', tracking=True)
#     planned_amount_revised = fields.Float('Initial Budget Amount', tracking=True)
#     nhcl_planned_amount_revised = fields.Float('Revised Budget Amount', default=0.0, tracking=True)
#     approver = fields.Many2one('res.users', string="Approver")
#
#     def reset_to_draft(self):
#         self.write({'state':'draft'})
#
#     def cancel_revised(self):
#         self.write({'state': 'cancel'})
#
#     def approve_revised_amount(self):
#         """Approve the revised budget and update the planned_amount in the related budget lines."""
#         for record in self:
#             # Find the corresponding crossovered.budget.line based on project_name
#             crossovered_budget_lines = self.env['budget.line'].search([('name', '=', record.project_name)])
#             # If there are related budget lines, update their planned_amount
#             if crossovered_budget_lines:
#                 crossovered_budget_lines.write({'planned_amount': record.nhcl_planned_amount_revised})
#
#             # Update the state of the nhcl.revised.budgets record to 'approved'
#             record.write({'state': 'approved'})
