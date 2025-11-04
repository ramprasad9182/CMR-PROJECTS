# """Odoo16 Module: Sale Order"""
# import xml.etree.ElementTree as ET
# from datetime import datetime
# from odoo import models
# import requests
# from bs4 import BeautifulSoup
#
#
# class SaleOrder(models.Model):
#     """This model extends the default functionality of 'sale.order' in Odoo16,
#     providing additional methods to synchronize out payment with an external system
#     using XML requests, specifically tailored for integration with Tally ERP."""
#     _inherit = 'sale.order'
#
#     def action_sale_order(self):
#         """This method constructs an XML request to synchronize Sale Order
#         with an external system, likely using Tally ERP. It retrieves necessary
#         details from the out payment and sends the data to the specified URL."""
#         tally_log_ids = []
#         db_config = self.env['mysqldb.config'].search([], limit=1)
#         url = db_config.db_hostname
#         company = db_config.company_name
#         h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
#         sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
#         head_xml = '<ENVELOPE>\
#                     <HEADER>\
#                     <TALLYREQUEST>Import Data</TALLYREQUEST>\
#                     </HEADER>\
#                     <BODY>\
#                     <IMPORTDATA>\
#                     <REQUESTDESC>\
#                     <REPORTNAME>Vouchers</REPORTNAME>\
#                     <STATICVARIABLES>\
#                     <SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\
#                     </STATICVARIABLES>\
#                     </REQUESTDESC>\
#                     <REQUESTDATA>\
#                     <TALLYMESSAGE xmlns:UDF="TallyUDF">\
#                                 <VOUCHER VCHTYPE="Sales Order" ACTION="Create" OBJVIEW="Invoice Voucher View">' \
#                % (company)
#
#         xml_foot = '</VOUCHER>\
#                     </TALLYMESSAGE>\
#                     </REQUESTDATA>\
#                     </IMPORTDATA>\
#                     </BODY>\
#                     </ENVELOPE>'
#
#         if self.validity_date:
#             day = '0' + str(self.validity_date.day) if self.validity_date.day < 10 \
#                 else str(self.validity_date.day)
#             month = '0' + str(self.validity_date.month) if self.validity_date.month < 10 \
#                 else str(self.validity_date.month)
#             expiration = str(self.validity_date.year) + month + day
#
#         if self.date_order:
#             day = '0' + str(self.date_order.day) if self.date_order.day < 10 \
#                 else str(self.date_order.day)
#             month = '0' + str(self.date_order.month) if self.date_order.month < 10 \
#                 else str(self.date_order.month)
#             quotation_date = str(self.date_order.year) + month + day
#         parent_xml = '<DATE>%s</DATE>\
#                 <NARRATION>%s</NARRATION>\
#                 <PARTYNAME>%s</PARTYNAME>\
#                 <VOUCHERTYPENAME>Sales order</VOUCHERTYPENAME>\
#                 <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
#                 <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
#                 <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
#                 <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
#                 <REFERENCE>%s</REFERENCE>\
#                 <PARTYMAILINGNAME>%s</PARTYMAILINGNAME>\
#                 <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\
#                 <BILLOFLADINGNO></BILLOFLADINGNO>\
#                 <EICHECKPOST></EICHECKPOST>\
#                 <BASICSHIPPEDBY></BASICSHIPPEDBY>\
#                 <BASICFINALDESTINATION>%s</BASICFINALDESTINATION>\
#                 <BASICORDERREF></BASICORDERREF>\
#                 <BASICSHIPVESSELNO></BASICSHIPVESSELNO>\
#                 <BASICDUEDATEOFPYMT>%s</BASICDUEDATEOFPYMT>\
#                 <VOUCHERNUMBERSERIES></VOUCHERNUMBERSERIES>' % (
#             expiration, self.note, self.partner_id.name, str(self.id), sync_date,
#             self.partner_id.name, self.id, self.id, self.partner_id.name, self.incoterm_location,
#             self.payment_term_id.name)
#         order_line = []
#         for rec in self.order_line:
#             child_data = '<ALLINVENTORYENTRIES.LIST>\
#             <STOCKITEMNAME>%s</STOCKITEMNAME>\
#             <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#             <RATE>%s</RATE>\
#             <AMOUNT>%s</AMOUNT>\
#             <ACTUALQTY>%s</ACTUALQTY>\
#             <BILLEDQTY>%s</BILLEDQTY>\
#             <BATCHALLOCATIONS.LIST>\
#                 <GODOWNNAME>Main Location</GODOWNNAME>\
#                 <BATCHNAME>Primary Batch</BATCHNAME>\
#                 <ORDERNO>%s</ORDERNO>\
#                 <AMOUNT>%s</AMOUNT>\
#                 <ACTUALQTY>%s</ACTUALQTY>\
#                 <BILLEDQTY>%s</BILLEDQTY>\
#                 <ORDERDUEDATE JD = "45016" P = "">%s</ORDERDUEDATE>\
#             </BATCHALLOCATIONS.LIST>\
#             <ACCOUNTINGALLOCATIONS.LIST>\
#             <LEDGERNAME>Sales order</LEDGERNAME>\
#             <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\
#             <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#             <AMOUNT>%s</AMOUNT>\
#             </ACCOUNTINGALLOCATIONS.LIST>\
#             </ALLINVENTORYENTRIES.LIST>' % (
#                 rec.product_template_id.name,rec.price_unit,rec.price_subtotal * (-1) ,
#                 rec.product_uom_qty,rec.product_uom_qty,rec.order_id.id,rec.price_subtotal * (-1),
#                 rec.product_uom_qty,rec.product_uom_qty,quotation_date,rec.price_subtotal * (-1))
#
#             order_line.append(child_data)
#
#         # for rec in self.invoice_ids.line_ids:
#         #     tax_amount = []
#         #     for res in self.invoice_ids:
#         tax_amount = []
#         for rec in self.invoice_ids.line_ids:
#             amount_tax='<LEDGERENTRIES.LIST>\
#                     <LEDGERNAME>%s</LEDGERNAME>\
#                     <AMOUNT>%s</AMOUNT>\
#                     <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
#                     </LEDGERENTRIES.LIST>' %(
#                 rec.account_id.name,rec.credit * (-1),rec.credit * (-1))
#             tax_amount.append(amount_tax)
#
#         entries_xml = '<LEDGERENTRIES.LIST>\
#                         <LEDGERNAME>%s</LEDGERNAME>\
#                         <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\
#                         <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\
#                         <AMOUNT>%s</AMOUNT>\
#                         </LEDGERENTRIES.LIST>' % (self.partner_id.name, self.amount_untaxed)
#
#         body_xml = ''
#         for body in order_line:
#             body_xml.join(body)
#         tax_id = ''
#         for tax in tax_amount:
#             tax_id.join(tax)
#         xml = head_xml + parent_xml + body_xml + tax_id + entries_xml + xml_foot
#         xml_data = xml.replace("&", "amp;")
#         soup = BeautifulSoup(xml_data, "xml")
#         pretty_xml = soup.prettify()
#         try:
#             response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
#         except requests.exceptions.RequestException as e:
#             print(e, 'eee-----------')
#
#         if response:
#             # soup_2 = BeautifulSoup(response.text, 'xml')
#             rec = ET.fromstring(response.content)
#             line_error = rec.find(".//LINEERROR")
#             if line_error is not None:
#                 line = line_error.text
#             else:
#                 line = "No LINEERROR element found in the XML"
#
#             if '<LINEERROR>' in str(response.text):
#                 vals = (0, 0, {
#                     'master_type': 'sale_order',
#                     'sync_action': 'create',
#                     'sync_data': str(pretty_xml),
#                     'error_data': line,
#                     'name': self.name,
#                     'sync_status': 'fail',
#                     'sync_for': 'master',
#                 })
#                 tally_log_ids.append(vals)
#             if ('<CREATED>1</CREATED>' in str(response.text) or
#                     "<ALTERED>1</ALTERED>" in str(response.text)):
#                 self.ndw_select = 'done'
#                 rec = ET.fromstring(response.content)
#                 log_create = rec.find(".//CREATED")
#                 if log_create is not None:
#                     line = log_create.text
#                 else:
#                     line = "No LINEERROR element found in the XML"
#                 vals = (0, 0, {
#                     'master_type': 'sale_order',
#                     'sync_action': 'create',
#                     'sync_data': str(pretty_xml),
#                     'error_data': line,
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
