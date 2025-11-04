"""
Module Description: This module manages API access tokens for Odoo.
It defines a model `api.access_token` for access tokens, providing methods
to check token validity, manage expiration, and create tokens for users.
Additionally, it extends the `res.users` model to include access tokens.
Note: Add more details as needed to describe the module's functionalities, usage, etc.
"""
import logging
import hashlib
import os
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)
EXPIRES_IN = "2592000"
def nonce(length=40, prefix="access_token"):
    """ Generates a random token.
    :param length: Length of the token (default is 40)
    :param prefix: Prefix to prepend to the token (default is 'access_token')
    :return: A string representing the generated token"""
    rbytes = os.urandom(length)
    return f"{prefix}_{hashlib.sha1(rbytes).hexdigest()}"


class APIAccessToken(models.Model):
    """ Model for managing API access tokens."""
    _name = 'api.access_token'
    _description = 'API Access Token'

    token = fields.Char('Access Token', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    expires = fields.Datetime(string="Expires", required=True)
    last_request = fields.Datetime('Last Requested On')
    scope = fields.Char('Scope')
    is_expired = fields.Boolean(string="Expired", store=True, readonly=True)

    def is_valid(self, scopes=None):
        """Checks if the access token is valid.
        :param scopes: An iterable containing the scopes to check or None"""
        self.ensure_one()
        return not self.has_expired() and self._allow_scopes(scopes)

    def has_expired(self):
        """Checks if the access token has expired.
        :return: True if the access token has expired, False otherwise"""
        self.ensure_one()
        if self.expires:
            return datetime.now() > fields.Datetime.from_string(self.expires)
        return False  # Explicit return for cases when self.expires is None

    def _allow_scopes(self, scopes):
        """Checks if the provided scopes are allowed.
        :param scopes: An iterable containing the scopes to check
        :return: True if all provided scopes are allowed, False otherwise"""
        self.ensure_one()
        if not scopes:
            return True
        provided_scopes = set(self.scope.split())
        resource_scopes = set(scopes)
        return resource_scopes.issubset(provided_scopes)

    def find_one_or_create_token(self, user_id=None, create=False):
        """Finds or creates a token for a user.
        :param user_id: ID of the user for whom the token is created
        :param create: Boolean to indicate whether to create a token if not found
        :return: Access token string or None if not found or creation is disabled"""
        if not user_id:
            user_id = self.env.user.id
        access_token = self.env["api.access_token"].sudo().search([("user_id", "=", user_id)],
                                                                  order="id DESC", limit=1)
        if access_token:
            access_token = access_token[0]
            access_token.sudo().update({
                'last_request': datetime.now()
            })
            if access_token.has_expired():
                access_token.sudo().update({
                    'is_expired': True
                })
                access_token = None
        if not access_token and create:
            expires = datetime.now() + timedelta(seconds=int(EXPIRES_IN))
            vals = {
                "user_id": user_id,
                "scope": "userinfo",
                "expires": expires.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                "token": nonce(),
            }
            access_token = self.env["api.access_token"].sudo().create(vals)
        if not access_token:
            return None
        return access_token.token

    @api.model
    def expire_token(self):
        """Expires tokens older than 10 minutes."""
        date = datetime.now()-timedelta(minutes=10)
        token_ids = self.search([('last_request','<=',date.strftime("%Y-%m-%d %H:%M:%S"))])
        if token_ids:
            _logger.info("Tokens are deleted :%s",(token_ids))
            token_ids.unlink()
