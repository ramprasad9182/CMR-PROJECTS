from odoo import api, fields, models, _
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests


class MysqldbConfig(models.Model):
    _name = 'mysqldb.config'
    _description = 'MySQL DB Configuration'
    _rec_name = 'company_name'
    _inherit = ['mail.thread']

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,  # Set default to current company
        required=True)

    db_hostname = fields.Char(string='IP Address of Host', required=True, tracking=True)
    company_name = fields.Char(string='Company Name', required=True, tracking=True)
    db_port = fields.Integer(string='Port', tracking=True)
    db_username = fields.Char(string='Username',tracking=True)
    db_password = fields.Char(string='Password', tracking=True)
    db_sync_type = fields.Selection([('tly2odo', "Tally to Odoo"),('odo2tly', "Odoo to Tally")],
                                    string='Type of Sync', required=True, default="odo2tly")
    # db_OdooCmpName = fields.Char(
    #     string="Odoo Company Name",
    #     compute="_compute_company_name",  # Compute method to auto-update value
    #     store=True,  # Stores in DB and updates when needed
    #     readonly=True  # Prevents manual editing
    # )
    #
    # @api.depends()
    # def _compute_company_name(self):
    #     for rec in self:
    #         rec.db_OdooCmpName = self.env.company.name
            # company_name = record.company_id.name if record.company_id else "No Company Found"
            # record.db_OdooCmpName = company_name
    # db_sync_type = fields.Selection([('tly2odo', "Tally.ERP 9 to Odoo"),('odo2tly', "Odoo to Tally.ERP 9"),
    # ('odotly', "Bi-Directional")],string='Type of Sync',required=True)

    def run_testquery(self):
        url = self.db_hostname
        try:
            response = requests.get(url)
            print('response status code:', response.status_code)
            print('response:', response)

            if response.status_code == 200:
                xml_data = (
                            '<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>CompanyInfo</ID></HEADER><BODY><DESC><STATICVARIABLES /><TDL><TDLMESSAGE><OBJECT NAME="CurrentCompany"><LOCALFORMULA>CurrentCompany:##SVCURRENTCOMPANY</LOCALFORMULA></OBJECT><COLLECTION NAME="CompanyInfo"><OBJECTS>CurrentCompany</OBJECTS></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>')
                print("hiii")
                xml_data = xml_data.replace("&", "&amp;")
                soup = BeautifulSoup(xml_data, "xml")
                pretty_xml = soup.prettify()
                print('pretty_xml:\n', pretty_xml)
                h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
                response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'))
                print('response status code:', response.status_code)
                print('response content:', response.content.decode('utf-8'))
                data = response.content.decode('utf-8')

                # Parse the XML response
                root = ET.fromstring(data)
                server_company_name_element = root.find(".//CURRENTCOMPANY/CURRENTCOMPANY")

                if server_company_name_element is not None:
                    server_company_name = server_company_name_element.text
                    if server_company_name == self.company_name:
                        # return self.env.user.notify_success(message='Connected to Tally Server')
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'success',
                                'message': _('Connected to Tally Server'),
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }


                    else:
                        print("ksbkdbgfvb******")
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'warning',
                                'message': _('Connection issue or Company mismatch'),
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

                        # return self.env.user.notify_warning(message='Connection issue or Company mismatch')
                else:
                    print('Server Company Name element not found in XML response')
                    return self.env.user.notify_warning(message='Connection issue or Company name not found')
        except requests.exceptions.RequestException as e:
            print('Errortytyty:', e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _('IP Address is invalid'),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            # return self.env.user.notify_warning(message='Tally Server Connection lost')
