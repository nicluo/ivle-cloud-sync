import os
import logging

from dropbox import client, rest, session
from datetime import datetime

from ivlemods import app

from ivlemods.models import User
from ivlemods.error import DropboxNoCredentials
import ivlemods.tasks_dropbox

logger = logging.getLogger(__name__)

class SessionHandler():
    def __init__(self, user_id):
        user = User.query.get(user_id)
        logger.debug("Session - logging in as user %s", user.user_id)
        if user.dropbox_key == None or user.dropbox_secret == None:
            raise DropboxNoCredentials([user.dropbox_key, user.dropbox_secret])

        sess = session.DropboxSession(app.config['DROPBOX_APP_KEY'],
            app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
        sess.set_token(user.dropbox_key, user.dropbox_secret)
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
        return retry
