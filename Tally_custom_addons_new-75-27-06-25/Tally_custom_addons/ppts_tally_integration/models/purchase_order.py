# """Odoo16 Module: Purchase Order"""
# import xml.etree.ElementTree as ET
# from datetime import datetime
# from odoo import models
# import requests
# from bs4 import BeautifulSoup
#
#
# class PurchaseOrder(models.Model):
#     """This model extends the default functionality of 'purchase.order' in Odoo16,
#     providing additional methods to synchronize out payment with an external system
#     using XML requests, specifically tailored for integration with Tally ERP."""
#     _inherit = 'purchase.order'
#
#     def action_purchase_order(self):
#         """This method constructs an XML request to synchronize Purchase Order
#         with an external system, likely using Tally ERP. It retrieves necessary
#         details from the out payment and sends the data to the specified URL."""
#         tally_log_ids = []
#         db_config = self.env['mysqldb.config'].search([], limit=1)
#         url = db_config.db_hostname
#         company = db_config.company_name
#         h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
#         sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
#
#         head_xml = '<ENVELOPE>\
#                 <HEADER>\
#                 <TALLYREQUEST>Import Data</TALLYREQUEST>\
#                 </HEADER>\
#                         <BODY>\
#                 <IMPORTDATA>\
#                 <REQUESTDESC>\
#                 <REPORTNAME>Vouchers</REPORTNAME>\
#                 <STATICVARIABLES>\
#                 <SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\
#                 </STATICVARIABLES>\
#                 </REQUESTDESC>\
#                 <REQUESTDATA>\
#                 <TALLYMESSAGE xmlns:UDF="TallyUDF">\
#                             <VOUCHER VCHTYPE="Purchase Order" ACTION="Create" OBJVIEW="Invoice Voucher View">' \
#                    % (company)
#
#         xml_foot = '</VOUCHER>\
#                         </TALLYMESSAGE>\
#                         </REQUESTDATA>\
#                         </IMPORTDATA>\
#                         </BODY>\
#                         </ENVELOPE>'
#
#         if self.date_approve:
#             day = '0' + str(self.date_approve.day) if self.date_approve.day < 10 \
#                 else str(self.date_approve.day)
#             month = '0' + str(self.date_approve.month) if self.date_approve.month < 10 \
#                 else str(self.date_approve.month)
#             confirmation_date = str(self.date_approve.year) + month + day
#
#         if self.date_planned:
#             day = '0' + str(self.date_planned.day) if self.date_planned.day < 10 \
#                 else str(self.date_planned.day)
#             month = '0' + str(self.date_planned.month) if self.date_planned.month < 10 \
#                 else str(self.date_planned.month)
#             planned_date = str(self.date_planned.year) + month + day
#
#         parent_xml = '<DATE>%s</DATE>\
#         <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`" >%s</UDF:UDF_PPTSMJSONMST_ODOOID >\
#         <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
#         <NARRATION>%s</NARRATION>\
#         <PARTYNAME>%s</PARTYNAME>\
#         <VOUCHERTYPENAME>Purchase Order</VOUCHERTYPENAME>\
#         <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
#         <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
#         <REFERENCE>%s</REFERENCE>\
#         <PARTYMAILINGNAME>%s</PARTYMAILINGNAME>\
#         <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\
#         <BILLOFLADINGNO></BILLOFLADINGNO>\
#         <EICHECKPOST></EICHECKPOST>\
#         <BASICSHIPPEDBY>%s</BASICSHIPPEDBY>\
#         <BASICFINALDESTINATION>%s</BASICFINALDESTINATION>\
#         <BASICORDERREF>%s</BASICORDERREF>\
#         <BASICSHIPVESSELNO></BASICSHIPVESSELNO>\
#         <BASICDUEDATEOFPYMT>%s</BASICDUEDATEOFPYMT>\
#         <VOUCHERNUMBERSERIES></VOUCHERNUMBERSERIES>' % (
#         confirmation_date, str(self.id), str(sync_date), self.notes, self.partner_id.name,
#         self.partner_id.name, self.id, self.id,self.partner_id.name, self.incoterm_id.name,
#         self.incoterm_location, self.partner_ref,self.payment_term_id.name)
#
#         order_line = []
#         for rec in self.order_line:
#             child_data = '<ALLINVENTORYENTRIES.LIST>\
#             <STOCKITEMNAME>%s</STOCKITEMNAME>\
#             <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#             <RATE>%s</RATE>\
#             <AMOUNT>%s</AMOUNT>\
#             <ACTUALQTY>%s</ACTUALQTY>\
#             <BILLEDQTY>%s</BILLEDQTY>\
#             <BATCHALLOCATIONS.LIST >\
#                 <GODOWNNAME>Main Location</GODOWNNAME>\
#                 <BATCHNAME>Primary Batch</BATCHNAME>\
#                 <ORDERNO>%s</ORDERNO>\
#                 <AMOUNT>%s</AMOUNT>\
#                 <ACTUALQTY>%s</ACTUALQTY>\
#                 <BILLEDQTY>%s</BILLEDQTY>\
#                 <ORDERDUEDATE JD = "45016" P = "" >%s</ORDERDUEDATE>\
#             </BATCHALLOCATIONS.LIST>\
#             <ACCOUNTINGALLOCATIONS.LIST>\
#             <LEDGERNAME>Purchase Order</LEDGERNAME>\
#             <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\
#             <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#             <AMOUNT>%s</AMOUNT>\
#             </ACCOUNTINGALLOCATIONS.LIST>\
#             </ALLINVENTORYENTRIES.LIST >' % (
#                 rec.product_id.name,rec.price_unit,rec.price_subtotal,rec.product_qty,
#                 rec.product_qty,rec.order_id.id,rec.price_subtotal,rec.product_qty,
#                 rec.product_qty,planned_date,rec.price_subtotal)
#             order_line.append(child_data)
#
#         tax_amount = []
#         for rec in self.invoice_ids.line_ids:
#             amount_tax = '<LEDGERENTRIES.LIST>\
#                             <LEDGERNAME>%s</LEDGERNAME>\
#                             <AMOUNT>%s</AMOUNT>\
#                             <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
#                             </LEDGERENTRIES.LIST>' % (rec.account_id.name, rec.debit, rec.debit)
#             tax_amount.append(amount_tax)
#
#         entries_xml =  '<LEDGERENTRIES.LIST>\
#         <LEDGERNAME>%s</LEDGERNAME>\
#         <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\
#         <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\
#         <AMOUNT>%s</AMOUNT>\
#         </LEDGERENTRIES.LIST>' % (self.partner_id.name,self.amount_untaxed)
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
#
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
#
#             if '<LINEERROR>' in str(response.text):
#                 vals = (0, 0, {
#                     'master_type': 'purchase_order',
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
#                     'master_type': 'purchase_order',
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
