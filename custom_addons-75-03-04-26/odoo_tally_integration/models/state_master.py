from odoo import models, fields, api

class StateMaster(models.Model):
    _name = "state.master"
    _rec_name = 'state_id'

    # country_id = fields.Many2one(comodel_name='res.country', string='Country', required=True)
    state_id = fields.Many2one(comodel_name='res.country.state', string='State',
                               domain=[('country_id.code', '=', 'IN')])
    company_name = fields.Char(string="Tally Company Name")
    tally_company_code = fields.Char(string="Tally Company Code")




class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    acc_state_id = fields.Many2one(comodel_name='state.master', string='State')
    nhcl_company_name = fields.Char(string="Tally Company")
    nhcl_tally_flag = fields.Selection([('n', 'N'), ('y', 'Y')], string='Flag', default='n', copy=False)
    update_flag = fields.Selection([('no_update', 'No Update'), ('update', 'Update')], string='Tally Update Flag',
                                   default='no_update', copy=False)
    tally_record_id = fields.Char(string="Tally Id")

    # name = fields.Char(
    #     string='Analytic Account',
    #     index='trigram',
    #     required=True,
    #     tracking=True,
    #     translate=False,
    # )


    @api.onchange('acc_state_id')
    def _onchange_acc_state_id(self):
        for record in self:
            if record.acc_state_id:
                record.nhcl_company_name = record.acc_state_id.company_name
            else:
                record.nhcl_company_name = False




