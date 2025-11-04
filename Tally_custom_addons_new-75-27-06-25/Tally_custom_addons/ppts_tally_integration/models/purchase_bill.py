# """Odoo16 Module: Purchase Bill"""
# import xml.etree.ElementTree as ET
# from datetime import datetime
# from odoo import models
# import requests
# from bs4 import BeautifulSoup
#
#
# class PurchaseBill(models.Model):
#     """This model extends the default functionality of 'account.move' in Odoo16,
#     providing additional methods to synchronize out payment with an external system
#     using XML requests, specifically tailored for integration with Tally ERP."""
#     _inherit = 'account.move'
#
#     def action_purchase_bill_sync(self):
#         """This method constructs an XML request to synchronize Purchase Bill
#         with an external system, likely using Tally ERP. It retrieves necessary
#         details from the out payment and sends the data to the specified URL."""
#         tally_log_ids = []
#         db_config = self.env['mysqldb.config'].search([], limit=1)
#         url = db_config.db_hostname
#         company = db_config.company_name
#         h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
#         sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
#         head_xml = '<ENVELOPE>\
#                            <HEADER>\
#                            <TALLYREQUEST>Import Data</TALLYREQUEST>\
#                            </HEADER>\
#                            <BODY>\
#                            <IMPORTDATA>\
#                            <REQUESTDESC>\
#                            <REPORTNAME>Vouchers</REPORTNAME>\
#                            <STATICVARIABLES>\
#                            <SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\
#                            </STATICVARIABLES>\
#                            </REQUESTDESC>\
#                            <REQUESTDATA>\
#                            <TALLYMESSAGE xmlns:UDF="TallyUDF">\
#                                        <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">' \
#                    % (company)
#
#         xml_foot = '</VOUCHER>\
#                    </TALLYMESSAGE>\
#                    </REQUESTDATA>\
#                    </IMPORTDATA>\
#                    </BODY>\
#                    </ENVELOPE>'
#
#         if self.invoice_date:
#             day = '0' + str(self.invoice_date.day) if self.invoice_date.day < 10 \
#                 else str(self.invoice_date.day)
#             month = '0' + str(self.invoice_date.month) if self.invoice_date.month < 10 \
#                 else str(self.invoice_date.month)
#             bill = str(self.invoice_date.year) + month + day
#
#         if self.date:
#             day = '0' + str(self.date.day) if self.date.day < 10 else str(self.date.day)
#             month = '0' + str(self.date.month) if self.date.month < 10 else str(self.date.month)
#             accounting_date = str(self.date.year) + month + day
#
#         parent_xml = '<DATE>%s</DATE>\
#                    <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`" >%s</UDF:UDF_PPTSMJSONMST_ODOOID >\
#                    <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
#                    <NARRATION>%s</NARRATION>\
#                    <PARTYNAME>%s</PARTYNAME>\
#                    <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>\
#                    <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
#                    <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
#                    <REFERENCE>%s</REFERENCE>\
#                    <PARTYMAILINGNAME>%s</PARTYMAILINGNAME>\
#                    <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\
#                    <BILLOFLADINGNO></BILLOFLADINGNO>\
#                    <EICHECKPOST></EICHECKPOST>\
#                    <BASICSHIPPEDBY>%s</BASICSHIPPEDBY>\
#                    <BASICFINALDESTINATION></BASICFINALDESTINATION>\
#                    <BASICORDERREF>%s</BASICORDERREF>\
#                    <BASICSHIPVESSELNO></BASICSHIPVESSELNO>\
#                    <BASICDUEDATEOFPYMT></BASICDUEDATEOFPYMT>\
#                    <VOUCHERNUMBERSERIES></VOUCHERNUMBERSERIES>' % (
#             bill,str(self.id), str(sync_date),self.name, self.partner_id.name,
#             self.partner_id.name, self.id, self.id,
#             self.partner_id.name,self.invoice_incoterm_id.name,self.ref)
#         order_line = []
#         account_coa = []
#         for rec in self.invoice_line_ids:
#             child_data = '<ALLINVENTORYENTRIES.LIST>\
#                <STOCKITEMNAME>%s</STOCKITEMNAME>\
#                <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#                <RATE>%s</RATE>\
#                <AMOUNT>%s</AMOUNT>\
#                <ACTUALQTY>%s</ACTUALQTY>\
#                <BILLEDQTY>%s</BILLEDQTY>\
#                <BATCHALLOCATIONS.LIST>\
#                    <GODOWNNAME>Main Location</GODOWNNAME>\
#                    <BATCHNAME>Primary Batch</BATCHNAME>\
#                    <ORDERNO></ORDERNO>\
#                    <AMOUNT>%s</AMOUNT>\
#                    <ACTUALQTY>%s</ACTUALQTY>\
#                    <BILLEDQTY>%s</BILLEDQTY>\
#                    <ORDERDUEDATE JD = "45016" P = "">%s</ORDERDUEDATE>\
#                </BATCHALLOCATIONS.LIST>\
#                <ACCOUNTINGALLOCATIONS.LIST>\
#                <LEDGERNAME>Purchase</LEDGERNAME>\
#                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\
#                <ISLASTDEEMEDPOSITIVE>Yes</ISLASTDEEMEDPOSITIVE>\
#                <AMOUNT>%s</AMOUNT>\
#                </ACCOUNTINGALLOCATIONS.LIST>\
#                </ALLINVENTORYENTRIES.LIST>' % (
#                 rec.product_id.name, rec.price_unit * (-1), rec.price_subtotal *(-1),
#                 rec.quantity * (-1), rec.quantity * (-1),rec.price_subtotal * (-1),
#                 rec.quantity * (-1),  rec.quantity * (-1), accounting_date,
#                 rec.price_subtotal * (-1))
#             account_coa.append(rec.account_id.id)
#             order_line.append(child_data)
#
#         tax_amount = []
#         for rec in self.line_ids:
#             if rec.account_id.id not in account_coa:
#                 if rec.credit > 0.0:
#                     print('rec.debit', rec.debit)
#                     amount_tax = '<LEDGERENTRIES.LIST>\
#                                   <LEDGERNAME>%s</LEDGERNAME>\
#                                   <AMOUNT>%s</AMOUNT>\
#                                   <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
#                                   </LEDGERENTRIES.LIST>' % (
#                         rec.account_id.name, rec.credit, rec.credit)
#                     tax_amount.append(amount_tax)
#                 elif rec.debit > 0.0:
#                     print('rec.credit', rec.credit)
#                     amount_tax = '<LEDGERENTRIES.LIST>\
#                                   <LEDGERNAME>%s</LEDGERNAME>\
#                                   <AMOUNT>%s</AMOUNT>\
#                                   <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
#                                   </LEDGERENTRIES.LIST>' % (rec.account_id.name, rec.debit * (-1),
#                                                             rec.debit * (-1))
#                     tax_amount.append(amount_tax)
#
#         # entries_xml = '<LEDGERENTRIES.LIST>\
#         #                    <LEDGERNAME>%s</LEDGERNAME>\
#         #                    <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\
#         #                    <ISPARTYLEDGER>No</ISPARTYLEDGER>\
#         #                    <AMOUNT>%s</AMOUNT>\
#         #                    </LEDGERENTRIES.LIST>' % (self.partner_id.name,self.amount_residual)
#
#         body_xml = ''
#         for body in order_line:
#             body_xml.join(body)
#         tax_id = ''
#         for tax in tax_amount:
#             tax_id.join(tax)
#         xml = head_xml + parent_xml + body_xml + tax_id + xml_foot
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
#             if '<LINEERROR>' in str(response.text):
#                 vals = (0, 0, {
#                     'master_type': 'in_invoice',
#                     'sync_action': 'create',
#                     'sync_data': str(pretty_xml),
#                     'error_data': line,
#                     'name': self.name,
#                     'sync_status': 'fail',
#                     'sync_for': 'master',
#                 })
#                 tally_log_ids.append(vals)
#
#             if ('<CREATED>1</CREATED>' in str(response.text)
#                     or "<ALTERED>1</ALTERED>" in str(response.text)):
#                 self.ndw_select = 'done'
#                 rec = ET.fromstring(response.content)
#                 log_create = rec.find(".//CREATED")
#                 if log_create is not None:
#                     line = log_create.text
#                 else:
#                     line = "No LINEERROR element found in the XML"
#                 vals = (0, 0, {
#                     'master_type': 'in_invoice',
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
