"""Common methods"""
import ast
import json
import werkzeug.wrappers
import requests
from bs4 import BeautifulSoup
import urllib.request


def valid_response(data, message=None, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    xml= "<ENVELOPE><HEADER>\
    <VERSION>1</VERSION>\
    <TALLYREQUEST>IMPORT</TALLYREQUEST>\
    <TYPE>DATA</TYPE>\
    <ID >RPT_PPTSMJSONMST_PostConfig</ID>\
    </HEADER>\
    <BODY>\
    <DESC>\
    <STATICVARIABLES>\
    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>\
    </STATICVARIABLES>\
    <UDF_PPTSMJSONMST_PostUserName>Test </UDF_PPTSMJSONMST_PostUserName>\
    <UDF_PPTSMJSONMST_PostUserPwd> Testpwd </UDF_PPTSMJSONMST_PostUserPwd>\
    <UDF_PPTSMJSONMST_PostToken> PSDFDS354234234324242423 </UDF_PPTSMJSONMST_PostToken>\
    </DESC>\
    </BODY>\
    </ENVELOPE>" % (data['access_token'])

    xml_data = xml.replace("&", "&amp;")
    soup = BeautifulSoup(xml_data, "xml")
    pretty_xml = soup.prettify()

    response = requests.post(url, headers = h, data=pretty_xml.encode('utf-8'))
    return response

def valid_response1(data,count=0, message=None, status=200):
    """Valid Response
    This will be return when the http request was successfully processed."""
    return json.loads(json.dumps([
        {
            'success': True,
            'count':count,
            # "error": False,
            'status': status,
            'message': message,
            'data': data,
        }]))

    # return werkzeug.wrappers.Response(
    #     status=status,
    #     content_type='application/json; charset=utf-8',
    #     response=json.dumps(data),
    # )


def invalid_response(typ, message=None, status=400):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    return json.loads(json.dumps([
            {'success': False,
            # "error":True,
            'status': status,
            # 'type': typ,
            'message': str(message) if message else 'wrong arguments (missing validation)'}
    ]))
    # return werkzeug.wrappers.Request(
    #     status=status,
    #     content_type="application/json; charset=utf-8",
    #     response=json.dumps({
    #         "type": typ,
    #         "message": str(message) if message else "wrong arguments (missing validation)",
    #     }),
    # )


def extract_arguments(payload, offset=0, limit=0, order=None):
    """."""
    fields, domain = [], []
    if payload.get('domain'):
        domain += ast.literal_eval(payload.get('domain'))
    if payload.get('fields'):
        fields += ast.literal_eval(payload.get('fields'))
    if payload.get('offset'):
        offset = int(payload['offset'])
    if payload.get('limit'):
        limit = int(payload['limit'])
    if payload.get('order'):
        order = payload.get('order')
    return [domain, fields, offset, limit, order]
