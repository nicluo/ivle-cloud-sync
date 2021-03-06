from __future__ import absolute_import
import logging

from celery import group
import ivlemods.dist as dist
from ivlemods.models import Job, User, Cache

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.task import SqlAlchemyTask
from ivlemods.dropbox_session import SessionHandler
from datetime import datetime

logger = logging.getLogger(__name__)

@celery.task(base=SqlAlchemyTask)
def wait_dropbox_job(job_id, time = 20):
    logger.info("Delaying file transfer %d by %d seconds" % (job_id, time))
    #time is in seconds
    entry = Job.query.filter_by(job_id = job_id).one()
    #update time of update, status 1 so it doesn't get queued again
    entry.status_update = datetime.now()
    entry.status = 1
    file_copier_task.apply_async(args=(entry.job_id, time), countdown=time)

@celery.task(base=SqlAlchemyTask)
def upload_dropbox_jobs():
    logger.info("Queueing file transfers for all users")
    group(upload_user_dropbox_jobs.s(id) for id in [id for id, in User.query.values(User.user_id)])()

@celery.task(base=SqlAlchemyTask)
def retry_dropbox_jobs():
    logger.info("Retrying file transfers for all users")
    group(retry_user_dropbox_jobs.s(id) for id in [id for id, in User.query.values(User.user_id)])()

@celery.task(base=SqlAlchemyTask)
def upload_dropbox_job_by_list(job_ids, callback=None):
    logger.debug('Uploading dropbox job by list, %s', job_ids)
    #set job statuses to 1
    for job_id in job_ids:
        job  = Job.query.get(job_id)
        job.status = 1
        job.status_update = datetime.now()
    db_session.commit()
    #create a group with the list of jobs
    jobs = group(file_copier_task.si(job_id) for job_id in job_ids)
    #chain with callback and delay
    if callback:
        (jobs | callback)()
    else:
        jobs()
        

@celery.task(base=SqlAlchemyTask)
def upload_user_dropbox_jobs(user_id):
    logger.info("Queueing file transfers for user %s", user_id)
    for entry in Job.query.filter_by(status = 0).filter_by(user_id = user_id).all():
        entry.status = 1
        db_session.commit()
        file_copier_task.delay(entry.job_id)

@celery.task(base=SqlAlchemyTask)
def retry_user_dropbox_jobs(user_id):
    logger.info("Retrying file transfers for user %s", user_id)
    max_retries = 5
    for entry in Job.query.filter(Job.status == 11, Job.status_retries < max_retries, Job.user_id == user_id).all():
        #update time of update, increment retries, set status 1 so it doesn't get queued again
        entry.status_update = datetime.now()
        entry.status_retries += 1
        entry.status = 1
        db_session.commit()
        file_copier_task.delay(entry.job_id)

@celery.task(base=SqlAlchemyTask)
def update_dropbox_quotas():
    logger.info("Updating dropbox quotas for all users")
    group(update_user_dropbox_quota.s(user_id) for user_id in [id for id, in User.query.filter(User.dropbox_key != None).values(User.user_id)]).delay()


@celery.task(base=SqlAlchemyTask)
def count_dropbox_jobs():
    logger.info('counting pending dropbox jobs')
    count = Job.query.filter_by(status = 1).count()
    return count

@celery.task(base=SqlAlchemyTask)
def update_user_dropbox_quota(user_id):
    logger.info('Updating dropbox quota info for user %s', user_id)
    sh = SessionHandler(user_id)
    info = sh.ignore_timeout(sh.client.account_info)()
    user = User.query.get(user_id)
    user.dropbox_uid = info['uid']
    user.dropbox_data_quota = info['quota_info']['quota']
    user.dropbox_data_normal = info['quota_info']['normal']
    user.dropbox_data_shared = info['quota_info']['shared']
    user.dropbox_data_datastores = info['quota_info']['datastores']
    user.dropbox_quota_checked = datetime.now() 
    db_session.commit()

@celery.task(base=SqlAlchemyTask)
def file_copier_task(job_id, time = 10):
    fc = dist.FileCopier(job_id, time * 2)
    fc.start()

@celery.task(base=SqlAlchemyTask)
#discretionary task to update file sizes
def update_all_file_sizes():
    for entry in Cache.query.filter(Cache.file_size == None).all():
        entry.file_size = dist.get_file_size('cache/'+entry.file_id)
    db_session.commit()
