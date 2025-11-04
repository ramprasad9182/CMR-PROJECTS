# -*- coding: utf-8 -*-
"""Part of Odoo. See LICENSE file for full copyright and licensing details."""
import xml.etree.ElementTree as ET
from dataclasses import fields
from datetime import datetime
from odoo import api, models
from bs4 import BeautifulSoup
import requests
from odoo import models, fields
import pytz
import time

class ResPartner(models.Model):
    _inherit = "res.partner"

    from_date = fields.Date('Applicable from date', required=True)

    def write(self, vals):
        for rec in self:
            # Check if group name is being changed
            if 'name' in vals:
                rec.old_name = rec.name  # Save old name before changing

                # If status is 'done' and not already changing ndw_select, switch to 'write'
                if rec.ndw_select == 'done' and 'ndw_select' not in vals:
                    vals['ndw_select'] = 'write'

        return super(ResPartner, self).write(vals)

    def __init__(self, env, ids, prefetch_ids):
        super().__init__(env, ids, prefetch_ids)

    def _create_partner(self, name, partner_type, from_date, tally_id):
        """Create a partner record with the given details."""
        return self.sudo().create({'name': name,
                                   'type_partner': partner_type, 'from_date': from_date, 'tally_id': tally_id})

    def action_sync_partner(self):
        """Synchronize partner data with an external system, possibly Tally ERP.

               Retrieves partner details and sends the data to the specified URL.
               """

        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        if self:
            odoo_currcmp = self.company_registry
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_registry  # Get the current company ID
        # print('odoocmp', odoo_curcmp)

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        company_rec = self.env['res.company'].sudo().browse(int(self.company_registry))
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', company_rec.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({current_company_id}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({current_company_id})')

        h = {'Content-Encoding': 'gzip','CONTENT-TYPE': 'text/xml; charset=utf-8'}
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        print("System time:", time.tzname)
        print("Local time:", datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        print("synctime", sync_date_str)
        print("System time:", time.tzname)
        print("Local time:", datetime.now().strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        # group_action = "ALTER"
        # group_name = "My Debtors"
        ledger_name = self.name
        # old_partner_name = self.old_name
        print('partner name', ledger_name)
        print('partner_id', str(self.id))
        address_1 = (str(self.street if self.street else '')  +
                     str(self.street2 if self.street2 else '') or '')
        address_2 = str(self.city if self.city else '' + ', ' +
                                                    self.state_id.name + ', ' if self.state_id else ''  + self.country_id.name if self.country_id else '') or ''
        parent_name = ''
        if self.type_partner== 'customer':
            parent_name =  'Sundry Debtors'   #self.property_account_receivable_id.group_id.name
        else:
            if self.type_partner == 'supplier':
                parent_name = 'Sundry Creditors'        #self.property_account_payable_id.group_id.name
        print('parent', parent_name)
        email = self.email or ''
        pincode = self.zip or ''
        incometax_no = self.pan_no or ''
        country_name = self.country_id.name or ''
        gst_registration_type = ''
        if self.l10n_in_gst_treatment == 'regular':
            gst_registration_type = 'Regular'
        elif self.l10n_in_gst_treatment == 'consumer':
            gst_registration_type = 'Consumer'
        elif self.l10n_in_gst_treatment == 'composition':
            gst_registration_type = 'Composition'
        else:
            gst_registration_type = 'Unregistered'
        vat_dealer_type = 'Regular' or ''
        tax_type = 'Others' or ''
        billcredit_period = self.property_payment_term_id.name or '30 Days'
        country_residence = self.country_id.name or 'India'
        ledger_phn = self.phone or ''
        ledger_contact = self.contact_person or ''
        ledger_mobile = self.mobile or ''
        party_gstin = self.vat or ''
        led_statename = self.state_id.name or ''
        affect_stock = 'No' or ''
        # str_date = self.from_date or ''
        # date_obj = datetime.strftime(str_date, '%y-%m-%d') or ''
        formatted_date = self.from_date.strftime("%Y%m%d") if self.from_date else ''

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
                    <LEDGER NAME="%s" RESERVEDNAME="">\
                    <LEDGSTREGDETAILS.LIST>\
                    <APPLICABLEFROM>%s</APPLICABLEFROM>\
                    <GSTREGISTRATIONTYPE>%s</GSTREGISTRATIONTYPE>\
                    <PLACEOFSUPPLY>%s</PLACEOFSUPPLY>\
                    <GSTIN>%s</GSTIN>\
                    </LEDGSTREGDETAILS.LIST>\
                    <LEDMAILINGDETAILS.LIST>\
                    <ADDRESS.LIST TYPE="String">\
                    <ADDRESS>%s</ADDRESS>\
                    <ADDRESS>%s</ADDRESS>\
                    </ADDRESS.LIST>\
                    <APPLICABLEFROM>%s</APPLICABLEFROM>\
                    <MAILINGNAME>%s</MAILINGNAME>\
                    <PINCODE>%s</PINCODE>\
                    <STATE>%s</STATE>\
                    <COUNTRY>%s</COUNTRY>\
                    </LEDMAILINGDETAILS.LIST>\
                    <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                    <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                    </OLDAUDITENTRYIDS.LIST>\
                    <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                    <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                    <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                    <INCOMETAXNUMBER>%s</INCOMETAXNUMBER>\
                    <COUNTRYNAME>%s</COUNTRYNAME>\
                    <GSTREGISTRATIONTYPE>%s</GSTREGISTRATIONTYPE>\
                    <VATDEALERTYPE>%s</VATDEALERTYPE>\
                    <PARENT>%s</PARENT>\
                    <TAXTYPE>%s</TAXTYPE>\
                    <BILLCREDITPERIOD>%s</BILLCREDITPERIOD>\
                    <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                    <LEDGERPHONE>%s</LEDGERPHONE>\
                    <LEDGERCONTACT>%s</LEDGERCONTACT>\
                    <LEDGERMOBILE>%s</LEDGERMOBILE>\
                    <PARTYGSTIN>%s</PARTYGSTIN>\
                    <LEDSTATENAME>%s</LEDSTATENAME>\
                    <ISBILLWISEON>Yes</ISBILLWISEON>\
                    <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                    <ISINTERESTON>No</ISINTERESTON>\
                    <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                    <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                    <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                    <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                    <ASORIGINAL>Yes</ASORIGINAL>\
                    <ISCONDENSED>No</ISCONDENSED>\
                    <AFFECTSSTOCK>%s</AFFECTSSTOCK>\
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
                    <LANGUAGENAME.LIST>\
                    <NAME.LIST TYPE="String">\
                    <NAME>%s</NAME>\
                    </NAME.LIST>\
                    <LANGUAGEID> 1033</LANGUAGEID>\
                    </LANGUAGENAME.LIST>\
                    </LEDGER>\
                    </TALLYMESSAGE>\
                    </REQUESTDATA>\
                    </IMPORTDATA>\
                    </BODY>\
            </ENVELOPE>' % (tally_currcompany,ledger_name, str(formatted_date), vat_dealer_type, led_statename, party_gstin, address_1, address_2, str(formatted_date), ledger_name, str(pincode), led_statename, country_name, str(self.id), sync_date_str, incometax_no, country_name, gst_registration_type, vat_dealer_type, parent_name, tax_type, billcredit_period, country_residence, ledger_phn, ledger_contact, ledger_mobile, party_gstin, led_statename, affect_stock, ledger_name))
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        try:
            response = requests.post(url, headers = h, data=pretty_xml.encode('utf-8'), timeout=60)


        except requests.exceptions.RequestException as e:
            # raise UserError(_(str(e)))
            print(e, "eeee--------")

            # self.env.user.notify_danger(message='Exception occured while importing : %s' % str(e))
        # error_message =''
        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            # error_message = ''
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'partner',
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
            # error_message = ''
            if success is not None:
                create_log = success.text  # Assign the extracted error message
            else:
                create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'partner',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': create_log,
                    'name': self.name,
                    'sync_status': 'done',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
                # self.env.user.notify_success(message='Records successfully Created / Altered')
        data = {
            "tally_log_ids": tally_log_ids,
            "tally_log_xml_data": xml_data
        }

        group_masterid_req = f"""<ENVELOPE>
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
                                                            <SYSTEM TYPE="Formula" NAME="FLTR_MNIAPI_GrpMID">$Name={ledger_name}</SYSTEM>
                                                        </TDLMESSAGE>
                                                    </TDL>
                                                </DESC>
                                            </BODY>
                                        </ENVELOPE>"""

        headers = {'Content-Type': 'text/xml'}
        response = requests.post(url, data=group_masterid_req.encode('utf-8'), headers=headers)
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

        return data

    def action_sync_partner_alter(self):
        tally_log_ids = []
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        if self:
            odoo_currcmp = self.company_registry
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_registry # Get the current company ID
        # print('odoocmp', odoo_curcmp)

        # Use sudo() if necessary, to bypass access rules if they are filtering records
        company_rec = self.env['res.company'].sudo().browse(int(self.company_registry))
        tally_db_name = self.env['ppts.tally.integration'].sudo().search(
            [('company_id', '=', company_rec.id)], limit=1
        )

        if tally_db_name:
            tally_currcompany = tally_db_name.tally_company
            print(f'COA Company for Current Company ({current_company_id}):', tally_currcompany)
        else:
            print(f'No tally company assigned for the current company ({current_company_id})')

        h = {'Content-Encoding': 'gzip', 'CONTENT-TYPE': 'text/xml; charset=utf-8'}
        # sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        # group_action = "ALTER"
        # group_name = "My Debtors"
        ledger_name = self.name
        print('partner name', ledger_name)
        print('partner_id', str(self.id))
        address_1 = (str(self.street if self.street else '') +
                     str(self.street2 if self.street2 else '') or '')
        address_2 = str(self.city if self.city else '' + ', ' +
                                                    self.state_id.name + ', ' if self.state_id else '' + self.country_id.name if self.country_id else '') or ''
        parent_name = ''
        if self.type_partner == 'customer':
            parent_name = 'Sundry Debtors'  # self.property_account_receivable_id.group_id.name
        else:
            if self.type_partner == 'supplier':
                parent_name = 'Sundry Creditors'  # self.property_account_payable_id.group_id.name
        print('parent', parent_name)
        email = self.email or ''
        pincode = self.zip or ''
        incometax_no = self.pan_no or ''
        country_name = self.country_id.name or ''
        gst_registration_type = ''
        if self.l10n_in_gst_treatment == 'regular':
            gst_registration_type = 'Regular'
        elif self.l10n_in_gst_treatment == 'consumer':
            gst_registration_type = 'Consumer'
        elif self.l10n_in_gst_treatment == 'composition':
            gst_registration_type = 'Composition'
        else:
            gst_registration_type = 'Unregistered'
        vat_dealer_type = 'Regular' or ''
        tax_type = 'Others' or ''
        # old_partner_name = self.old_name
        billcredit_period = self.property_payment_term_id.name or '30 Days'
        country_residence = self.country_id.name or 'India'
        ledger_phn = self.phone or ''
        ledger_contact = self.contact_person or ''
        ledger_mobile = self.mobile or ''
        party_gstin = self.vat or ''
        led_statename = self.state_id.name or ''
        affect_stock = 'No' or ''
        old_partner_name=self.old_name
        # str_date = self.from_date or ''
        # date_obj = datetime.strftime(str_date, '%y-%m-%d') or ''
        formatted_date = self.from_date.strftime("%Y%m%d") if self.from_date else ''

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
                            <LEDGER NAME="%s" MASTERID="%s" RESERVEDNAME="" ACTION="Alter">\
                            <LEDGSTREGDETAILS.LIST>\
                            <APPLICABLEFROM>%s</APPLICABLEFROM>\
                            <GSTREGISTRATIONTYPE>%s</GSTREGISTRATIONTYPE>\
                            <PLACEOFSUPPLY>%s</PLACEOFSUPPLY>\
                            <GSTIN>%s</GSTIN>\
                            </LEDGSTREGDETAILS.LIST>\
                            <LEDMAILINGDETAILS.LIST>\
                            <ADDRESS.LIST TYPE="String">\
                            <ADDRESS>%s</ADDRESS>\
                            <ADDRESS>%s</ADDRESS>\
                            </ADDRESS.LIST>\
                            <APPLICABLEFROM>%s</APPLICABLEFROM>\
                            <MAILINGNAME>%s</MAILINGNAME>\
                            <PINCODE>%s</PINCODE>\
                            <STATE>%s</STATE>\
                            <COUNTRY>%s</COUNTRY>\
                            </LEDMAILINGDETAILS.LIST>\
                            <OLDAUDITENTRYIDS.LIST TYPE="Number">\
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>\
                            </OLDAUDITENTRYIDS.LIST>\
                            <CURRENCYNAME><string name="Rs">\u20B9</string></CURRENCYNAME>\
                            <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                            <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                            <INCOMETAXNUMBER>%s</INCOMETAXNUMBER>\
                            <COUNTRYNAME>%s</COUNTRYNAME>\
                            <GSTREGISTRATIONTYPE>%s</GSTREGISTRATIONTYPE>\
                            <VATDEALERTYPE>%s</VATDEALERTYPE>\
                            <PARENT>%s</PARENT>\
                            <TAXTYPE>%s</TAXTYPE>\
                            <BILLCREDITPERIOD>%s</BILLCREDITPERIOD>\
                            <COUNTRYOFRESIDENCE>%s</COUNTRYOFRESIDENCE>\
                            <LEDGERPHONE>%s</LEDGERPHONE>\
                            <LEDGERCONTACT>%s</LEDGERCONTACT>\
                            <LEDGERMOBILE>%s</LEDGERMOBILE>\
                            <PARTYGSTIN>%s</PARTYGSTIN>\
                            <LEDSTATENAME>%s</LEDSTATENAME>\
                            <ISBILLWISEON>Yes</ISBILLWISEON>\
                            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>\
                            <ISINTERESTON>No</ISINTERESTON>\
                            <ALLOWINMOBILE>No</ALLOWINMOBILE>\
                            <ISCOSTTRACKINGON>No</ISCOSTTRACKINGON>\
                            <ISBENEFICIARYCODEON>No</ISBENEFICIARYCODEON>\
                            <ISUPDATINGTARGETID>No</ISUPDATINGTARGETID>\
                            <ASORIGINAL>Yes</ASORIGINAL>\
                            <ISCONDENSED>No</ISCONDENSED>\
                            <AFFECTSSTOCK>%s</AFFECTSSTOCK>\
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
                            <ISPARTYEXEMPTED>No</ISPARTYEXEMPTEDx>\
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
                            <LANGUAGENAME.LIST>\
                            <NAME.LIST TYPE="String">\
                            <NAME>%s</NAME>\
                            </NAME.LIST>\
                            <LANGUAGEID> 1033</LANGUAGEID>\
                            </LANGUAGENAME.LIST>\
                            </LEDGER>\
                            </TALLYMESSAGE>\
                            </REQUESTDATA>\
                            </IMPORTDATA>\
                            </BODY>\
                    </ENVELOPE>' % (
        tally_currcompany, old_partner_name, self.tally_id ,str(formatted_date), vat_dealer_type, led_statename, party_gstin, address_1,
        address_2, str(formatted_date), ledger_name, str(pincode), led_statename, country_name, str(self.id),
        sync_date_str, incometax_no, country_name, gst_registration_type, vat_dealer_type, parent_name, tax_type,
        billcredit_period, country_residence, ledger_phn, ledger_contact, ledger_mobile, party_gstin, led_statename,
        affect_stock, ledger_name))
        xml_data = xml.replace("&", "&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        try:
            response = requests.post(url, headers=h, data=pretty_xml.encode('utf-8'), timeout=60)


        except requests.exceptions.RequestException as e:
            # raise UserError(_(str(e)))
            print(e, "eeee--------")

            # self.env.user.notify_danger(message='Exception occured while importing : %s' % str(e))
        # error_message =''
        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            # error_message = ''
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'partner',
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
            # error_message = ''
            if success is not None:
                create_log = success.text  # Assign the extracted error message
            else:
                create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'partner',
                    'sync_action': 'create',
                    'sync_data': str(pretty_xml),
                    'error_data': create_log,
                    'name': self.name,
                    'sync_status': 'done',
                    'sync_for': 'master',
                })
                tally_log_ids.append(vals)
                # self.env.user.notify_success(message='Records successfully Created / Altered')
        data = {
            "tally_log_ids": tally_log_ids,
            "tally_log_xml_data": xml_data
        }
        return data

    # @api.onchange('name','tally_id','company_id',
    #               'street','vat','customer','supplier','country_id',
    #               'state_id','zip','phone','mobile','email','contact_person','account_group_id')
    # def onchange_ndw_select(self):
    #     """
    #     Triggered when key partner fields change.
    #     If 'tally_flag' is set, marks the record as needing write sync by setting 'ndw_select' to 'write'.
    #     """
    #     if self.tally_flag:
    #         self.ndw_select = 'write'
    #
    #     # if self._origin and self._origin.id and self.name != self._origin.name:
    #     #     self.old_name = self._origin.name
    #
