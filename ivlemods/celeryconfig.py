from __future__ import absolute_import

from celery.schedules import crontab

BROKER_URL = 'redis://localhost:6379/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_IMPORTS = ['ivlemods.tasks']
CELERY_TIMEZONE = 'Singapore'
CELERYBEAT_SCHEDULE = {
    'every-five-minutes-except-between-three-to-four-am': {
        'task': 'ivlemods.tasks.one_task_to_rule_them_all',
        'schedule': crontab(minute='*/5')
    }
}
CELERY_ROUTES = {
    'ivlemods.poll_ivle_folders.poll_ivle_folders': {'queue': 'ivle'},
    'ivlemods.poll_ivle_modules.poll_ivle_modules': {'queue': 'ivle'}
}