from __future__ import absolute_import

from celery.schedules import crontab
from datetime import timedelta

BROKER_URL = 'redis://localhost:6379/0'
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_IMPORTS = ['ivlemods.tasks']
# CELERY_TIMEZONE = 'Singapore'
CELERYBEAT_SCHEDULE = {
    'one-task-every-20-minutes': {
        'task': 'ivlemods.tasks.one_task_for_them_all_no_callback',
        'schedule': timedelta(minutes=20),
        'args': ()
        },
    }
CELERY_ROUTES = {
    'ivlemods.poll_ivle_folders.poll_ivle_folders': {'queue': 'ivle'},
    'ivlemods.poll_ivle_modules.poll_ivle_modules': {'queue': 'ivle'},
    'ivlemods.tasks.queue_user_dropbox_jobs' : {'queue': 'celery'},
    'ivlemods.tasks_dropbox.wait_dropbox_job' : {'queue' : 'celery'},
    'ivlemods.tasks_dropbox.upload_dropbox_jobs' : {'queue' : 'celery'},
    'ivlemods.tasks_dropbox.retry_dropbox_jobs' : {'queue' : 'celery'},
    'ivlemods.tasks_dropbox.upload_user_dropbox_jobs' : {'queue' : 'celery'},
    'ivlemods.tasks_dropbox.retry_user_dropbox_jobs' : {'queue' : 'celery'},
    'ivlemods.tasks_dropbox.file_copier_task' : {'queue' : 'dropbox'},
    'ivlemods.tasks.one_task_on_user_flask' : {'queue' : 'flask'}
}
CELERY_RESULT_BACKEND = 'redis://'
