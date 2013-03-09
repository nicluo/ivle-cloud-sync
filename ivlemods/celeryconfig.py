from __future__ import absolute_import

from celery.schedules import crontab

BROKER_URL = 'amqp://'
CELERY_IMPORTS = ['ivlemods.tasks']
CELERY_TIMEZONE = 'Singapore'
CELERYBEAT_SCHEDULE = {
    'every-five-minutes-except-between-three-to-four-am': {
        'task': 'ivlemods.tasks.one_task_to_rule_them_all',
        'schedule': crontab(minute='*/5', hour='0-2,4-23'),
        'args': (5,),
        }
}