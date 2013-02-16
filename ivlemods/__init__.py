from flask import Flask
import logging
from logging.handlers import SMTPHandler

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('application.cfg', silent=True)

file_handler = logging.FileHandler('ivlemods.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)

mail_handler = SMTPHandler('smtp.gmail.com', 'ivlecloudsync@gmail.com',
    app.config['ADMINS'], 'IVLE Cloud Sync Error',
    credentials=('ivlecloudsync@gmail.com', '***REMOVED***'), secure=())
mail_handler.setFormatter(logging.Formatter('''
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s

Message:

%(message)s
'''))
mail_handler.setLevel(logging.ERROR)

loggers = [app.logger, logging.getLogger('ivlemods')]
for logger in loggers:
    logger.addHandler(file_handler)
    logger.addHandler(mail_handler)

import ivlemods.views