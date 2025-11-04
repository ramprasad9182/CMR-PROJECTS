"""Part of Odoo. See LICENSE file for full copyright and licensing details."""
from datetime import datetime
import xml.etree.ElementTree as ET
from odoo import api, models
import requests
from bs4 import BeautifulSoup
import pytz
import time


class AccountGroup(models.Model):
    """This model inherits from 'account.group' and can be used
     for additional functionalities or customizations related to
     accounting groups in Odoo."""
    _inherit = "account.group"

    def write(self, vals):
        for rec in self:
            # Check if group name is being changed
            if 'name' in vals:
                rec.old_name = rec.name  # Save old name before changing

                # If status is 'done' and not already changing ndw_select, switch to 'write'
                if rec.ndw_select == 'done' and 'ndw_select' not in vals:
                    vals['ndw_select'] = 'write'

        return super(AccountGroup, self).write(vals)

    # @api.onchange('name', 'tally_id', 'company_id', 'parent_group_id', 'parent_id')
    # def _onchange_group_ndw_select(self):
    #     # self.write({'ndw_select':'write'})
    #     for rec in self:
    #         # If record is not yet saved (new in UI), set to 'New'
    #         if not rec.id:
    #             rec.ndw_select = 'new'
    #         else:
    #             rec.ndw_select = 'write'

    # @api.model
    # def create(self, vals):
    #     vals['ndw_select'] = 'new'
    #     return super(AccountGroup, self).create(vals)
    #
    # def write(self, vals):
    #     if 'name' in vals:
    #         for rec in self:
    #             rec.old_name = rec.name  # Save current name before update
    #     return super().write(vals)

    def action_sync_ac_grp(self):
        """Sync Account Groups with an external system.
        This method constructs an XML request to synchronize Account Groups
        with an external system (probably Tally ERP) and sends the data
        to the specified URL."""
        tally_log_ids = []
        if self:
            odoo_currcmp = self.company_id
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_id  # Get the current company ID
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
        h = {'Content-Encoding': 'gzip','CONTENT-TYPE': 'text/xml; charset=utf-8'}
        # company = "Demo Company"
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        group_action = "create"
        group_name = self.name
        sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        print("System time:", time.tzname)
        print("Local time:", datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S"))
        print("UTC time:  ", datetime.utcnow().strftime("%d-%b-%Y : %H:%M:%S"))
        print("synctime", sync_date_str)
        # parent_group = self.parent_id.name
        parent_group = "$$SysName:Primary" if not self.parent_id.name else self.parent_id.name
        print('group parent', self.parent_id.name)
        # parent_group = self.parent_group_id.name
        xml = ('<ENVELOPE>\n<HEADER>\n<TALLYREQUEST> Import Data </TALLYREQUEST>\n</HEADER>\n<BODY>\n'
               '<IMPORTDATA>\n<REQUESTDESC>\n<REPORTNAME> All Masters </REPORTNAME>\n'
               '<STATICVARIABLES>\n<SVCURRENTCOMPANY>%s</SVCURRENTCOMPANY>\n</STATICVARIABLES>\n'
               '</REQUESTDESC>\n<REQUESTDATA>\n<TALLYMESSAGE xmlns:UDF="TallyUDF">\n'
               '<GROUP ACTION="%s" NAME="%s">\n<NAME.LIST>\n<NAME>%s</NAME>\n'
               '</NAME.LIST>\n<PARENT>%s</PARENT>\n'
               '<UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\n'
               '<UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\n'
               '<ISSUBLEDGER> No </ISSUBLEDGER>\n'
               '<ISBILLWISEON> No </ISBILLWISEON>\n<ISCOSTCENTRESON> No </ISCOSTCENTRESON>\n</GROUP>\n'
               '</TALLYMESSAGE>\n</REQUESTDATA>\n</IMPORTDATA>\n</BODY>\n</ENVELOPE>\n'
                    % (tally_currcompany, group_action, group_name, self.name,
                       parent_group if self.parent_id else "Primary",
                       str(self.id), str(sync_date)))
        xml_data = xml.replace("&","&amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
        response = False
        try:
            response = requests.post(url, headers = h, data=pretty_xml.encode('utf-8'),timeout=120)
        except requests.exceptions.RequestException as e:
            print(e, "eeee--------")

        if response:
            # soup_2 = BeautifulSoup(response.text, 'xml')
            rec = ET.fromstring(response.content)
            line_error = rec.find(".//LINEERROR")
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'group',
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
            # create_log = ''
            if success is not None:
                create_log = success.text  # Assign the extracted error message
            # else:
            #     create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'group',
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

        print("235246345345",tally_log_ids)

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
                                                        <TYPE>Group</TYPE >
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
    def action_sync_ac_grp_alter(self):
        tally_log_ids = []
        if self:
            odoo_currcmp = self.company_id
            print('All Field Values:', odoo_currcmp)

        tally_currcompany = ''
        current_company_id = self.company_id   # Get the current company ID
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
        # company = "Demo Company"
        db_config = self.env['mysqldb.config'].search([], limit=1)
        url = db_config.db_hostname
        company = db_config.company_name
        group_action = "Alter"
        group_name = self.name
        old_group_name=self.old_name
        tally_master_id = self.tally_id
        sync_date = datetime.now().strftime("%d-%b-%y : %H:%M:%S")
        ist_timez = pytz.timezone('Asia/Kolkata')
        sync_date = datetime.now(ist_timez).strftime("%d-%b-%Y : %H:%M:%S")
        sync_date_str = str(sync_date)
        # parent_group = self.parent_id.name
        parent_group = "$$SysName:Primary" if not self.parent_id.name else self.parent_id.name
        print('group parent', self.parent_id.name)
        # parent_group = self.parent_group_id.name
        xml = '''<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <GROUP NAME="{old_name}" MASTERID="{master_id}" ACTION="Alter">
            <LANGUAGENAME.LIST>
              <NAME.LIST>
                <NAME>{group_name}</NAME>
              </NAME.LIST>
            </LANGUAGENAME.LIST>
            <PARENT>{parent_name}</PARENT>
            <MASTERID>{master_id}</MASTERID>
            <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">{odoo_id}</UDF:UDF_PPTSMJSONMST_ODOOID>
            <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">{sync_date}</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>
            <ISSUBLEDGER>No</ISSUBLEDGER>
            <ISBILLWISEON>No</ISBILLWISEON>
            <ISCOSTCENTRESON>No</ISCOSTCENTRESON>
          </GROUP>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>'''.format(
    company=tally_currcompany,
    old_name= old_group_name,
    master_id=tally_master_id,
    group_name=self.name,
    parent_name=parent_group if self.parent_id else "Primary",
    odoo_id=self.id,
    sync_date=str(sync_date)
)
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
            if line_error is not None:
                error_log = line_error.text  # Assign the extracted error message
            else:
                error_log = "No LINEERROR element found in the XML."

            if '<LINEERROR>' in str(response.text):
                self.ndw_select = 'new'
                vals = (0, 0, {
                    'master_type': 'group',
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
            # create_log = ''
            if success is not None:
                create_log = success.text  # Assign the extracted error message
            # else:
            #     create_log = "No LINEERROR element found in the XML."
            if ('<CREATED>1</CREATED>' in str(response.text) or
                    "<ALTERED>1</ALTERED>" in str(response.text)):
                self.ndw_select = 'done'
                vals = (0, 0, {
                    'master_type': 'group',
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

        print("235246345345", tally_log_ids)
        return data
