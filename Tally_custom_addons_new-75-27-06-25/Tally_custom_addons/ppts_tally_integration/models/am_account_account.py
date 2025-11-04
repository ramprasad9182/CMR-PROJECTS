# -*- coding: utf-8 -*-
"""Description: This module contains functionalities for interacting with XML,
 Odoo, and web scraping."""
import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import api, models
import requests
from bs4 import BeautifulSoup
import pytz
import time


class Account(models.Model):
    _inherit = "account.account"

    # @api.onchange('name', 'tally_id', 'company_id', 'code', 'account_type', 'group_id')
    # def onchange_ndw_select(self):
    #     self.write({'ndw_select':'write'})
    # def __init__(self, env, ids, prefetch_ids):
    #     super().__init__(env, ids, prefetch_ids)
    #     self.group_id = None
    #     self.id = None

    @api.model
    def create(self, vals):
        vals['ndw_select'] = 'new'
        return super(Account, self).create(vals)

    def write(self, vals):
        for rec in self:
            if 'name' in vals:
                rec.old_name = rec.name  # Save old name before changing

            # If record is already synced, and something is being updated
            if rec.ndw_select == 'done':
                vals['ndw_select'] = 'write'
        return super(Account, self).write(vals)


    def action_sync_coa(self):

        """Sync Chart of Accounts with an external system.

                This method is responsible for synchronizing the Chart of Accounts
                with an external system, likely using Tally ERP. It constructs an XML
                request and sends it to the specified URL to import data into Tally.
                """
        # if not accounts:
        #     accounts = self
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        # tally_curid   = self.env
        if self:
            odoo_currcmp = self.company_ids[0] if self.company_ids else False
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_ids[0] if self.company_ids else False   # Get the current company ID
        # print('odoocmp', odoo_curcmp)

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', odoo_currcmp.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({current_company_id}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({current_company_id})')

        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        ist_timez=pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        print("System time:", time.tzname)
        print("Local time:", datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        print("synctime", sync_date_str)
        # for rec in accounts:
        head_xml = '<ENVELOPE>\
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
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">' % (tally_currcompany)
        xml_foot = '</TALLYMESSAGE>\
                            </REQUESTDATA>\
                            </IMPORTDATA>\
                            </BODY>\
                            </ENVELOPE>'

        ledger_name = self.name
        # created_date = str(self.create_date.date())
        key_type =''
        parent_name=''

        if self.group_id:
            parent_name = self.group_id.name

        else:

            if self.account_type == 'asset_receivable':
                key_type = 'Sundry Debtors'
            elif self.account_type == 'asset_cash':
                key_type = 'Cash in Hands'
            elif self.account_type == 'asset_current':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_non_current':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_prepayments':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_fixed':
                key_type = 'Fixed Assets'
            elif self.account_type == 'liability_payable':
                key_type = 'Sundry Creditors'
            elif self.account_type == 'liability_credit_card':
                key_type = 'Current Liabilities'
            elif self.account_type == 'liability_current':
                key_type = 'Current Liabilities'
            elif self.account_type == 'liability_non_current':
                key_type = 'Current Liabilities'
            elif self.account_type == 'equity':
                key_type = 'Capital Accounts'
            elif self.account_type == 'equity_unaffected':
                key_type = 'Profit $ Loss or Primary'
            elif self.account_type == 'income':
                key_type = 'InDirect Income'
            elif self.account_type == 'income_other':
                key_type = 'Indirect Income'
            elif self.account_type == 'expense':
                key_type = 'Indirect Expenses'
            elif self.account_type == 'expense_depreciation':
                key_type = 'Direct Expenses'
            elif self.account_type == 'expense_direct_cost':
                key_type = 'Purchase Accounts'
            elif self.account_type == 'off_balance':
                key_type = 'Primary'

        if key_type:
            coa_group = self.env['account.group'].create({'name': key_type})

            parent_name = coa_group.name

        old_coa_name = self.old_name
        coa_map = str(dict(self._fields['account_type'].selection).get(self.account_type))
        print('coa_map', coa_map)

        tax_type = str(dict(self._fields['types_tax'].selection).get(self.types_tax))\
            if self.types_tax else ''
        gst_type = str(dict(self._fields['types_gst'].selection).get(self.types_gst)) \
            if self.types_gst else ''
        print('taxtype', tax_type)
        print('gst_type', gst_type)
        body_xml = ''

        if self.account_type == 'Current Liabilities' or self.account_type == 'Current Assets':
            body_xml = ('<LEDGER NAME="%s" RESERVEDNAME="">\
                    <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                    <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                    </OLDAUDITENTRYIDS.LIST>\
                    <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                    <PARENT>%s</PARENT>\
                    <TAXTYPE>%s</TAXTYPE>\
                    <GSTDUTYHEAD>%s</GSTDUTYHEAD>\
                    <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                    <ISBILLWISEON>No</ISBILLWISEON>\
                    <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                    <ISINTERESTON>No</ISINTERESTON>\
                    <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                    <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                    <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                      <ASORIGINAL>Yes</ASORIGINAL>\
                    <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                    <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                    <FORPAYROLL>No</FORPAYROLL>\
                    <ISABCENABLED>No</ISABCENABLED>\
                    <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                    <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                    <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                    <USEFORVAT>No</USEFORVAT>\
                    <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                    <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                    <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                    <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                    <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                    <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                    <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                    <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                    <ISTRANSPORTER>No</ISTRANSPORTER>\
                    <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                    <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                    <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                    <USEFORGRATUITY>No</USEFORGRATUITY>\
                    <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                    <FORSERVICETAX>No</FORSERVICETAX>\
                    <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                    <ISEXEMPTED>No</ISEXEMPTED>\
                    <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                    <ISSTXPARTY>No</ISSTXPARTY>\
                    <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                    <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                    <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                    <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                    <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                    <ISSEZPARTY>No</ISSEZPARTY>\
                    <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                    <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                    <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                    <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                    <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                    <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                    <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                    <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                    <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                    <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                    <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                    <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                    <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                    <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                    <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                    <ISBATCHENABLED>No</ISBATCHENABLED>\
                    <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                    <HASEDDCITY>No</HASEDDCITY>\
                    <HASECHEQUECITY>No</HASECHEQUECITY>\
                    <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                    <HASCLIENTCODE>No</HASCLIENTCODE>\
                    <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                    <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                    <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                    <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                    <ISSCBUAE>No</ISSCBUAE>\
                    <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                    <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                    <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                    <AUDITED>No</AUDITED>\
                    <SORTPOSITION> 1000</SORTPOSITION>\
                    <LANGUAGENAME.LIST>\
                    <NAME.LIST TYPE="String">\
                        <NAME>%s</NAME>\
                    </NAME.LIST>\
                    <LANGUAGEID> 1033</LANGUAGEID>\
                    </LANGUAGENAME.LIST>\
                    </LEDGER>') % (ledger_name, str(self.id), sync_date_str, parent_name,
                                   tax_type, gst_type,
                                   ledger_name if self.group_id.name else coa_map )

        if self.account_type == 'Bank and Cash':
            body_xml = '<LEDGER NAME="%s" RESERVEDNAME="">\
                            <ADDRESS.LIST TYPE="String">\
                            <ADDRESS>%s</ADDRESS>\
                            <ADDRESS>%s</ADDRESS>\
                            </ADDRESS.LIST>\
                            <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                            <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                            <MAILINGNAME.LIST TYPE="String">\
                            <MAILINGNAME>%s</MAILINGNAME>\
                            </MAILINGNAME.LIST>\
                            <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                            </OLDAUDITENTRYIDS.LIST>\
                            <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                            <COUNTRYNAME>%s</COUNTRYNAME>\
                            <PARENT>%s</PARENT>\
                            <IFSCODE>%s</IFSCODE>\
                            <TAXTYPE>Others</TAXTYPE>\
                            <BANKDETAILS>%s</BANKDETAILS>\
                            <BANKBRANCHNAME>%s</BANKBRANCHNAME>\
                            <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                            <PARTYGSTIN>GSTIN 33</PARTYGSTIN>\
                            <BANKACCHOLDERNAME>%s</BANKACCHOLDERNAME>\
                            <LEDSTATENAME>%s</LEDSTATENAME>\
                            <ISBILLWISEON>No</ISBILLWISEON>\
                            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                            <ISINTERESTON>No</ISINTERESTON>\
                            <ASORIGINAL>Yes</ASORIGINAL>\
                            <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                            <FORPAYROLL>No</FORPAYROLL>\
                            <ISABCENABLED>No</ISABCENABLED>\
                            <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                            <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                            <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                            <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                            <USEFORVAT>No</USEFORVAT>\
                            <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                            <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                            <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                            <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                            <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                            <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                            <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                            <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                            <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                            <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                            <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                            <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                            <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                            <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                            <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                            <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                            <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                            <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                            <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                            <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                            <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                            <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                            <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                            <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                            <ISTRANSPORTER>No</ISTRANSPORTER>\
                            <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                            <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                            <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                            <USEFORGRATUITY>No</USEFORGRATUITY>\
                            <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                            <FORSERVICETAX>No</FORSERVICETAX>\
                            <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                            <ISEXEMPTED>No</ISEXEMPTED>\
                            <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                            <ISSTXPARTY>No</ISSTXPARTY>\
                            <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                            <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                            <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                            <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                            <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                            <ISSEZPARTY>No</ISSEZPARTY>\
                            <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                            <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                            <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                            <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                            <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                            <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                            <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                            <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                            <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                            <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                            <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                            <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                            <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                            <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                            <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                            <ISBATCHENABLED>No</ISBATCHENABLED>\
                            <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                            <HASEDDCITY>No</HASEDDCITY>\
                            <HASECHEQUECITY>No</HASECHEQUECITY>\
                            <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                            <HASCLIENTCODE>No</HASCLIENTCODE>\
                            <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                            <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                            <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                            <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                            <ISSCBUAE>No</ISSCBUAE>\
                            <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                            <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                            <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                            <AUDITED>No</AUDITED>\
                            <SORTPOSITION> 1000</SORTPOSITION>\
                            <LANGUAGENAME.LIST>\
                            <NAME.LIST TYPE="String">\
                                <NAME>%s</NAME>\
                            </NAME.LIST>\
                            <LANGUAGEID> 1033</LANGUAGEID>\
                            </LANGUAGENAME.LIST>\
                            </LEDGER>\
                            </TALLYMESSAGE>\
                            <LEDGER NAME="%s" RESERVEDNAME="">\
                            <ADDRESS.LIST TYPE="String">\
                            <ADDRESS>%s</ADDRESS>\
                            <ADDRESS>%s</ADDRESS>\
                            </ADDRESS.LIST>\
                            <MAILINGNAME.LIST TYPE="String">\
                            <MAILINGNAME>%s</MAILINGNAME>\
                            </MAILINGNAME.LIST>\
                            <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                            </OLDAUDITENTRYIDS.LIST>\
                            <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                            <COUNTRYNAME>%s</COUNTRYNAME>\
                            <PARENT>%s</PARENT>\
                            <IFSCODE>%s</IFSCODE>\
                            <TAXTYPE>Others</TAXTYPE>\
                            <BANKDETAILS>%s</BANKDETAILS>\
                            <BANKBRANCHNAME>%s</BANKBRANCHNAME>\
                            <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                            <PARTYGSTIN>GSTIN 33</PARTYGSTIN>\
                            <BANKACCHOLDERNAME>%s</BANKACCHOLDERNAME>\
                            <LEDSTATENAME>%s</LEDSTATENAME>\
                            <ISBILLWISEON>No</ISBILLWISEON>\
                            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                            <ISINTERESTON>No</ISINTERESTON>\
                            <ASORIGINAL>Yes</ASORIGINAL>\
                            <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                            <FORPAYROLL>No</FORPAYROLL>\
                            <ISABCENABLED>No</ISABCENABLED>\
                            <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                            <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                            <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                            <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                            <USEFORVAT>No</USEFORVAT>\
                            <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                            <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                            <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                            <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                            <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                            <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                            <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                            <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                            <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                            <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                            <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                            <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                            <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                            <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                            <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                            <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                            <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                            <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                            <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                            <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                            <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                            <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                            <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                            <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                            <ISTRANSPORTER>No</ISTRANSPORTER>\
                            <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                            <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                            <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                            <USEFORGRATUITY>No</USEFORGRATUITY>\
                            <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                            <FORSERVICETAX>No</FORSERVICETAX>\
                            <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                            <ISEXEMPTED>No</ISEXEMPTED>\
                            <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                            <ISSTXPARTY>No</ISSTXPARTY>\
                            <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                            <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                            <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                            <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                            <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                            <ISSEZPARTY>No</ISSEZPARTY>\
                            <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                            <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                            <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                            <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                            <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                            <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                            <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                            <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                            <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                            <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                            <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                            <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                            <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                            <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                            <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                            <ISBATCHENABLED>No</ISBATCHENABLED>\
                            <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                            <HASEDDCITY>No</HASEDDCITY>\
                            <HASECHEQUECITY>No</HASECHEQUECITY>\
                            <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                            <HASCLIENTCODE>No</HASCLIENTCODE>\
                            <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                            <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                            <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                            <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                            <ISSCBUAE>No</ISSCBUAE>\
                            <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                            <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                            <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                            <AUDITED>No</AUDITED>\
                            <SORTPOSITION> 1000</SORTPOSITION>\
                            <LANGUAGENAME.LIST>\
                            <NAME.LIST TYPE="String">\
                                <NAME>%s</NAME>\
                            </NAME.LIST>\
                            <LANGUAGEID> 1033</LANGUAGEID>\
                            </LANGUAGENAME.LIST>\
                            </LEDGER>'

        if self.account_type == 'Expenses':
            body_xml = '<LEDGER NAME="%s" RESERVEDNAME="">\
                        <MAILINGNAME.LIST TYPE="String">\
                        <MAILINGNAME>%s</MAILINGNAME>\
                        </MAILINGNAME.LIST>\
                        <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                        </OLDAUDITENTRYIDS.LIST>\
                        <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                        <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                        <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                        <COUNTRYNAME>India</COUNTRYNAME>\
                        <PARENT>%s</PARENT>\
                        <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                        <TAXTYPE>Others</TAXTYPE>\
                        <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>\
                        <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                        <LEDSTATENAME>Tamil Nadu</LEDSTATENAME>\
                        <VATAPPLICABLE>&#4; Not Applicable</VATAPPLICABLE>\
                        <ISBILLWISEON>No</ISBILLWISEON>\
                        <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                        <ISINTERESTON>No</ISINTERESTON>\
                        <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                        <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                        <ASORIGINAL>Yes</ASORIGINAL>\
                        <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                        <FORPAYROLL>No</FORPAYROLL>\
                        <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                        <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                        <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                        <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                        <USEFORVAT>No</USEFORVAT>\
                        <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                        <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                        <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                        <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                        <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                        <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                        <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                        <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                        <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                        <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                        <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                        <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                        <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                        <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                        <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                        <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                        <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                        <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                        <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                        <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                        <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                        <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                        <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                        <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                        <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                        <USEFORGRATUITY>No</USEFORGRATUITY>\
                        <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                        <FORSERVICETAX>No</FORSERVICETAX>\
                        <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                        <ISEXEMPTED>No</ISEXEMPTED>\
                        <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                        <ISSTXPARTY>No</ISSTXPARTY>\
                        <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                        <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                        <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                        <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                        <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                        <ISSEZPARTY>No</ISSEZPARTY>\
                        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                        <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                        <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                        <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                        <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                        <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                        <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                        <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                        <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                        <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                        <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                        <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                        <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                        <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                        <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                        <ISBATCHENABLED>No</ISBATCHENABLED>\
                        <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                        <HASEDDCITY>No</HASEDDCITY>\
                        <HASECHEQUECITY>No</HASECHEQUECITY>\
                        <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                        <HASCLIENTCODE>No</HASCLIENTCODE>\
                        <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                        <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                        <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                        <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                        <ISSCBUAE>No</ISSCBUAE>\
                        <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                        <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                        <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                        <AUDITED>No</AUDITED>\
                        <SORTPOSITION> 1000</SORTPOSITION>\
                        <LANGUAGENAME.LIST>\
                        <NAME.LIST TYPE="String">\
                            <NAME>%s</NAME>\
                        </NAME.LIST>\
                        <LANGUAGEID> 1033</LANGUAGEID>\
                        </LANGUAGENAME.LIST>\
                        </LEDGER>' % (ledger_name, str(self.id), sync_date_str, ledger_name,
                                      parent_name, ledger_name if self.group_id.name else coa_map)

        if self.account_type == 'Cost of Revenue':
            body_xml = '<LEDGER NAME="%s" RESERVEDNAME="%s">\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <VATAPPLICABLE>&#4; Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>Yes</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                        </LEDGER>' % (ledger_name, str(self.id), parent_name,
                                      ledger_name if self.group_id.name else coa_map)

        if self.account_type == 'Income':
            body_xml = '<LEDGER NAME="%s" RESERVEDNAME="">\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <VATAPPLICABLE>&#4; Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>Yes</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                            </LEDGER>' % (ledger_name, str(self.id), sync_date_str, parent_name,
                                          ledger_name if self.group_id.name else coa_map)

        else:
            body_xml =' '
            body_xml = '<LEDGER NAME="%s" RESERVEDNAME="">\
                                <MAILINGNAME.LIST TYPE="String">\
                                <MAILINGNAME>%s</MAILINGNAME>\
                                </MAILINGNAME.LIST>\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <COUNTRYNAME>India</COUNTRYNAME>\
                                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <LEDSTATENAME>Tamil Nadu</LEDSTATENAME>\
                                <VATAPPLICABLE>&#4; Not Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                        </LEDGER>' % (ledger_name, ledger_name, str(self.id),
                                      sync_date_str, parent_name, ledger_name )

        xml = head_xml + body_xml + xml_foot
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'),timeout=60)
        except requests.exceptions.RequestException as e:
            print(e, "eeee--------")

        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            # error_log=''
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                # self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'coa',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': error_log,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//CREATED")
            # create_log = ''
            if line_error is not None:
                create_log = line_error.text  # Assign the extracted error message
            else:
                create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'coa',
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
        coa_masterid_req = f"""<ENVELOPE>
                                           <HEADER>
                                               <VERSION>1</VERSION>
                                               <TALLYREQUEST>Export</TALLYREQUEST>
                                               <TYPE>Collection</TYPE>
                                               <ID>TestLedgerList2</ID>
                                           </HEADER>
                                           <BODY>
                                               <DESC>
                                                   <STATICVARIABLES>
                                                       <SVCURRENTCOMPANY>{(tally_currcompany)}</SVCURRENTCOMPANY>
                                                   </STATICVARIABLES>
                                                   <TDL>
                                                       <TDLMESSAGE>
                                                           <COLLECTION NAME='TestLedgerList2' ISMSTDEPTYPE="Yes">
                                                               <TYPE>Ledger</TYPE >
                                                               <FETCH>Name, MasterId</FETCH>
                                                               <FILTER>FLTR_MNIAPI_GrpMID</FILTER>
                                                           </COLLECTION>
                                                           <SYSTEM TYPE="Formula" NAME="FLTR_MNIAPI_GrpMID">$Name={self.name}</SYSTEM>
                                                       </TDLMESSAGE>
                                                   </TDL>
                                               </DESC>
                                           </BODY>
                                       </ENVELOPE>"""

        headers = {'Content-Type': 'text/xml'}
        response = requests.post(url, data=coa_masterid_req.encode('utf-8'), headers=headers)
        print('tallyID_resp', response.text)
        tally_masterid_result = response.text.strip()
        soup = BeautifulSoup(tally_masterid_result, 'xml')
        print('idsoup', soup)
        tallyid_val = ""
        try:
            root = ET.fromstring(response.text.strip())
            master_id_el = root.find('.//MASTERID')
            if master_id_el is not None:
                print("ElementTree MASTERID:", master_id_el.text.strip())
                tallyid_val = int(master_id_el.text.strip())
                self.tally_id = tallyid_val
            else:
                print("ElementTree: MASTERID not found")
        except Exception as e:
            print("ElementTree error:", e)
        self.tally_id = tallyid_val
        return data

    def action_sync_coa_alter(self):

        """Sync Chart of Accounts with an external system.

                This method is responsible for synchronizing the Chart of Accounts
                with an external system, likely using Tally ERP. It constructs an XML
                request and sends it to the specified URL to import data into Tally.
                """
        # if not accounts:
        #     accounts = self
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        # tally_curid   = self.env
        if self:
            odoo_currcmp = self.company_ids[0] if self.company_ids else False
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_ids[0] if self.company_ids else False  # Get the current company ID
        # print('odoocmp', odoo_curcmp)
        old_account_name = self.old_name

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', odoo_currcmp.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({current_company_id}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({current_company_id})')

        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        print("System time:", time.tzname)
        print("Local time:", datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        print("synctime", sync_date_str)
        # for rec in accounts:
        head_xml = '<ENVELOPE>\
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
                        <TALLYMESSAGE xmlns:UDF="TallyUDF">' % (tally_currcompany)
        xml_foot = '</TALLYMESSAGE>\
                            </REQUESTDATA>\
                            </IMPORTDATA>\
                            </BODY>\
                            </ENVELOPE>'

        ledger_name = self.name
        # created_date = str(self.create_date.date())
        key_type = ''
        parent_name = ''

        if self.group_id:
            parent_name = self.group_id.name

        else:

            if self.account_type == 'asset_receivable':
                key_type = 'Sundry Debtors'
            elif self.account_type == 'asset_cash':
                key_type = 'Cash in Hands'
            elif self.account_type == 'asset_current':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_non_current':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_prepayments':
                key_type = 'Current Assets'
            elif self.account_type == 'asset_fixed':
                key_type = 'Fixed Assets'
            elif self.account_type == 'liability_payable':
                key_type = 'Sundry Creditors'
            elif self.account_type == 'liability_credit_card':
                key_type = 'Current Liabilities'
            elif self.account_type == 'liability_current':
                key_type = 'Current Liabilities'
            elif self.account_type == 'liability_non_current':
                key_type = 'Current Liabilities'
            elif self.account_type == 'equity':
                key_type = 'Capital Accounts'
            elif self.account_type == 'equity_unaffected':
                key_type = 'Profit $ Loss or Primary'
            elif self.account_type == 'income':
                key_type = 'InDirect Income'
            elif self.account_type == 'income_other':
                key_type = 'Indirect Income'
            elif self.account_type == 'expense':
                key_type = 'Indirect Expenses'
            elif self.account_type == 'expense_depreciation':
                key_type = 'Direct Expenses'
            elif self.account_type == 'expense_direct_cost':
                key_type = 'Purchase Accounts'
            elif self.account_type == 'off_balance':
                key_type = 'Primary'

        if key_type:
            coa_group = self.env['account.group'].create({'name': key_type})

            parent_name = coa_group.name

        coa_map = str(dict(self._fields['account_type'].selection).get(self.account_type))
        print('coa_map', coa_map)

        tax_type = str(dict(self._fields['types_tax'].selection).get(self.types_tax)) \
            if self.types_tax else ''
        gst_type = str(dict(self._fields['types_gst'].selection).get(self.types_gst)) \
            if self.types_gst else ''
        print('taxtype', tax_type)
        print('gst_type', gst_type)
        body_xml = ''
        coa_masterid = self.tally_id
        if self.account_type == 'Current Liabilities' or self.account_type == 'Current Assets':
            altermain_body_xml = ('<LEDGER NAME="%s" MASTERID="%s" ACTION="Alter" RESERVEDNAME="">\
                    <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                    <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                    </OLDAUDITENTRYIDS.LIST>\
                    <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                    <PARENT>%s</PARENT>\
                    <TAXTYPE>%s</TAXTYPE>\
                    <GSTDUTYHEAD>%s</GSTDUTYHEAD>\
                    <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                    <ISBILLWISEON>No</ISBILLWISEON>\
                    <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                    <ISINTERESTON>No</ISINTERESTON>\
                    <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                    <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                    <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                      <ASORIGINAL>Yes</ASORIGINAL>\
                    <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                    <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                    <FORPAYROLL>No</FORPAYROLL>\
                    <ISABCENABLED>No</ISABCENABLED>\
                    <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                    <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                    <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                    <USEFORVAT>No</USEFORVAT>\
                    <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                    <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                    <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                    <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                    <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                    <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                    <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                    <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                    <ISTRANSPORTER>No</ISTRANSPORTER>\
                    <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                    <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                    <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                    <USEFORGRATUITY>No</USEFORGRATUITY>\
                    <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                    <FORSERVICETAX>No</FORSERVICETAX>\
                    <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                    <ISEXEMPTED>No</ISEXEMPTED>\
                    <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                    <ISSTXPARTY>No</ISSTXPARTY>\
                    <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                    <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                    <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                    <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                    <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                    <ISSEZPARTY>No</ISSEZPARTY>\
                    <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                    <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                    <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                    <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                    <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                    <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                    <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                    <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                    <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                    <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                    <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                    <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                    <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                    <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                    <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                    <ISBATCHENABLED>No</ISBATCHENABLED>\
                    <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                    <HASEDDCITY>No</HASEDDCITY>\
                    <HASECHEQUECITY>No</HASECHEQUECITY>\
                    <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                    <HASCLIENTCODE>No</HASCLIENTCODE>\
                    <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                    <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                    <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                    <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                    <ISSCBUAE>No</ISSCBUAE>\
                    <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                    <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                    <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                    <AUDITED>No</AUDITED>\
                    <SORTPOSITION> 1000</SORTPOSITION>\
                    <LANGUAGENAME.LIST>\
                    <NAME.LIST TYPE="String">\
                        <NAME>%s</NAME>\
                    </NAME.LIST>\
                    <LANGUAGEID> 1033</LANGUAGEID>\
                    </LANGUAGENAME.LIST>\
                    </LEDGER>') % (old_account_name, coa_masterid, str(self.id), sync_date_str, parent_name,
                                   tax_type, gst_type,
                                   ledger_name if self.group_id.name else coa_map)

        if self.account_type == 'Bank and Cash':
            alter_body_xml = '<LEDGER NAME="%s" RESERVEDNAME="">\
                            <ADDRESS.LIST TYPE="String">\
                            <ADDRESS>%s</ADDRESS>\
                            <ADDRESS>%s</ADDRESS>\
                            </ADDRESS.LIST>\
                            <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                            <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                            <MAILINGNAME.LIST TYPE="String">\
                            <MAILINGNAME>%s</MAILINGNAME>\
                            </MAILINGNAME.LIST>\
                            <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                            </OLDAUDITENTRYIDS.LIST>\
                            <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                            <COUNTRYNAME>%s</COUNTRYNAME>\
                            <PARENT>%s</PARENT>\
                            <IFSCODE>%s</IFSCODE>\
                            <TAXTYPE>Others</TAXTYPE>\
                            <BANKDETAILS>%s</BANKDETAILS>\
                            <BANKBRANCHNAME>%s</BANKBRANCHNAME>\
                            <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                            <PARTYGSTIN>GSTIN 33</PARTYGSTIN>\
                            <BANKACCHOLDERNAME>%s</BANKACCHOLDERNAME>\
                            <LEDSTATENAME>%s</LEDSTATENAME>\
                            <ISBILLWISEON>No</ISBILLWISEON>\
                            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                            <ISINTERESTON>No</ISINTERESTON>\
                            <ASORIGINAL>Yes</ASORIGINAL>\
                            <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                            <FORPAYROLL>No</FORPAYROLL>\
                            <ISABCENABLED>No</ISABCENABLED>\
                            <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                            <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                            <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                            <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                            <USEFORVAT>No</USEFORVAT>\
                            <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                            <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                            <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                            <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                            <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                            <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                            <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                            <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                            <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                            <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                            <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                            <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                            <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                            <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                            <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                            <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                            <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                            <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                            <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                            <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                            <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                            <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                            <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                            <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                            <ISTRANSPORTER>No</ISTRANSPORTER>\
                            <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                            <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                            <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                            <USEFORGRATUITY>No</USEFORGRATUITY>\
                            <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                            <FORSERVICETAX>No</FORSERVICETAX>\
                            <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                            <ISEXEMPTED>No</ISEXEMPTED>\
                            <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                            <ISSTXPARTY>No</ISSTXPARTY>\
                            <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                            <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                            <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                            <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                            <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                            <ISSEZPARTY>No</ISSEZPARTY>\
                            <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                            <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                            <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                            <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                            <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                            <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                            <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                            <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                            <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                            <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                            <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                            <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                            <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                            <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                            <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                            <ISBATCHENABLED>No</ISBATCHENABLED>\
                            <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                            <HASEDDCITY>No</HASEDDCITY>\
                            <HASECHEQUECITY>No</HASECHEQUECITY>\
                            <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                            <HASCLIENTCODE>No</HASCLIENTCODE>\
                            <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                            <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                            <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                            <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                            <ISSCBUAE>No</ISSCBUAE>\
                            <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                            <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                            <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                            <AUDITED>No</AUDITED>\
                            <SORTPOSITION> 1000</SORTPOSITION>\
                            <LANGUAGENAME.LIST>\
                            <NAME.LIST TYPE="String">\
                                <NAME>%s</NAME>\
                            </NAME.LIST>\
                            <LANGUAGEID> 1033</LANGUAGEID>\
                            </LANGUAGENAME.LIST>\
                            </LEDGER>\
                            </TALLYMESSAGE>\
                            <LEDGER NAME="%s" RESERVEDNAME="">\
                            <ADDRESS.LIST TYPE="String">\
                            <ADDRESS>%s</ADDRESS>\
                            <ADDRESS>%s</ADDRESS>\
                            </ADDRESS.LIST>\
                            <MAILINGNAME.LIST TYPE="String">\
                            <MAILINGNAME>%s</MAILINGNAME>\
                            </MAILINGNAME.LIST>\
                            <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                            </OLDAUDITENTRYIDS.LIST>\
                            <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                            <COUNTRYNAME>%s</COUNTRYNAME>\
                            <PARENT>%s</PARENT>\
                            <IFSCODE>%s</IFSCODE>\
                            <TAXTYPE>Others</TAXTYPE>\
                            <BANKDETAILS>%s</BANKDETAILS>\
                            <BANKBRANCHNAME>%s</BANKBRANCHNAME>\
                            <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                            <PARTYGSTIN>GSTIN 33</PARTYGSTIN>\
                            <BANKACCHOLDERNAME>%s</BANKACCHOLDERNAME>\
                            <LEDSTATENAME>%s</LEDSTATENAME>\
                            <ISBILLWISEON>No</ISBILLWISEON>\
                            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                            <ISINTERESTON>No</ISINTERESTON>\
                            <ASORIGINAL>Yes</ASORIGINAL>\
                            <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                            <FORPAYROLL>No</FORPAYROLL>\
                            <ISABCENABLED>No</ISABCENABLED>\
                            <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                            <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                            <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                            <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                            <USEFORVAT>No</USEFORVAT>\
                            <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                            <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                            <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                            <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                            <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                            <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                            <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                            <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                            <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                            <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                            <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                            <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                            <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                            <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                            <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                            <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                            <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                            <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                            <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                            <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                            <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                            <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                            <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                            <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                            <ISTRANSPORTER>No</ISTRANSPORTER>\
                            <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                            <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                            <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                            <USEFORGRATUITY>No</USEFORGRATUITY>\
                            <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                            <FORSERVICETAX>No</FORSERVICETAX>\
                            <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                            <ISEXEMPTED>No</ISEXEMPTED>\
                            <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                            <ISSTXPARTY>No</ISSTXPARTY>\
                            <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                            <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                            <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                            <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                            <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                            <ISSEZPARTY>No</ISSEZPARTY>\
                            <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                            <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                            <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                            <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                            <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                            <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                            <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                            <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                            <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                            <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                            <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                            <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                            <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                            <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                            <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                            <ISBATCHENABLED>No</ISBATCHENABLED>\
                            <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                            <HASEDDCITY>No</HASEDDCITY>\
                            <HASECHEQUECITY>No</HASECHEQUECITY>\
                            <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                            <HASCLIENTCODE>No</HASCLIENTCODE>\
                            <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                            <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                            <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                            <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                            <ISSCBUAE>No</ISSCBUAE>\
                            <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                            <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                            <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                            <AUDITED>No</AUDITED>\
                            <SORTPOSITION> 1000</SORTPOSITION>\
                            <LANGUAGENAME.LIST>\
                            <NAME.LIST TYPE="String">\
                                <NAME>%s</NAME>\
                            </NAME.LIST>\
                            <LANGUAGEID> 1033</LANGUAGEID>\
                            </LANGUAGENAME.LIST>\
                            </LEDGER>'

        if self.account_type == 'Expenses':
            body_xml = '<LEDGER NAME="%s" MASTERID="%s" RESERVEDNAME="" ACTION="Alter">\
                        <MAILINGNAME.LIST TYPE="String">\
                        <MAILINGNAME>%s</MAILINGNAME>\
                        </MAILINGNAME.LIST>\
                        <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                        <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                        </OLDAUDITENTRYIDS.LIST>\
                        <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                        <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                        <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                        <COUNTRYNAME>India</COUNTRYNAME>\
                        <PARENT>%s</PARENT>\
                        <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                        <TAXTYPE>Others</TAXTYPE>\
                        <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>\
                        <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                        <LEDSTATENAME>Tamil Nadu</LEDSTATENAME>\
                        <VATAPPLICABLE>&#4; Not Applicable</VATAPPLICABLE>\
                        <ISBILLWISEON>No</ISBILLWISEON>\
                        <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                        <ISINTERESTON>No</ISINTERESTON>\
                        <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                        <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                        <ASORIGINAL>Yes</ASORIGINAL>\
                        <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                        <FORPAYROLL>No</FORPAYROLL>\
                        <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                        <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                        <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                        <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                        <USEFORVAT>No</USEFORVAT>\
                        <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                        <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                        <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                        <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                        <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                        <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                        <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                        <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                        <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                        <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                        <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                        <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                        <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                        <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                        <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                        <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                        <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                        <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                        <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                        <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                        <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                        <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                        <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                        <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                        <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                        <USEFORGRATUITY>No</USEFORGRATUITY>\
                        <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                        <FORSERVICETAX>No</FORSERVICETAX>\
                        <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                        <ISEXEMPTED>No</ISEXEMPTED>\
                        <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                        <ISSTXPARTY>No</ISSTXPARTY>\
                        <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                        <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                        <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                        <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                        <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                        <ISSEZPARTY>No</ISSEZPARTY>\
                        <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                        <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                        <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                        <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                        <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                        <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                        <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                        <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                        <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                        <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                        <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                        <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                        <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                        <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                        <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                        <ISBATCHENABLED>No</ISBATCHENABLED>\
                        <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                        <HASEDDCITY>No</HASEDDCITY>\
                        <HASECHEQUECITY>No</HASECHEQUECITY>\
                        <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                        <HASCLIENTCODE>No</HASCLIENTCODE>\
                        <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                        <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                        <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                        <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                        <ISSCBUAE>No</ISSCBUAE>\
                        <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                        <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                        <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                        <AUDITED>No</AUDITED>\
                        <SORTPOSITION> 1000</SORTPOSITION>\
                        <LANGUAGENAME.LIST>\
                        <NAME.LIST TYPE="String">\
                            <NAME>%s</NAME>\
                        </NAME.LIST>\
                        <LANGUAGEID> 1033</LANGUAGEID>\
                        </LANGUAGENAME.LIST>\
                        </LEDGER>' % (old_account_name, self.tally_id, str(self.id), parent_name, ledger_name,
                                      parent_name, ledger_name if self.group_id.name else coa_map)

        if self.account_type == 'Cost of Revenue':
            body_xml = '<LEDGER NAME="%s" MASTERID="%s", RESERVEDNAME="%s" ACTION="Alter">\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <VATAPPLICABLE>&#4; Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>Yes</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                        </LEDGER>' % (old_account_name, self.tally_id, str(self.id), parent_name,
                                      ledger_name if self.group_id.name else coa_map)

        if self.account_type == 'Income':
            body_xml = '<LEDGER NAME="%s" MASTERID="%s" RESERVEDNAME="" ACTION="Alter">\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <VATAPPLICABLE>&#4; Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>Yes</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                            </LEDGER>' % (old_account_name, self.tally_id, str(self.id), sync_date_str, parent_name,
                                          ledger_name if self.group_id.name else coa_map)

        else:
            body_xml = ' '
            body_xml = '<LEDGER NAME="%s" MASTERID="%s" RESERVEDNAME="" ACTION="Alter">\
                                <MAILINGNAME.LIST TYPE="String">\
                                <MAILINGNAME>%s</MAILINGNAME>\
                                </MAILINGNAME.LIST>\
                                <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                                <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                                </OLDAUDITENTRYIDS.LIST>\
                                <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                                <COUNTRYNAME>India</COUNTRYNAME>\
                                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                                <PARENT>%s</PARENT>\
                                <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>\
                                <TAXCLASSIFICATIONNAME/>\
                                <TAXTYPE>Others</TAXTYPE>\
                                <COUNTRYOFRESIDENCE>India</COUNTRYOFRESIDENCE>\
                                <LEDADDLALLOCTYPE/>\
                                <GSTTYPE/>\
                                <APPROPRIATEFOR/>\
                                <GSTTYPEOFSUPPLY>Services</GSTTYPEOFSUPPLY>\
                                <EXCISELEDGERCLASSIFICATION/>\
                                <EXCISEDUTYTYPE/>\
                                <EXCISENATUREOFPURCHASE/>\
                                <LEDGERFBTCATEGORY/>\
                                <LEDSTATENAME>Tamil Nadu</LEDSTATENAME>\
                                <VATAPPLICABLE>&#4; Not Applicable</VATAPPLICABLE>\
                                <ISBILLWISEON>No</ISBILLWISEON>\
                                <ISCOSTCENTRESON>Yes</ISCOSTCENTRESON>\
                                <ISINTERESTON>No</ISINTERESTON>\
                                <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                                <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                                <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                                <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                                <ASORIGINAL>Yes</ASORIGINAL>\
                                <ISCONDENSED>No</ISCONDENSED>\
                                <AFFECTSSTOCK>No</AFFECTSSTOCK>\
                                <ISRATEINCLUSIVEVAT>No</ISRATEINCLUSIVEVAT>\
                                <FORPAYROLL>No</FORPAYROLL>\
                                <ISABCENABLED>No</ISABCENABLED>\
                                <ISCREDITDAYSCHKON>No</ISCREDITDAYSCHKON>\
                                <INTERESTONBILLWISE>No</INTERESTONBILLWISE>\
                                <OVERRIDEINTEREST>No</OVERRIDEINTEREST>\
                                <OVERRIDEADVINTEREST>No</OVERRIDEADVINTEREST>\
                                <USEFORVAT>No</USEFORVAT>\
                                <IGNORETDSEXEMPT>No</IGNORETDSEXEMPT>\
                                <ISTCSAPPLICABLE>No</ISTCSAPPLICABLE>\
                                <ISTDSAPPLICABLE>No</ISTDSAPPLICABLE>\
                                <ISFBTAPPLICABLE>No</ISFBTAPPLICABLE>\
                                <ISGSTAPPLICABLE>No</ISGSTAPPLICABLE>\
                                <ISEXCISEAPPLICABLE>No</ISEXCISEAPPLICABLE>\
                                <ISTDSEXPENSE>No</ISTDSEXPENSE>\
                                <ISEDLIAPPLICABLE>No</ISEDLIAPPLICABLE>\
                                <ISRELATEDPARTY>No</ISRELATEDPARTY>\
                                <USEFORESIELIGIBILITY>No</USEFORESIELIGIBILITY>\
                                <ISINTERESTINCLLASTDAY>No</ISINTERESTINCLLASTDAY>\
                                <APPROPRIATETAXVALUE>No</APPROPRIATETAXVALUE>\
                                <ISBEHAVEASDUTY>No</ISBEHAVEASDUTY>\
                                <INTERESTINCLDAYOFADDITION>No</INTERESTINCLDAYOFADDITION>\
                                <INTERESTINCLDAYOFDEDUCTION>No</INTERESTINCLDAYOFDEDUCTION>\
                                <ISOTHTERRITORYASSESSEE>No</ISOTHTERRITORYASSESSEE>\
                                <OVERRIDECREDITLIMIT>No</OVERRIDECREDITLIMIT>\
                                <ISAGAINSTFORMC>No</ISAGAINSTFORMC>\
                                <ISCHEQUEPRINTINGENABLED>Yes</ISCHEQUEPRINTINGENABLED>\
                                <ISPAYUPLOAD>No</ISPAYUPLOAD>\
                                <ISPAYBATCHONLYSAL>No</ISPAYBATCHONLYSAL>\
                                <ISBNFCODESUPPORTED>No</ISBNFCODESUPPORTED>\
                                <ALLOWEXPORTWITHERRORS>No</ALLOWEXPORTWITHERRORS>\
                                <CONSIDERPURCHASEFOREXPORT>No</CONSIDERPURCHASEFOREXPORT>\
                                <ISTRANSPORTER>No</ISTRANSPORTER>\
                                <USEFORNOTIONALITC>No</USEFORNOTIONALITC>\
                                <ISECOMMOPERATOR>No</ISECOMMOPERATOR>\
                                <SHOWINPAYSLIP>No</SHOWINPAYSLIP>\
                                <USEFORGRATUITY>No</USEFORGRATUITY>\
                                <ISTDSPROJECTED>No</ISTDSPROJECTED>\
                                <FORSERVICETAX>No</FORSERVICETAX>\
                                <ISINPUTCREDIT>No</ISINPUTCREDIT>\
                                <ISEXEMPTED>No</ISEXEMPTED>\
                                <ISABATEMENTAPPLICABLE>No</ISABATEMENTAPPLICABLE>\
                                <ISSTXPARTY>No</ISSTXPARTY>\
                                <ISSTXNONREALIZEDTYPE>No</ISSTXNONREALIZEDTYPE>\
                                <ISUSEDFORCVD>No</ISUSEDFORCVD>\
                                <LEDBELONGSTONONTAXABLE>No</LEDBELONGSTONONTAXABLE>\
                                <ISEXCISEMERCHANTEXPORTER>No</ISEXCISEMERCHANTEXPORTER>\
                                <ISPARTYEXEMPTED>No</ISPARTYEXEMPTED>\
                                <ISSEZPARTY>No</ISSEZPARTY>\
                                <TDSDEDUCTEEISSPECIALRATE>No</TDSDEDUCTEEISSPECIALRATE>\
                                <ISECHEQUESUPPORTED>No</ISECHEQUESUPPORTED>\
                                <ISEDDSUPPORTED>No</ISEDDSUPPORTED>\
                                <HASECHEQUEDELIVERYMODE>No</HASECHEQUEDELIVERYMODE>\
                                <HASECHEQUEDELIVERYTO>No</HASECHEQUEDELIVERYTO>\
                                <HASECHEQUEPRINTLOCATION>No</HASECHEQUEPRINTLOCATION>\
                                <HASECHEQUEPAYABLELOCATION>No</HASECHEQUEPAYABLELOCATION>\
                                <HASECHEQUEBANKLOCATION>No</HASECHEQUEBANKLOCATION>\
                                <HASEDDDELIVERYMODE>No</HASEDDDELIVERYMODE>\
                                <HASEDDDELIVERYTO>No</HASEDDDELIVERYTO>\
                                <HASEDDPRINTLOCATION>No</HASEDDPRINTLOCATION>\
                                <HASEDDPAYABLELOCATION>No</HASEDDPAYABLELOCATION>\
                                <HASEDDBANKLOCATION>No</HASEDDBANKLOCATION>\
                                <ISEBANKINGENABLED>No</ISEBANKINGENABLED>\
                                <ISEXPORTFILEENCRYPTED>No</ISEXPORTFILEENCRYPTED>\
                                <ISBATCHENABLED>No</ISBATCHENABLED>\
                                <ISPRODUCTCODEBASED>No</ISPRODUCTCODEBASED>\
                                <HASEDDCITY>No</HASEDDCITY>\
                                <HASECHEQUECITY>No</HASECHEQUECITY>\
                                <ISFILENAMEFORMATSUPPORTED>No</ISFILENAMEFORMATSUPPORTED>\
                                <HASCLIENTCODE>No</HASCLIENTCODE>\
                                <PAYINSISBATCHAPPLICABLE>No</PAYINSISBATCHAPPLICABLE>\
                                <PAYINSISFILENUMAPP>No</PAYINSISFILENUMAPP>\
                                <ISSALARYTRANSGROUPEDFORBRS>No</ISSALARYTRANSGROUPEDFORBRS>\
                                <ISEBANKINGSUPPORTED>No</ISEBANKINGSUPPORTED>\
                                <ISSCBUAE>No</ISSCBUAE>\
                                <ISBANKSTATUSAPP>No</ISBANKSTATUSAPP>\
                                <ISSALARYGROUPED>No</ISSALARYGROUPED>\
                                <USEFORPURCHASETAX>No</USEFORPURCHASETAX>\
                                <AUDITED>No</AUDITED>\
                                <SORTPOSITION> 1000</SORTPOSITION>\
                                <LANGUAGENAME.LIST>\
                                <NAME.LIST TYPE="String">\
                                    <NAME>%s</NAME>\
                                </NAME.LIST>\
                                <LANGUAGEID> 1033</LANGUAGEID>\
                                </LANGUAGENAME.LIST>\
                        </LEDGER>' % (old_account_name, self.tally_id, ledger_name, str(self.id),
                                      sync_date_str, parent_name, ledger_name)

        xml = head_xml + body_xml + xml_foot
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)
        except requests.exceptions.RequestException as e:
            print(e, "eeee--------")

        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            # error_log=''
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                # self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'coa',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': error_log,
                    'name': self.name,
                    'sync_status': 'fail',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//CREATED")
            # create_log = ''
            if line_error is not None:
                create_log = line_error.text  # Assign the extracted error message
            else:
                create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'coa',
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
