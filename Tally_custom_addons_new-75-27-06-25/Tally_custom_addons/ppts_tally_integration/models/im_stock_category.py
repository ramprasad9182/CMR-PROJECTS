"""Odoo16 Module: Product Master"""
import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import api, fields, models
import requests
from bs4 import BeautifulSoup


class ProductCategory(models.Model):
    """This model extends the default functionality of 'product.template' in Odoo16,
    providing additional methods to synchronize out payment with an external system
    using XML requests, specifically tailored for integration with Tally ERP."""
    _inherit = "product.template"

    @api.onchange('write_date')
    def _onchange_write_date_ndw_select(self):
        if self.tally_flag:
            self.ndw_select = 'write'

    def action_product_category(self):
        """This method constructs an XML request to synchronize Product Master
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the out payment and sends the data to the specified URL."""
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
        parent = ''
        if self.categ_id.name == 'All' or not self.categ_id:
            parent = "Primary"
        else:
            parent = str(self.categ_id.name)
        # parent_name= self.categ_id.name
        product_name = self.name
        xml = ('<ENVELOPE>\
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
                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`" >%s</UDF:UDF_PPTSMJSONMST_ODOOID >\
                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
               <OPENINGBALANCE></OPENINGBALANCE>\
                <OPENINGVALUE></OPENINGVALUE>\
                <OPENINGRATE> </OPENINGRATE>\
                </STOCKITEM>\
                </TALLYMESSAGE>\
                </ENVELOPE>'
                       % (company,parent,product_name,self.uom_id.name,str(self.id), str(sync_date)))

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
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            # error_log = ''
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                vals = (0, 0, {
                    'master_type': 'products',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': error_log,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
            rec = ET.fromstring(response.content)
            success = rec.find(".//CREATED")
            # create_log = ''
            if success is not None:
                create_log = success.text  # Assign the extracted error message
            else:
                create_log = "No CREATED element found in the XML."

            if ('<CREATED>1</CREATED>' in str(response.text)
                    or "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'products',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': create_log,
                    'name': self.name,
                    'sync_status': 'done',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
        data = {
            "tally_log_ids": tally_log_ids,
            "tally_log_xml_data": xml_data
        }
        return data
