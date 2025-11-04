"""Odoo16 Module: Product Master"""
from odoo import models, api
import requests
from bs4 import BeautifulSoup


class ProductTallySync(models.Model):
    """This model extends the default functionality of 'account.move' in Odoo16,
    providing additional methods to synchronize out payment with an external system
    using XML requests, specifically tailored for integration with Tally ERP."""
    _inherit = 'product.product'

    @api.onchange('write_date')
    def _onchange_write_date_ndw_select(self):
        if self.tally_flag:
            self.ndw_select = 'write'

    def action_odoo_tally_product_sync(self):
        """This method constructs an XML request to synchronize Credit Note
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the out payment and sends the data to the specified URL."""
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        # if self.detailed_type == 'service':
        #     product_type = 'Service'
        # else:
        #     product_type = 'Goods'
        product_name = self.name
        xml = '<ENVELOPE>\
              <HEADER>\
              <TALLYREQUEST>Import Data</TALLYREQUEST>\
              </HEADER>\
              <BODY>\
              <IMPORTDATA>\
              <REQUESTDESC>\
              <REPORTNAME>All Masters</REPORTNAME>\
              <STATICVARIABLES>\
              <SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\
              </STATICVARIABLES>\
              </REQUESTDESC>\
              <REQUESTDATA>\
              <TALLYMESSAGE xmlns:UDF="TallyUDF">\
              <STOCKITEM NAME="" RESERVEDNAME="">\
              <PARENT>%s</PARENT>\
              <NAME>%s</NAME>\
              <BASEUNITS>%s</BASEUNITS>\
              <OPENINGBALANCE></OPENINGBALANCE>\
              <OPENINGVALUE></OPENINGVALUE>\
              <OPENINGRATE> </OPENINGRATE>\
              </STOCKITEM>\
              </TALLYMESSAGE>\
              </ENVELOPE>' % (company, self.product_tmpl_id.name,
                              product_name, self.uom_id.name)

        xml_data = xml.replace("&", "amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        self.ndw_select = 'done'
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
        except requests.exceptions.RequestException as e:
            print(e, 'eee-----------')
        if response:
            soup_2 = BeautifulSoup(response.text, 'xml')
            if '<LINEERROR>' in str(response.text):
                print(str(soup_2.LINEERROR.get_text()), "sssss")
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
