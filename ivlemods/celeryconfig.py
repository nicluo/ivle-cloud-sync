from __future__ import absolute_import

from celery.schedules import crontab

BROKER_URL = 'amqp://'
CELERY_IMPORTS = ('ivlemods.dist', 'ivlemods.tasks')
CELERY_TIMEZONE = 'Singapore'
CELERYBEAT_SCHEDULE = {
    'every-five-minutes': {
        'task': 'ivlemods.dist.upload_dropbox_jobs',
        'schedule': crontab(minute='*/1')
        },
    'every-five-minutes-except-between-three-to-four-am': {
        'task': 'ivlemods.tasks.ivle_workbin_to_dropbox_jobs',
        'schedule': crontab(minute='*/5', hour=[0-2,4-23]),
        'args': (5,),
        }
}