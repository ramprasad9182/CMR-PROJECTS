# """Odoo16 Module: Unit of Measure Category Master"""
# import xml.etree.ElementTree as ET
# from datetime import datetime
# from odoo import api, models
# import requests
# from bs4 import BeautifulSoup
#
#
# class UomCategory(models.Model):
#     """This model extends the default functionality of 'uom.category' in Odoo16,
#     providing additional methods to synchronize out payment with an external system
#     using XML requests, specifically tailored for integration with Tally ERP."""
#     _inherit = "uom.category"
#
#     @api.onchange('write_date')
#     def _onchange_write_date_ndw_select(self):
#         if self.tally_flag:
#             self.ndw_select = 'write'
#
#     def action_odoo_tally_uom_sync(self):
#         """This method constructs an XML request to synchronize UOM Category
#         with an external system, likely using Tally ERP. It retrieves necessary
#         details from the out payment and sends the data to the specified URL."""
#         tally_log_ids = []
#         db_config = self.env['mysqldb.config'].search([], limit=1)
#         url = db_config.db_hostname
#         company = db_config.company_name
#         h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
#         sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
#         # group_action = "CREATE"
#         # group_name = "Stock UOM"
#         # xml = ''
#         # uom_list = []
#         for rec in self.uom_ids:
#             xml = '<ENVELOPE>\n<HEADER>\n<TALLYREQUEST>Import Data</TALLYREQUEST>\n</HEADER>\n<BODY>\n<IMPORTDATA>\n<REQUESTDESC>\n<REPORTNAME>All Masters</REPORTNAME>\n<STATICVARIABLES>\n<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\n</STATICVARIABLES>\n</REQUESTDESC>\n<REQUESTDATA>\n<TALLYMESSAGE xmlns:UDF="TallyUDF">\n<UNIT NAME="Import" RESERVEDNAME="">\n<NAME>%s</NAME>\n<GUID></GUID>\n<ORIGINALNAME>%s</ORIGINALNAME>\n<GSTREPUOM>%s</GSTREPUOM>\n<ASORIGINAL>Yes</ASORIGINAL>\n<ISGSTEXCLUDED>No</ISGSTEXCLUDED>\n<ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>\n<ALTERID>%s</ALTERID>\n<UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\n<UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\n<DECIMALPLACES>2</DECIMALPLACES>\n</UNIT>\n</TALLYMESSAGE>\n</REQUESTDATA>\n</IMPORTDATA>\n</BODY>\n</ENVELOPE>' % (company, rec.name[0],rec.name,rec.l10n_in_code,str(rec.id), str(self.id), sync_date)
#             # uom_list.append(xml)
#             xml_data = xml.replace("&", "amp;")
#             soup = BeautifulSoup(xml_data, "xml")
#             pretty_xml = soup.prettify()
#             response = False
#             try:
#                 response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'),
#                                          timeout=60)
#             except requests.exceptions.RequestException as e:
#                 print(e, 'eee-----------')
#
#             if response:
#                 # soup_2 = BeautifulSoup(response.text, 'xml')
#                 rec = ET.fromstring(response.content)
#                 line_error = rec.find(".//LINEERROR")
#                 # error_log = ''
#                 if line_error is not None:
#                     error_log = line_error.text  # Assign the extracted error message
#                 else:
#                     error_log = "No LINEERROR element found in the XML."
#                 if '<LINEERROR>' in str(response.text):
#                     self.ndw_select = 'new'
#                     vals = (0, 0, {
#                         'master_type': 'uom',
#                         'sync_action': 'create',
#                         'sync_data': str(pretty_xml),
#                         'error_data': error_log,
#                         'name': self.name,
#                         'sync_status': 'fail',
#                         'sync_for': 'master',
#                     })
#                     tally_log_ids.append(vals)
#                 rec = ET.fromstring(response.content)
#                 success = rec.find(".//CREATED")
#                 # create_log = ''
#                 if success is not None:
#                     create_log = success.text  # Assign the extracted error message
#                 else:
#                     create_log = "No LINEERROR element found in the XML."
#                 if ('<CREATED>1</CREATED>' in str(response.text)
#                         or "<ALTERED>1</ALTERED>" in str(response.text)):
#                     self.ndw_select = 'done'
#                     vals = (0, 0, {
#                         'master_type': 'uom',
#                         'sync_action': 'create',
#                         'sync_data': str(pretty_xml),
#                         'error_data': create_log,
#                         'name': self.name,
#                         'sync_status': 'done',
#                         'sync_for': 'master',
#                     })
#                     tally_log_ids.append(vals)
#                     # self.env.user.notify_success(message='Records successfully Created / Altered')
#             data = {
#                 "tally_log_ids": tally_log_ids,
#                 "tally_log_xml_data": xml_data
#             }
#             return data
