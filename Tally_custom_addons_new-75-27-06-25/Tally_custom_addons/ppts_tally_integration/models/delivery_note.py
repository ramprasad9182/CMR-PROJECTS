"""Odoo16 Module: Delivery Note"""
import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import models
import requests
from bs4 import BeautifulSoup


class DeliveryNote(models.Model):
    """This model extends the default functionality of 'stock.picking' in Odoo16,
    providing additional methods to synchronize out payment with an external system
    using XML requests, specifically tailored for integration with Tally ERP."""
    _inherit = 'stock.picking'

    def action_delivery_note(self):
        """This method constructs an XML request to synchronize Delivery Note
        with an external system, likely using Tally ERP. It retrieves necessary
        details from the out payment and sends the data to the specified URL."""
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
                                    <VOUCHER VCHTYPE="Delivery Note" ACTION="Create" OBJVIEW="Invoice Voucher View">' \
                   % (company)

        xml_foot = '</VOUCHER>\
                                </TALLYMESSAGE>\
                                </REQUESTDATA>\
                                </IMPORTDATA>\
                                </BODY>\
                                </ENVELOPE>'

        if self.scheduled_date:
            day = '0' + str(self.scheduled_date.day) if self.scheduled_date.day < 10\
                else str(self.scheduled_date.day)
            month = '0' + str(self.scheduled_date.month) if self.scheduled_date.month < 10 \
                else str(self.scheduled_date.month)
            delivery_date = str(self.scheduled_date.year) + month + day

        if self.sale_id.date_order:
            day = '0' + str(self.sale_id.date_order.day) if self.sale_id.date_order.day < 10 \
                else str(self.sale_id.date_order.day)
            month = '0' + str(self.sale_id.date_order.month) if self.sale_id.date_order.month < 10 \
                else str(self.sale_id.date_order.month)
            deadline = str(self.sale_id.date_order.year) + month + day

        parent_xml = '<DATE>%s</DATE>\
                <UDF:UDF_PPTSMJSONMST_ODOOID DESC="`UDF_PPTSMJSONMST_OdooID`">%s</UDF:UDF_PPTSMJSONMST_ODOOID>\
                <UDF:UDF_PPTSMJSONMST_SYNCDATETIME DESC="`UDF_PPTSMJSONMST_SyncDateTime`">%s</UDF:UDF_PPTSMJSONMST_SYNCDATETIME>\
                <NARRATION>%s</NARRATION>\
                <PARTYNAME>%s</PARTYNAME>\
                <VOUCHERTYPENAME>Delivery Note</VOUCHERTYPENAME>\
                <PARTYLEDGERNAME>%s</PARTYLEDGERNAME>\
                <VOUCHERNUMBER>%s</VOUCHERNUMBER>\
                <REFERENCE>%s</REFERENCE>\
                <PARTYMAILINGNAME>%s</PARTYMAILINGNAME>\
                <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>\
                <BILLOFLADINGNO></BILLOFLADINGNO>\
                <EICHECKPOST></EICHECKPOST>\
                <BASICSHIPPEDBY></BASICSHIPPEDBY>\
                <BASICFINALDESTINATION></BASICFINALDESTINATION>\
                <BASICORDERREF></BASICORDERREF>\
                <BASICSHIPVESSELNO></BASICSHIPVESSELNO>\
                <BASICDUEDATEOFPYMT></BASICDUEDATEOFPYMT>\
                <VOUCHERNUMBERSERIES></VOUCHERNUMBERSERIES>' % (
            delivery_date, str(self.id), sync_date, self.note, self.partner_id.name,
            self.partner_id.name, self.id, self.id,
            self.partner_id.name)
        order_line = []
        for rec in self.move_ids_without_package:
            child_data = '<ALLINVENTORYENTRIES.LIST>\
                            <STOCKITEMNAME>%s</STOCKITEMNAME>\
                            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\
                            <ACTUALQTY>%s</ACTUALQTY>\
                            <BILLEDQTY>%s</BILLEDQTY>\
                            <BATCHALLOCATIONS.LIST>\
                            <GODOWNNAME>Main Location</GODOWNNAME>\
                            <BATCHNAME>Primary Batch</BATCHNAME>\
                            <ORDERNO>%s</ORDERNO>\
                            <TRACKINGNUMBER>%s</TRACKINGNUMBER>\
                            <ACTUALQTY>%s</ACTUALQTY>\
                            <BILLEDQTY>%s</BILLEDQTY>\
                            <ORDERDUEDATE JD = "45180" P = "12-Sep-23">%s</ORDERDUEDATE>\
                            </BATCHALLOCATIONS.LIST>\
                            </ALLINVENTORYENTRIES.LIST>' % (
                rec.product_id.name,rec.quantity_done, rec.quantity_done,
                rec.picking_id.sale_id.id,rec.picking_id.sale_id.id,rec.quantity_done,
                rec.quantity_done,deadline)

            order_line.append(child_data)
        entries_xml = '<LEDGERENTRIES.LIST>\
                <LEDGERNAME>%s</LEDGERNAME>\
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\
                <ISPARTYLEDGER>Yes</ISPARTYLEDGER>\
                <AMOUNT></AMOUNT>\
                </LEDGERENTRIES.LIST>' % (self.partner_id.name)

        body_xml = ''
        for body in order_line:
            body_xml.join(body)
        xml = head_xml + parent_xml + body_xml + entries_xml+  xml_foot
        xml_data = xml.replace("&", "amp;")
        soup = BeautifulSoup(xml_data, "xml")
        pretty_xml = soup.prettify()
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
                    'master_type': 'delievry',
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
                    'master_type': 'delievry',
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
