import logging, sys
from logging.handlers import SMTPHandler

file_handler = logging.FileHandler('monitor.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.DEBUG)

mail_handler = SMTPHandler('smtp.gmail.com', 'ivlecloudsync@gmail.com',
    'nicholasluo@gmail.com', 'IVLE Cloud Sync Error',
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

root = logging.getLogger()
root.setLevel(logging.DEBUG)

main_logger = logging.getLogger('monitor')
main_logger.addHandler(file_handler)
main_logger.addHandler(mail_handler)
