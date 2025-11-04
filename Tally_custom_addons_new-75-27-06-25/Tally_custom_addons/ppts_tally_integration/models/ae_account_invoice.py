""" This module requires access to Tally ERP and involves sending sensitive
    invoice data. Ensure proper permissions and security measures are in place
    before utilizing these functions in a production environment."""

import xml.etree.ElementTree as ET
from odoo import api, models
from datetime import datetime
import requests
from bs4 import BeautifulSoup


class AccountMove(models.Model):
    """ Extends the 'account.move' model for additional functionality."""
    _inherit = "account.move"

    @api.onchange('write_date','state')
    def _onchange_write_date_ndw_select(self):
        if self.tally_flag:
            self.ndw_select = 'write'

    def action_sale_invoice_sync(self):
        """Syncs sale invoices with Tally ERP.

               This function prepares invoice data, generates XML, and sends it to the
               specified URL to synchronize sales invoices with Tally ERP.

               Returns:
                   list: List of tuples containing synchronization log details.
               """
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        h = {'Content-Encoding': 'gzip','CONTENT-TYPE': 'text/xml; charset=utf-8'}
        sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
        head_xml = '<ENVELOPE>\
                        <HEADER>\
                        <TALLYREQUEST>Import Data</TALLYREQUEST>\
                        </HEADER>\
                        <BODY>\
                        <IMPORTDATA>\
                        <REQUESTDESC>\
                        <REPORTNAME>Vouchers</REPORTNAME>\
                        <STATICVARIABLES>\
                        <SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\
                        </STATICVARIABLES>\
                        </REQUESTDESC>\
                        <REQUESTDATA>\
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">\
                                    <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">' \
                   % (company)

        xml_foot = '</VOUCHER>\
                    </TALLYMESSAGE>\
                    </REQUESTDATA>\
                    </IMPORTDATA>\
                    </BODY>\
                    </ENVELOPE>'

        if self.invoice_date:
            day = '0' + str(self.invoice_date.day) \
                if self.invoice_date.day < 10 else str(self.invoice_date.day)
            month = '0' + str(self.invoice_date.month) \
                if self.invoice_date.month < 10 else str(self.invoice_date.month)
            sale_invoice = str(self.invoice_date.year) + month + day

        invoice_date = ''
        if self.sale_id.date_order:
            day = '0' + str(self.sale_id.date_order.day)\
                if self.sale_id.date_order.day < 10 else str(self.sale_id.date_order.day)
            month = '0' + str(self.sale_id.date_order.month) \
                if self.sale_id.date_order.month < 10 else str(self.sale_id.date_order.month)
            invoice_date = str(self.sale_id.date_order.year) + month + day

        parent_xml = '<DATE>%s</DATE>\
                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                <NARRATION>%s</NARRATION>\
                <PARTYNAME>%s</PARTYNAME>\
                <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>\
                <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
                <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
                <REFERENCE>%s</REFERENCE>\
                <PARTYMAILINGNAME>%s</PARTYMAILINGNAME>\
                <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\
                <BILLOFLADINGNO></BILLOFLADINGNO>\
                <EICHECKPOST></EICHECKPOST>\
                <BASICSHIPPEDBY></BASICSHIPPEDBY>\
                <BASICFINALDESTINATION>%s</BASICFINALDESTINATION>\
                <BASICORDERREF></BASICORDERREF>\
                <BASICSHIPVESSELNO></BASICSHIPVESSELNO>\
                <BASICDUEDATEOFPYMT>%s</BASICDUEDATEOFPYMT>\
                <VOUCHERNUMBERSERIES></VOUCHERNUMBERSERIES>' % (
            sale_invoice, str(self.id), sync_date, self.name, self.partner_id.name,
            self.partner_id.name, self.id, self.id,
            self.partner_id.name, self.invoice_incoterm_id.name,
            self.payment_reference)
        order_line = []
        account_coa = []
        for rec in self.invoice_line_ids:
            child_data = '<ALLINVENTORYENTRIES.LIST>\
            <STOCKITEMNAME>%s</STOCKITEMNAME>\
            <ISLASTDEEMEDPOSITIVE>No</ISLASTDEEMEDPOSITIVE>\
            <RATE>%s</RATE>\
            <AMOUNT>%s</AMOUNT>\
            <ACTUALQTY>%s</ACTUALQTY>\
            <BILLEDQTY>%s</BILLEDQTY>\
            <BATCHALLOCATIONS.LIST>\
                <GODOWNNAME>Main Location</GODOWNNAME>\
                <BATCHNAME>Primary Batch</BATCHNAME>\
                <ORDERNO></ORDERNO>\
                <AMOUNT>%s</AMOUNT>\
                <ACTUALQTY>%s</ACTUALQTY>\
                <BILLEDQTY>%s</BILLEDQTY>\
                <ORDERDUEDATE JD = "45016" P = "">%s</ORDERDUEDATE>\
            </BATCHALLOCATIONS.LIST>\
            <ACCOUNTINGALLOCATIONS.LIST>\
            <LEDGERNAME>%s</LEDGERNAME>\
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\
            <ISLASTDEEMEDPOSITIVE>No</ISLASTDEEMEDPOSITIVE>\
            <AMOUNT>%s</AMOUNT>\
            </ACCOUNTINGALLOCATIONS.LIST>\
            </ALLINVENTORYENTRIES.LIST>' % (rec.product_id.name,rec.price_unit
            ,rec.price_subtotal * (-1)
            ,rec.quantity,rec.quantity,rec.price_subtotal * (-1) ,rec.quantity
            ,rec.quantity,invoice_date,rec.account_id.name,rec.price_subtotal )
            account_coa.append(rec.account_id.id)
            order_line.append(child_data)

        # partner_balance =''
        # for order in self.line_ids:
        #     partner_balance -= (order.credit)

        tax_amount = []
        for rec in self.line_ids:
            if rec.account_id.id not in account_coa:
                if rec.credit > 0.0:
                    print('rec.credit', rec.credit)
                    amount_tax = '<LEDGERENTRIES.LIST>\
                                   <LEDGERNAME>%s</LEDGERNAME>\
                                   <AMOUNT>%s</AMOUNT>\
                                   <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
                                   </LEDGERENTRIES.LIST>' % (rec.account_id.name,
                                                             rec.credit, rec.credit)
                    tax_amount.append(amount_tax)
                elif rec.debit >  0.0:
                    print('rec.debit', rec.debit)
                    amount_tax = '<LEDGERENTRIES.LIST>\
                                                   <LEDGERNAME>%s</LEDGERNAME>\
                                                   <AMOUNT>%s</AMOUNT>\
                                                   <VATEXPAMOUNT>%s</VATEXPAMOUNT>\
                                                   </LEDGERENTRIES.LIST>' % (
                    rec.account_id.name, rec.debit * (-1),rec.debit * (-1))
                    tax_amount.append(amount_tax)

        # entries_xml = '<LEDGERENTRIES.LIST>\
        #                 <LEDGERNAME>%s</LEDGERNAME>\
        #                 <ISDEEMEDPOSITIVE>yes</ISDEEMEDPOSITIVE>\
        #                 <ISPARTYLEDGER>yes</ISPARTYLEDGER>\
        #                 <AMOUNT>%s</AMOUNT>\
        #                 </LEDGERENTRIES.LIST>' % (self.partner_id.name,
        #                 self.amount_residual * (-1))

        body_xml = ''
        for body in order_line:
            # body_xml += body
            body_xml .join(body)
        tax_id = ''
        for tax in tax_amount:
            tax_id .join(tax)
        # xml = (head_xml + parent_xml + body_xml + tax_id + entries_xml + xml_foot)
        xml = head_xml + parent_xml + body_xml + tax_id + xml_foot
        xml_data = xml.replace("&", "amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=10)
        except requests.exceptions.RequestException as e:
            print(e, 'eee-----------')

        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            if line_error is not None:
                line = line_error.text
            else:
                line = "No LINEERROR element found in the XML"

            if '<LINEERROR>' in str(response.text):
                vals = (0, 0, {
                    'master_type': 'out_invoice',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': line,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                rec = ET.fromstring(response.content)
                log_create = rec.find(".//CREATED")
                if log_create is not None:
                    line = log_create.text
                else:
                    line = "No LINEERROR element found in the XML"
                vals = (0, 0, {
                    'master_type': 'out_invoice',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': line,
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
