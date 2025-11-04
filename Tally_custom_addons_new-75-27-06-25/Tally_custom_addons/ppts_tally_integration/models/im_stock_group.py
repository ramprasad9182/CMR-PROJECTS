# """Odoo16 Module: Product Master"""
# import xml.etree.ElementTree as ET
# from datetime import datetime
# from odoo import api, models
# import requests
# from bs4 import BeautifulSoup
#
#
# class Productgroup(models.Model):
#     """This model extends the default functionality of 'product.category' in Odoo16,
#     providing additional methods to synchronize out payment with an external system
#     using XML requests, specifically tailored for integration with Tally ERP."""
#     _inherit = "product.category"
#
#     @api.onchange('write_date')
#     def _onchange_write_date_ndw_select(self):
#         if self.tally_flag:
#             self.ndw_select = 'write'
#
#     def action_odoo_tally_stock_categ_sync(self):
#         """This method constructs an XML request to synchronize Product Category
#         with an external system, likely using Tally ERP. It retrieves necessary
#         details from the out payment and sends the data to the specified URL."""
#         tally_log_ids =[]
#         db_config = self.env['mysqldb.config'].search([], limit=1)
#         url = db_config.db_hostname
#         company = db_config.company_name
#         h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
#         sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
#         parent = ''
#         if self.parent_id.name == 'All' or not self.parent_id:
#             parent = "Primary"
#         else:
#             parent = str(self.parent_id.name)
#         xml = (('<ENVELOPE>\n<HEADER>\n<TALLYREQUEST>Import Data</TALLYREQUEST>\n</HEADER>\n'
#                '<BODY>\n<IMPORTDATA>\n<REQUESTDESC>\n<REPORTNAME>All Masters</REPORTNAME>\n'
#                '<STATICVARIABLES>\n<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\n</STATICVARIABLES>\n</REQUESTDESC>\n<REQUESTDATA>\n'
#                '<TALLYMESSAGE xmlns:UDF="TallyUDF">\n<STOCKGROUP NAME="" RESERVEDNAME="">\n<PARENT>%s</PARENT> \n'
#                '<UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\n'
#                '<UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>'
#                '<NAME>%s</NAME>\n'
#                '</STOCKGROUP>\n</TALLYMESSAGE>\n</ENVELOPE>') %
#                (company, parent, str(self.id), sync_date,self.name))
#         xml_data = xml.replace("&", "amp;")
#         soup = BeautifulSoup(xml_data, "xml")
#         pretty_xml = soup.prettify()
#         response = False
#         try:
#             response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
#         except requests.exceptions.RequestException as e:
#             print(e, 'eee-----------')
#         # line = ''
#         if response:
#             # soup_2 = BeautifulSoup(response.text, 'xml')
#             rec = ET.fromstring(response.content)
#             line_error = rec.find(".//LINEERROR")
#             if line_error is not None:
#                 line = line_error.text
#             else:
#                 line = "No LINEERROR element found in the XML"
#             if '<LINEERROR>' in str(response.text):
#                 vals = (0, 0, {
#                     'master_type': 'prod_categ',
#                     'sync_action': 'create',
#                     'sync_data': str(pretty_xml),
#                     'error_data': line,
#                     'name': self.name,
#                     'sync_status': 'fail',
#                     'sync_for': 'master',
#                 })
#                 tally_log_ids.append(vals)
#             rec = ET.fromstring(response.content)
#             success = rec.find(".//CREATED")
#             if success is not None:
#                 create_log = success.text
#             else:
#                 create_log = "No LINEERROR element found in the XML"
#             if ('<CREATED>1</CREATED>' in str(response.text) or
#                     "<ALTERED>1</ALTERED>" in str(response.text)):
#                 self.ndw_select = 'done'
#
#                 vals = (0, 0, {
#                     'master_type': 'prod_categ',
#                     'sync_action': 'create',
#                     'sync_data': str(pretty_xml),
#                     'error_data': create_log,
#                     'name': self.name,
#                     'sync_status': 'done',
#                     'sync_for': 'master',
#                 })
#                 tally_log_ids.append(vals)
#         data = {
#             "tally_log_ids": tally_log_ids,
#             "tally_log_xml_data": xml_data
#         }
#         return data
