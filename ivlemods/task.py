from __future__ import absolute_import
from celery.task import task
from celery.task import Task

from ivlemods.database import db_session

class SqlAlchemyTask(Task):
    """An abstract Celery Task that ensures that the connection the the
    database is closed on task completion"""
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        db_session.remove()
