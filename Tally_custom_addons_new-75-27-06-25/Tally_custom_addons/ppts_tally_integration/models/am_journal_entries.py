"""Odoo16 Module: Account Journal Entries

This module extends the default functionality of 'account.move' in Odoo16,
providing additional methods to synchronize journal entries with an external system
using XML requests, specifically tailored for integration with Tally ERP.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import models,fields,api
import requests
from bs4 import BeautifulSoup
import pytz
import time


class AccountJournalEntries(models.Model):
    _inherit = 'account.move'

    narrate = fields.Text(string='Narration')

    @api.model
    def create(self, vals):
        vals['ndw_select'] = 'new'
        return super(AccountJournalEntries, self).create(vals)

    def write(self, vals):
        for rec in self:
            # Only set to 'write' if it was 'done' before AND you're not explicitly updating ndw_select
            if rec.ndw_select == 'done' and 'ndw_select' not in vals:
                vals['ndw_select'] = 'write'
        return super(AccountJournalEntries, self).write(vals)

    def action_journal_entries(self):
        self.ensure_one()
        # general_journals = self.filtered(lambda rec: rec.journal_id.type == 'general')
        general_journals = self
        for rec in general_journals:
            print('Journal Type:', rec.journal_id.type, ' | Move:', rec.name)
        """This method constructs an XML request to synchronize journal entries
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the journal entries and sends the data to the specified URL."""
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        # tally_narration=self.
        if self:
            odoo_currcmp = self.company_id
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        # current_company_id = self.company_id or self.company_ids[0] if self.company_ids else False  # Get the current company ID
        # print('odoocmp', odoo_curcmp)

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', odoo_currcmp.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({odoo_currcmp}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({odoo_currcmp})')

        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        print("System time:", time.tzname)
        print("Local time:", datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        print("synctime", sync_date_str)


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
                <VOUCHER REMOTEID="" VCHKEY="" VCHTYPE="Journal" ACTION="Create" OBJVIEW="Accounting Voucher View">' % (tally_currcompany)

        xml_foot = ('<NARRATION>%s</NARRATION>\
                    </VOUCHER>\
                </TALLYMESSAGE>\
                </REQUESTDATA>\
                </IMPORTDATA>\
                </BODY>\
                </ENVELOPE>' % (self.narrate))

        if self.date:
            day = '0' + str(self.date.day) if self.date.day < 10 else str(self.date.day)
            month = '0' + str(self.date.month) if self.date.month < 10 else str(self.date.month)
            payment_date = str(self.date.year) + month + day

        parent_xml = ('<DATE>%s</DATE>\
                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`" >%s</UDF:UDF_PPTSMJSONMST_ODOOID >\
                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
               <VOUCHERTYPENAME>%s</VOUCHERTYPENAME>\
               <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
               <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>'
                      % (
        payment_date, str(self.id), str(sync_date), str(self.journal_id.name), str(self.name)))

        body_list = []
        line_items = []
        for partner_line in self.line_ids.filtered(lambda l: l.account_type == 'Receivable' and l.account_id):
            if partner_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': partner_line.account_id.name,
                                   'account_type': partner_line.account_id.account_type})

        for ac_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type not in [
                    'Receivable', 'Current Liabilities'] and l.account_id):
            if ac_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': ac_line.account_id.name,
                                   'account_type': ac_line.account_id.account_type})

        for tax_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type == 'Current Liabilities' and l.account_id):
            if tax_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': tax_line.account_id.name,
                                   'account_type': tax_line.account_id.account_type})

        amt_credit_debit = ''

        print('LineItems',line_items)

        for line in line_items:
            # ch_ledger_name = line.account_id.name
            aml_record = self.env['account.move.line'].search(
                [('account_id.name', '=', line['account_name']), ('move_id', '=', self.id)], limit=1)

            if aml_record and aml_record.partner_id:
                partner_name = aml_record.partner_id.name
            elif self.partner_id:
                partner_name = self.partner_id.name  # Fallback to parent move's partner
            else:
                partner_name = "No Partner"

            print("Resolved Partner Name:", partner_name)  # Debugging
            ch_ledger_name = partner_name \
                if line['account_name'] in ['Debtors' , 'Creditors'] else line['account_name']
            debit = round(sum([l.debit for l in self.line_ids
                               if l.account_id.name == line['account_name']]), 2) or 0
            credit = round(sum([l.credit for l in self.line_ids
                                if l.account_id.name == line['account_name']]), 2) or 0
            # Assuming aml_record has a field `analytic_distribution` which might hold a dictionary or a direct float value
            if aml_record and hasattr(aml_record, 'analytic_distribution'):
                analytic_distribution = aml_record.analytic_distribution if aml_record.analytic_distribution else {}

                analytic_accounts_data = []

                if not analytic_distribution:
                    print("No analytic distribution found for this record.")
                else:
                    for analytic_account_id, distribution_data in analytic_distribution.items():
                        if isinstance(distribution_data, float):  # If it's just a percentage value
                            percentage = distribution_data
                            amount = 0  # Amount is unknown in this case
                        else:
                            percentage = distribution_data.get('percentage', 0)
                            amount = distribution_data.get('amount', 0)

                        # Ensure we fetch only one analytic account at a time
                        # analytic_account = self.env['account.analytic.account'].sudo().search(
                        #     [('id', '=', analytic_account_id)], limit=1)
                        # Convert the string to a list of integers
                        analytic_account_ids = [int(x) for x in analytic_account_id.split(',') if x.strip().isdigit()]

                        # Use 'in' operator to search for any matching ID
                        analytic_account = self.env['account.analytic.account'].sudo().search(
                            [('id', 'in', analytic_account_ids)], limit=1
                        )

                        if analytic_account:
                            analytic_accounts_data.append({
                                'analytic_account': analytic_account,
                                'percentage': percentage,
                                'amount': amount
                            })
                        else:
                            print(f"Warning: Analytic account with ID {analytic_account_id} not found.")

                if not analytic_accounts_data:
                    print("No valid analytic accounts were found or all accounts had incomplete data.")

                # Loop through all fetched analytic account records
                for data in analytic_accounts_data:
                    print(f"Analytic Account: {data['analytic_account'].name}")
                    print(f"Percentage: {data['percentage']}%")
                    print(f"Amount: {data['amount']}")

            else:
                print("No analytic distribution found on this record.")

            # if line['account_type'] == 'asset_receivable':

            # if 'receivable' in (line.get('account_type') or 'asset_receivable' in (line.get('account_type') and debit or '')):
            #     print('if check', line.get('account_type'))
            #     is_deemed_positive = "Yes"
            #     is_party_ledger = "Yes"
            #     is_lastdigit_positive = "Yes"
            #     amount = debit * (-1)
            #     print('if amt', amount)
            # else:
            #     amount = debit * (-1) if debit > 0 else credit
            #     is_deemed_positive = "Yes" if debit > 0 else "No"
            #     is_party_ledger = "No"
            #     is_lastdigit_positive = "Yes" if debit > 0 else "No"

            account_type = line.get('account_type')
            is_deemed_positive = "No"
            is_lastdigit_positive = "No"
            is_party_ledger = "No"
            amount = 0

            # Check if the account is related to a customer (Receivable)
            if account_type in ['receivable', 'asset_receivable']:
                print('Customer-related account:', account_type)

                if debit > 0:
                    # Sales: Customer (Receivable) debited
                    is_deemed_positive = "Yes"
                    is_lastdigit_positive = "Yes"
                    is_party_ledger = "Yes"
                    amount = debit * (-1)
                    print('Sales debit → amount:', amount)
                elif credit > 0:
                    # Payment: Customer (Receivable) credited
                    is_deemed_positive = "No"
                    is_lastdigit_positive = "No"
                    is_party_ledger = "Yes"
                    amount = credit
                    print('Payment credit → amount:', amount)
            else:
                # For non-receivable accounts (e.g., income, expense, bank)
                if debit > 0:
                    is_deemed_positive = "Yes"
                    is_lastdigit_positive = "Yes"
                    amount = debit * (-1)
                else:
                    is_deemed_positive = "No"
                    is_lastdigit_positive = "No"
                    amount = credit

                is_party_ledger = "No"
                print('General ledger → amount:', amount)

            amt_credit_debit = '<ALLLEDGERENTRIES.LIST>\n' \
                               '    <LEDGERNAME>{}</LEDGERNAME>\n' \
                               '    <ISDEEMEDPOSITIVE>{}</ISDEEMEDPOSITIVE>\n' \
                               '    <ISPARTYLEDGER>{}</ISPARTYLEDGER>\n' \
                               '    <ISLASTDEEMEDPOSITIVE>{}</ISLASTDEEMEDPOSITIVE>\n' \
                               '    <AMOUNT>{}</AMOUNT>\n'.format(
                ch_ledger_name, is_deemed_positive, is_party_ledger,
                is_lastdigit_positive, str(amount)
            )

            # Check if analytic data exists
            if analytic_accounts_data:
                amt_credit_debit += '    <CATEGORYALLOCATIONS.LIST>\n'
                amt_credit_debit += '        <CATEGORY>Primary Cost Category</CATEGORY>\n'

                for data in analytic_accounts_data:
                    # print(f"Analytic Account: {data['analytic_account'].name}")
                    percentage = float(data['percentage']) / 100  # Convert percentage to decimal
                    allocated_amount = amount * percentage  # Calculate proportionate amount

                    amt_credit_debit += '        <COSTCENTREALLOCATIONS.LIST>\n' \
                                        '            <NAME>{}</NAME>\n' \
                                        '            <AMOUNT>{}</AMOUNT>\n' \
                                        '        </COSTCENTREALLOCATIONS.LIST>\n'.format(
                        data['analytic_account'].name, str(allocated_amount)
                    )

                amt_credit_debit += '    </CATEGORYALLOCATIONS.LIST>\n'
            else:
                print("No analytic distribution found on this record.")

            amt_credit_debit += '</ALLLEDGERENTRIES.LIST>\n'

            # Append to body_list
            body_list.append(amt_credit_debit)

            # print("things",amt_credit_debit)
        body_xml = ''
        for body in body_list:
            body_xml+=body
            # print("xml",body_xml)
        xml = head_xml + parent_xml + body_xml + xml_foot
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        # self.ndw_select = 'done'
        # print("body",body_list)
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
        except requests.exceptions.RequestException as e:
            print(e, 'eee-----------')
        print('tallydata', pretty_xml)
        # print(response.text)
        if response.status_code==200:
            self.ndw_select = 'done'
        else:
            print("journal post failed", response.text)

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
                    'master_type': 'entry',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': line,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)

            rec = ET.fromstring(response.content)
            line_error = rec.find(".//CREATED")
            if line_error is not None:
                line = line_error.text
            else:
                line = "No LINEERROR element found in the XML"

            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'

                vals = (0, 0, {
                    'master_type': 'entry',
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
        # print("sadfsfdsfdsfdsf", data)
        return data
    def action_journal_entries_alter(self):
        self.ensure_one()
        general_journals = self.filtered(lambda rec: rec.journal_id.type == 'general')
        for rec in general_journals:
            print('Journal Type:', rec.journal_id.type, ' | Move:', rec.name)
        """This method constructs an XML request to synchronize journal entries
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the journal entries and sends the data to the specified URL."""
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        # tally_narration=self.
        if self:
            odoo_currcmp = self.company_id
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        # current_company_id = self.company_id or self.company_ids[0] if self.company_ids else False  # Get the current company ID
        # print('odoocmp', odoo_curcmp)

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', odoo_currcmp.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({odoo_currcmp}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({odoo_currcmp})')

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
                 <VOUCHER REMOTEID="" VCHKEY="" VCHTYPE="Journal" ACTION="Alter" OBJVIEW="Accounting Voucher View">' % (
            tally_currcompany)

        xml_foot = ('<NARRATION>%s</NARRATION>\
                     </VOUCHER>\
                 </TALLYMESSAGE>\
                 </REQUESTDATA>\
                 </IMPORTDATA>\
                 </BODY>\
                 </ENVELOPE>' % (self.narrate))

        if self.date:
            day = '0' + str(self.date.day) if self.date.day < 10 else str(self.date.day)
            month = '0' + str(self.date.month) if self.date.month < 10 else str(self.date.month)
            payment_date = str(self.date.year) + month + day

        parent_xml = ('<DATE>%s</DATE>\
                 <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`" >%s</UDF:UDF_PPTSMJSONMST_ODOOID >\
                 <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                <VOUCHERTYPENAME>%s</VOUCHERTYPENAME>\
                <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
                <UDF:UDF_MNIAPI_ISSAPENTRY>Yes</UDF:UDF_MNIAPI_ISSAPENTRY>\
                <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW> '
                      % (
                          payment_date, str(self.id), str(sync_date), str(self.journal_id.name), str(self.name)))

        body_list = []
        line_items = []
        for partner_line in self.line_ids.filtered(lambda l: l.account_type == 'Receivable' and l.account_id):
            if partner_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': partner_line.account_id.name,
                                   'account_type': partner_line.account_id.account_type})

        for ac_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type not in [
                    'Receivable', 'Current Liabilities'] and l.account_id):
            if ac_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': ac_line.account_id.name,
                                   'account_type': ac_line.account_id.account_type})

        for tax_line in self.line_ids.filtered(
                lambda l: l.account_id.account_type == 'Current Liabilities' and l.account_id):
            if tax_line.account_id.name not in [d['account_name'] for d in line_items]:
                line_items.append({'account_name': tax_line.account_id.name,
                                   'account_type': tax_line.account_id.account_type})

        amt_credit_debit = ''

        print('LineItems', line_items)

        for line in line_items:
            # ch_ledger_name = line.account_id.name
            aml_record = self.env['account.move.line'].search(
                [('account_id.name', '=', line['account_name']), ('move_id', '=', self.id)], limit=1)

            if aml_record and aml_record.partner_id:
                partner_name = aml_record.partner_id.name
            elif self.partner_id:
                partner_name = self.partner_id.name  # Fallback to parent move's partner
            else:
                partner_name = "No Partner"

            print("Resolved Partner Name:", partner_name)  # Debugging
            ch_ledger_name = partner_name \
                if line['account_name'] in ['Debtors', 'Creditors'] else line['account_name']
            debit = round(sum([l.debit for l in self.line_ids
                               if l.account_id.name == line['account_name']]), 2) or 0
            credit = round(sum([l.credit for l in self.line_ids
                                if l.account_id.name == line['account_name']]), 2) or 0
            # Assuming aml_record has a field `analytic_distribution` which might hold a dictionary or a direct float value
            if aml_record and hasattr(aml_record, 'analytic_distribution'):
                analytic_distribution = aml_record.analytic_distribution if aml_record.analytic_distribution else {}

                analytic_accounts_data = []

                if not analytic_distribution:
                    print("No analytic distribution found for this record.")
                else:
                    for analytic_account_id, distribution_data in analytic_distribution.items():
                        if isinstance(distribution_data, float):  # If it's just a percentage value
                            percentage = distribution_data
                            amount = 0  # Amount is unknown in this case
                        else:
                            percentage = distribution_data.get('percentage', 0)
                            amount = distribution_data.get('amount', 0)

                        # Ensure we fetch only one analytic account at a time
                        # analytic_account = self.env['account.analytic.account'].sudo().search(
                        #     [('id', '=', analytic_account_id)], limit=1)
                        # Convert the string to a list of integers
                        analytic_account_ids = [int(x) for x in analytic_account_id.split(',') if x.strip().isdigit()]

                        # Use 'in' operator to search for any matching ID
                        analytic_account = self.env['account.analytic.account'].sudo().search(
                            [('id', 'in', analytic_account_ids)], limit=1
                        )

                        if analytic_account:
                            analytic_accounts_data.append({
                                'analytic_account': analytic_account,
                                'percentage': percentage,
                                'amount': amount
                            })
                        else:
                            print(f"Warning: Analytic account with ID {analytic_account_id} not found.")

                if not analytic_accounts_data:
                    print("No valid analytic accounts were found or all accounts had incomplete data.")

                # Loop through all fetched analytic account records
                for data in analytic_accounts_data:
                    print(f"Analytic Account: {data['analytic_account'].name}")
                    print(f"Percentage: {data['percentage']}%")
                    print(f"Amount: {data['amount']}")

            else:
                print("No analytic distribution found on this record.")

            # if line['account_type'] == 'asset_receivable':
            #     is_deemed_positive = "Yes"
            #     is_party_ledger = "Yes"
            #     is_lastdigit_positive = "Yes"
            #     amount = debit * (-1)
            # else:
            #     amount = debit * (-1) if debit > 0 else credit
            #     is_deemed_positive = "Yes" if debit > 0 else "No"
            #     is_party_ledger = "No"
            #     is_lastdigit_positive = "Yes" if debit > 0 else "No"

            account_type = (line.get('account_type') or '').lower()

            # Extract debit and credit safely
            debit = float(line.get('debit', 0))
            credit = float(line.get('credit', 0))

            if 'receivable' in account_type or 'asset_receivable' in account_type:
                print('if rece', account_type)
                is_deemed_positive = "Yes"
                is_party_ledger = "Yes"
                is_lastdigit_positive = "Yes"
                amount = debit * (-1)
                print('if amt', amount)
            else:
                amount = debit * (-1) if debit > 0 else credit
                is_deemed_positive = "Yes" if debit > 0 else "No"
                is_party_ledger = "No"
                is_lastdigit_positive = "Yes" if debit > 0 else "No"

            amt_credit_debit = '<ALLLEDGERENTRIES.LIST>\n' \
                               '    <LEDGERNAME>{}</LEDGERNAME>\n' \
                               '    <ISDEEMEDPOSITIVE>{}</ISDEEMEDPOSITIVE>\n' \
                               '    <ISPARTYLEDGER>{}</ISPARTYLEDGER>\n' \
                               '    <ISLASTDEEMEDPOSITIVE>{}</ISLASTDEEMEDPOSITIVE>\n' \
                               '    <AMOUNT>{}</AMOUNT>\n'.format(
                ch_ledger_name, is_deemed_positive, is_party_ledger,
                is_lastdigit_positive, str(amount)
            )

            # Check if analytic data exists
            if analytic_accounts_data:
                amt_credit_debit += '    <CATEGORYALLOCATIONS.LIST>\n'
                amt_credit_debit += '        <CATEGORY>Primary Cost Category</CATEGORY>\n'

                for data in analytic_accounts_data:
                    print(f"Analytic Account: {data['analytic_account'].name}")
                    percentage = float(data['percentage']) / 100  # Convert percentage to decimal
                    allocated_amount = amount * percentage  # Calculate proportionate amount

                    amt_credit_debit += '        <COSTCENTREALLOCATIONS.LIST>\n' \
                                        '            <NAME>{}</NAME>\n' \
                                        '            <AMOUNT>{}</AMOUNT>\n' \
                                        '        </COSTCENTREALLOCATIONS.LIST>\n'.format(
                        data['analytic_account'].name, str(allocated_amount)
                    )

                amt_credit_debit += '    </CATEGORYALLOCATIONS.LIST>\n'
            else:
                print("No analytic distribution found on this record.")

            amt_credit_debit += '</ALLLEDGERENTRIES.LIST>\n'

            # Append to body_list
            body_list.append(amt_credit_debit)

            print("things", amt_credit_debit)
        body_xml = ''
        for body in body_list:
            body_xml += body
            print("xml", body_xml)
        # xml = head_xml + parent_xml + body_xml + xml_foot
        xml = head_xml+ parent_xml + xml_foot
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        # self.ndw_select = 'done'
        print("body", body_list)
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
        except requests.exceptions.RequestException as e:
            print(e, 'eee-----------')

        print(response)
        print('Tally Status code', response.status_code)
        if response.status_code == 200:
            self.ndw_select = 'done'
        else:
            print("journal post failed", response.text)

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
                    'master_type': 'entry',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': line,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)

            rec = ET.fromstring(response.content)
            line_error = rec.find(".//CREATED")
            if line_error is not None:
                line = line_error.text
            else:
                line = "No LINEERROR element found in the XML"

            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'

                vals = (0, 0, {
                    'master_type': 'entry',
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
        print("sadfsfdsfdsfdsf", data)
        return data
