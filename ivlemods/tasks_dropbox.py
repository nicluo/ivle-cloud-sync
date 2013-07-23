import logging

import ivlemods.dist as dist
from ivlemods.models import Job, User
from ivlemods.celery import celery
from ivlemods.database import db_session

logger = logging.getLogger(__name__)

@celery.task
def wait_dropbox_job(job_id, time = 20):
    #time is in seconds
    entry = Job.query.filter_by(job_id = job_id).one()
    fc = dist.FileCopier(entry.job_id)
    dist.FileCopier.start.apply_async(args=[fc], countdown=time)

@celery.task
def upload_dropbox_jobs():
    logger.info("Queueing file transfers for all users")
    upload_user_dropbox_jobs.map([id for id, in User.query.values(User.user_id)]).delay()

@celery.task
def retry_dropbox_jobs():
    logger.info("Retrying file transfers for all users")
    retry_user_dropbox_jobs.map([id for id, in User.query.values(User.user_id)]).delay()

@celery.task
def upload_user_dropbox_jobs(user_id):
    logger.info("Queueing file transfers for user %s", user_id)
    for entry in Job.query.filter_by(status = 0).filter_by(user_id = user_id).all():
        entry.status = 1
        db_session.commit()
        fc = dist.FileCopier(entry.job_id)
        dist.FileCopier.start.delay(fc)

@celery.task
def retry_user_dropbox_jobs(user_id):
    logger.info("Retrying file transfers for user %s", user_id)
    for entry in Job.query.filter_by(status = 11).filter_by(user_id = user_id).all():
        entry.status = 1
        db_session.commit()
        fc = dist.FileCopier(entry.job_id)
        dist.FileCopier.start.delay(fc)
