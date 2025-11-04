"""Odoo16 Module: In Payment
This module extends the default functionality of 'account.move' in Odoo16,
providing additional methods to synchronize out payment with an external system
using XML requests, specifically tailored for integration with Tally ERP."""
import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import models
import requests
from bs4 import BeautifulSoup


class AccountInPayment(models.Model):
    _inherit = 'account.move'

    def action_in_payment(self):
        """This method constructs an XML request to synchronize In Payment
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the in payment and sends the data to the specified URL."""
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
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
                    <VOUCHER REMOTEID="" VCHKEY="" VCHTYPE="Receipt" ACTION="Create" OBJVIEW="Accounting Voucher View">' % (
            company)

        xml_foot = '</VOUCHER>\
                            </TALLYMESSAGE>\
                            </REQUESTDATA>\
                            </IMPORTDATA>\
                            </BODY>\
                            </ENVELOPE>'

        if self.date:
            day = '0' + str(self.date.day) if self.date.day < 10 else str(self.date.day)
            month = '0' + str(self.date.month) if self.date.month < 10 else str(self.date.month)
            payment_date = str(self.date.year) + month + day

        # I will change the xml tag parent_xml:
        parent_xml = '<OLDAUDITENTRYIDS.LIST TYPE="Number">\
                    <OLDAUDITENTRYIDS></OLDAUDITENTRYIDS>\
                    </OLDAUDITENTRYIDS.LIST>\
                    <DATE>%s</DATE>\
                    <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                    <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                    <NARRATION></NARRATION>\
                    <TAXUNITNAME></TAXUNITNAME>\
                    <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
                    <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>\
                    <VOUCHERNUMBER>2</VOUCHERNUMBER>\
                    <FBTPAYMENTTYPE>Default</FBTPAYMENTTYPE>\
                    <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>\
                    <VCHGSTCLASS/>\
                    <EFFECTIVEDATE>%s</EFFECTIVEDATE>\
                    <ALTERID>%s</ALTERID>\
                    <MASTERID>%s</MASTERID>\
                    <VOUCHERKEY>193342247796760</VOUCHERKEY>' % (
            payment_date, str(self.id), sync_date, self.payment_id.partner_id.name,
            payment_date, str(self.id), str(self.id))
        body_list = []
        line_items = []

        for partner_line in (self.line_ids.filtered
            (lambda l: l.account_type == 'Receivable' and l.account_id)):
            if partner_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': partner_line.account_id.name,
                                   'account_type': partner_line.account_id.account_type})

        for ac_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type not in
                          ['Receivable', 'Current Liabilities'] and l.account_id):
            if ac_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': ac_line.account_id.name,
                                   'account_type': ac_line.account_id.account_type})

        for tax_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type == 'Current Liabilities' and l.account_id):
            if tax_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': tax_line.account_id.name,
                                   'account_type': tax_line.account_id.account_type})

        amt_credit_debit = ''

        for line in line_items:
            # ch_ledger_name = line.account_id.name
            ch_ledger_name = self.partner_id.name if line['account_name'] == 'Debtors'\
                else line['account_name']
            debit = round(sum(l.debit for l in self.line_ids
                               if l.account_id.name == line['account_name']), 2) or 0
            credit = round(sum(l.credit for l in self.line_ids
                                if l.account_id.name == line['account_name']), 2) or 0
            if line['account_type'] == 'asset_receivable' and debit:
                is_deemed_positive = "Yes"
                is_party_ledger = "Yes"
                is_lastdigit_positive = "Yes"
                amount = debit * (-1)
            else:
                amount = debit * (-1) if debit > 0 else credit
                is_deemed_positive = "Yes" if debit > 0 else "No"
                is_party_ledger = "No"
                is_lastdigit_positive = "Yes" if debit > 0 else "No"

            amt_credit_debit = '<ALLLEDGERENTRIES.LIST>\
                           <LEDGERNAME>%s</LEDGERNAME>\
                           <ISDEEMEDPOSITIVE>%s</ISDEEMEDPOSITIVE>\
                           <LEDGERFROMITEM>yes</LEDGERFROMITEM>\
                           <REMOVEZEROENTRIES>yes</REMOVEZEROENTRIES>\
                           <ISPARTYLEDGER>%s</ISPARTYLEDGER>\
                           <ISLASTDEEMEDPOSITIVE>%s</ISLASTDEEMEDPOSITIVE>\
                           <ISCAPVATTAXALTERED>yes</ISCAPVATTAXALTERED>\
                           <ISCAPVATNOTCLAIMED>yes</ISCAPVATNOTCLAIMED>\
                           <AMOUNT>%s</AMOUNT>\
                           </ALLLEDGERENTRIES.LIST>' % (
                ch_ledger_name, is_deemed_positive, is_party_ledger,
                is_lastdigit_positive, str(amount))
            body_list.append(amt_credit_debit)
        body_xml = ''
        for body in body_list:
            body_xml.join(body)
        xml = head_xml + parent_xml + body_xml + xml_foot
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
            if line_error is not None:
                line = line_error.text
            else:
                line = "No LINEERROR element found in the XML"

            if '<LINEERROR>' in str(response.text):
                vals = (0, 0, {
                    'master_type': 'in_payment',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': line,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'trans',
                })
                tally_log_ids.append(vals)
            if ('<CREATED>1</CREATED>' in str(response.text)
                    or "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                rec = ET.fromstring(response.content)
                log_create = rec.find(".//CREATED")
                if log_create is not None:
                    line = log_create.text
                else:
                    line = "No LINEERROR element found in the XML"
                vals = (0, 0, {
                    'master_type': 'in_payment',
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
