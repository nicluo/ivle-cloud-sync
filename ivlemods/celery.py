from __future__ import absolute_import

from celery import Celery

celery = Celery()
import ivlemods.celeryconfig
celery.config_from_object(ivlemods.celeryconfig)

if __name__ == '__main__':
    celery.start()