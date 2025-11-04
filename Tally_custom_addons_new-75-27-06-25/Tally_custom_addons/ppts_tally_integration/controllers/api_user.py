""" APIController class for handling Tally integration in Odoo."""
import json
import logging
import functools
from odoo import http
from odoo.addons.ppts_tally_integration.common import invalid_response
from odoo.http import request
from odoo.exceptions import AccessError, AccessDenied
_logger = logging.getLogger(__name__)

EXPIRES_IN = "2592000000"
magic_fields = ['__last_update', 'create_uid', 'create_date', 'write_uid', 'write_date', 'id']


def validate_token(func):
    """ Access Token Validate"""
    @functools.wraps(func)
    def wrap(self, *args, **kwargs):
        params = json.loads(request.httprequest.data)
        access_token = params.get("access_token")
        # login=params.get("login")
        # session_id = request.httprequest.headers.get("Cookie")
        if not access_token:
            return invalid_response("access_token_not_found",
                                    "missing access token in request header", 401)
        access_token_data = (
            request.env["api.access_token"].sudo().search(
                [("token", "=", access_token)], order="id DESC", limit=1)
        )
        if not access_token_data:
            # if access_token_data.user_id.login != login:
            return invalid_response("access_token miss match", "Invalid Access Token", 401)
        if (access_token_data.find_one_or_create_token
            (user_id=access_token_data.user_id.id) != access_token):
            return invalid_response("access_token", "token seems to have expired or invalid", 401)
        request.env.uid = access_token_data.user_id.id
        return func(self, *args, **kwargs)
    return wrap


class APITokenController(http.Controller):
    """Access Token from Tally"""
    def __init__(self):
        self._token = request.env["api.access_token"]
        self._expires_in = EXPIRES_IN

    @http.route("/api/create/get_token", type='json', methods=['POST'], auth='public', csrf=False)
    def token(self, **post):
        """Once the access token created the notification generate"""
        try:
            _logger.error('@ Successfully Created Token :%s', str('Token'))
            _token = request.env["api.access_token"]
            post = json.loads(request.httprequest.data)
            params = ["db", "login", "password"]
            params = {key: post.get(key) for key in params if post.get(key)}
            db, username, password = (
                request.env['res.users'].sudo()._get_db_name(),
                post.get("login"),
                post.get("password"),
            )
            tally_host, tally_company = (
                post.get("host"),
                post.get("company"))
            _credentials_includes_in_body = all([db, username, password])
            if not _credentials_includes_in_body:
                headers = request.httprequest.headers
                db = headers.get("db")
                username = headers.get("login")
                password = headers.get("password")
                _credentials_includes_in_headers = all([db, username, password])
                if not _credentials_includes_in_headers:
                    return invalid_response(
                        "missing error",
                        "either of the following are missing [db, username,password]",
                        403,
                    )
            # Login in odoo database:
            try:
                request.session.authenticate(db, username, password)
            except AccessError as aee:
                return invalid_response("Access error", "Error: %s", aee.name)
            except AccessDenied:
                return invalid_response("Access denied", "Login or password invalid.")
            except ImportError as e:
                # Invalid database:
                info = "The database name is not valid {%s}",e
                error = "invalid_database"
                _logger.error(info)
                return invalid_response("wrong database name", error, 403)
            uid = request.session.uid
            # odoo login failed:
            if not uid:
                info = "authentication failed"
                error = "authentication failed"
                _logger.error(info)
                return invalid_response(401, error, info)
            # Generate tokens
            access_token = _token.find_one_or_create_token(user_id=uid, create=True)
            # Successful response:
            # user=request.env['res.users'].sudo().search([('id', '=', uid)])
            if access_token:
                result = []
                # emp_image = image.decode('UTF-8') if image else None
                val = {
                    'uid': uid,
                    'login':username,
                    'success': True,
                    'access_token': access_token,
                    'host': tally_host,
                    'company': tally_company
                }
                result.append(val)
                _logger.error('@ Successfully Created Token :%s', access_token)
                # Respone to Tally, Access Token
                response = {
                    'access_token': str(access_token),
                    'status':'success'}
                return response
            else:
                info = "Emaployee id not found"
                error = "invalid employee id"
                return invalid_response(408, error, info)
        except ImportError as e:
            result = {}
            result.update({'status': False, 'error': str(e)})
            _logger.info('@ Token Generation Error : %s',json.dumps(result))
            return json.dumps(result)
        return None
