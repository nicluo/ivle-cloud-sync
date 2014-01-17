from requests import get
from requests.exceptions import ConnectionError
from urllib import urlencode

from ivlemods import app

LAPI_URL = 'https://ivle.nus.edu.sg/api/Lapi.svc/'

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
        for self.connection_tries in range(1, 4):
            try:
                return get(LAPI_URL + method, params=self.build_params(params), timeout=30).json()
            except ConnectionError:
                if self.connection_tries == 3:
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
