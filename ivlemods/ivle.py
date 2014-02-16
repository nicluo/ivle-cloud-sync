import logging

from requests import get
from requests.exceptions import ConnectionError, HTTPError, Timeout
from urllib import urlencode

from ivlemods import app

LAPI_URL = 'https://ivle.nus.edu.sg/api/Lapi.svc/'

logger = logging.getLogger(__name__)


class IvleClient:

    def __init__(self, auth_token):
        self.api_key = app.config['IVLE_LAPI_KEY']
        self.auth_token = auth_token
        self.connection_tries = 0

    def build_params(self, params):
        token_key = 'AuthToken' if len(params) else 'Token'
        params['APIKey'] = self.api_key
        params[token_key] = self.auth_token
        return params

    def get(self, method, **params):
        max_tries = 3
        for self.connection_tries in range(0, max_tries):
            try:
                logger.info('Request #%d, %r, for %r' % (self.connection_tries, method, self.auth_token))
                response = get(LAPI_URL + method, params=self.build_params(params), timeout=10).json()
                logger.info('RequestSuccess %d, %r, for %r' % (self.connection_tries, method, self.auth_token))
                return response
            except ConnectionError, e:
                logger.debug(e)
                logger.info('ConnectionError %d, for %r' % (self.connection_tries, self.auth_token))
                if self.connection_tries == max_tries - 1:
                    raise
            except HTTPError, e:
                logger.debug(e)
                logger.info('HTTPError %d, for %r' % (self.connection_tries, self.auth_token))
                if self.connection_tries == max_tries - 1:
                    raise
            except Timeout, e:
                logger.debug(e)
                logger.info('TimeoutError %d, for %r' % (self.connection_tries, self.auth_token))
                if self.connection_tries == max_tries - 1:
                    raise

    def build_download_url(self, id):
        params = {'ID': id, 'target': 'workbin'}
        return ('https://ivle.nus.edu.sg/api/downloadfile.ashx?' +
                urlencode(self.build_params(params)))

    @staticmethod
    def build_authorize_url(callback_url):
        return ('https://ivle.nus.edu.sg/api/login/?' +
                urlencode({
                    'apikey': app.config['IVLE_LAPI_KEY'],
                    'url': callback_url
                }))
