import os
import logging

from dropbox import client, rest, session
from datetime import datetime

from ivlemods import app

from ivlemods.database import db_session
from ivlemods.error import DropboxNoCredentials, DropboxExceedQuota
from ivlemods.models import User
import ivlemods.tasks_dropbox

logger = logging.getLogger(__name__)

class SessionHandler():
    def __init__(self, user_id):
        user = User.query.get(user_id)
        logger.debug("Session - logging in as user %s", user.user_id)
        if user.dropbox_key == None or user.dropbox_secret == None or not user.dropbox_valid:
            raise DropboxNoCredentials([user.dropbox_key, user.dropbox_secret])

        sess = session.DropboxSession(app.config['DROPBOX_APP_KEY'],
            app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
        sess.set_token(user.dropbox_key, user.dropbox_secret)
        self.user_id = user_id
        self.client = client.DropboxClient(sess)
    
    def ignore_timeout(self, func):
        def retry(*args, **kwargs):
            complete = False
            while not complete:
                try:
                    meta = func(*args, **kwargs)
                    return meta
                except rest.RESTSocketError as e:
                    logger.debug('TIMEOUT DETECTED')
                    #ignore timeouts
                    pass
                except rest.ErrorResponse as e:
                    #unauthorized
                    if e.status == 401:
                        user = User.query.get(self.user_id)
                        user.dropbox_valid = False
                        db_session.commit()
                        #raise no credentials error
                        raise DropboxNoCredentials([user.dropbox_key, user.dropbox_secret])

                    if e.status == 507:
                        raise DropboxExceedQuota(self.user_id)

                    raise e
        return retry
