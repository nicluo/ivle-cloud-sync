import logging, sys
from logging.handlers import SMTPHandler

file_handler = logging.FileHandler('monitor.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s '
    '[in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.DEBUG)

mail_handler = SMTPHandler(('smtp.gmail.com', 587), 'ivlecloudsync@gmail.com',
    ['nicholasluo@gmail.com', 'ahbengish@gmail.com'], 'CloudSync Monitor Error',
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
mail_handler.setLevel(logging.WARNING)

root = logging.getLogger()
root.setLevel(logging.DEBUG)

main_logger = logging.getLogger('monitor')
main_logger.addHandler(file_handler)
main_logger.addHandler(mail_handler)

schedule_mail_handler = SMTPHandler(('smtp.gmail.com', 587), 'ivlecloudsync@gmail.com',
    ['nicholasluo@gmail.com', 'ahbengish@gmail.com'], 'CloudSync Monitor Scheduled Message',
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
schedule_mail_handler.setLevel(logging.INFO)

mail_logger = logging.getLogger('mail')
mail_logger.addHandler(schedule_mail_handler)
mail_logger.addHandler(file_handler)
