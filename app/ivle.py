from requests import get
from urllib import urlencode

LAPI_URL = 'https://ivle.nus.edu.sg/api/Lapi.svc/'
IVLE_LAPI_KEY = '***REMOVED***'

def build_authorize_url(callback_url):
    return ('https://ivle.nus.edu.sg/api/login/?' +
            urlencode({'apikey': IVLE_LAPI_KEY, 'url': callback_url}))


class Client:
    def __init__(self, auth_token):
        self.api_key = IVLE_LAPI_KEY
        self.auth_token = auth_token

    def get(self, method, **params):
        token_key = 'AuthToken' if len(params) else 'Token'
        params['APIKey'] = self.api_key
        params[token_key] = self.auth_token
        return get(LAPI_URL + method, params=params).json()