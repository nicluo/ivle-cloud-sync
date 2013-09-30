from __future__ import absolute_import
from datetime import datetime, timedelta
import logging
import random
import redis 

from celery import subtask, group
from ivlemods.celery import celery
from ivlemods.tasks_dropbox import upload_dropbox_jobs, upload_user_dropbox_jobs, retry_dropbox_jobs, retry_user_dropbox_jobs, upload_dropbox_job_by_list
from ivlemods.database import db_session
from ivlemods.models import User, Job, IVLEFile, IVLEFolder
from ivlemods.poll_ivle_folders import poll_ivle_folders
from ivlemods.poll_ivle_modules import poll_ivle_modules
from ivlemods.ivle import IvleClient
from ivlemods.task import SqlAlchemyTask

from ivlemods.lock import try_lock, release_lock, compare_and_swap_int
from ivlemods.error import CacheMutex

r = redis.StrictRedis(host='localhost', port=6379, db=0)
logger = logging.getLogger(__name__)

@celery.task(base=SqlAlchemyTask)
def ivle_workbin_to_dropbox_job(user_id, duration=0, status=0):
    logger.info("Populating dropbox jobs for user %s.", user_id)
    user = User.query.get(user_id)
    if user.workbin_checked < datetime.now() - timedelta(minutes=duration):
        user.workbin_checked = datetime.now()
        db_session.commit()

        client = IvleClient(user.ivle_token)
        new_files = user.ivle_files.filter(IVLEFile.parent_folder.has(sync = True),
                                           ~IVLEFile.jobs.any(),
                                           ~IVLEFile.is_deleted).all()

        for file in new_files:
            db_session.add(Job(file.ivle_id,\
                           client.build_download_url(file.ivle_id),\
                           'http',\
                           user.user_id,\
                           '/'.join([file.file_path, file.file_name]),\
                           status))
            file.dropbox_queued = datetime.now()
        db_session.commit()
    return

@celery.task(base=SqlAlchemyTask)
def halt_user_dropbox_jobs(user_id):
    logging.info("unsubscribing jobs for user %s", user_id)
    user = User.query.get(user_id)
    sync_files = user.ivle_files.filter(IVLEFile.parent_folder.has(sync = False))\
                                    .filter(IVLEFile.jobs.any()).all()
    count = 0
    for file in sync_files:
        jobs = file.jobs.filter(Job.status == 0)
        for job in jobs:
            job.status = 6
            job.status_paused = 1
            count+=1
    db_session.commit()
    logging.info("%s jobs halted.", count)

@celery.task(base=SqlAlchemyTask)
def resume_user_dropbox_jobs(user_id):
    #resumes jobs that were due to folders not being synced
    logging.info("resubscribing jobs for user %s", user_id)
    user = User.query.get(user_id)
    sync_files = user.ivle_files.filter(IVLEFile.parent_folder.has(sync = True))\
                                    .filter(IVLEFile.jobs.any()).all()
    count = 0
    for file in sync_files:
        jobs = file.jobs.filter(Job.status == 6)
        for job in jobs:
            job.status = 0
            job.status_paused = 0
            count+=1
    db_session.commit()
    logging.info("%s jobs resumed.", count)

@celery.task(base=SqlAlchemyTask)
def dropbox_login_resume_jobs(user_id):
    #resumes jobs that were paused because of missing dropbox login
    logger.info("Resuming file transfers for user %s because He/She had relogged in", user_id)
    for entry in Job.query.filter_by(status = 10).filter_by(user_id = user_id).all():
        entry.status = 0
        db_session.commit()
    upload_user_dropbox_jobs.delay(user_id)

#priority for new log-ins
#calls task directly 
@celery.task(base=SqlAlchemyTask)
def one_task_on_user_flask(user_id):
    poll_ivle_modules(user_id)
    poll_ivle_folders(user_id)
    #token pass is invoked with call_no 0 to start a new token
    (queue_user_dropbox_jobs_flask.si(user_id) | token_pass_run_dropbox_jobs_flask.si(user_id, 0))()
    return

@celery.task(base=SqlAlchemyTask)
def one_task_for_them_all():
    (group((poll_ivle_modules.s(user_id) | poll_ivle_folders.si(user_id) | queue_user_dropbox_jobs.s(user_id)) for user_id in [user_id for user_id, in User.query.values(User.user_id)]) | one_task_callback.si())()
    return

@celery.task(base=SqlAlchemyTask)
def queue_user_dropbox_jobs(change, user_id):
    (ivle_workbin_to_dropbox_job.s(user_id) | upload_user_dropbox_jobs.si(user_id))()
    retry_user_dropbox_jobs.si(user_id)()
    return

@celery.task(base=SqlAlchemyTask)
def queue_user_dropbox_jobs_flask(user_id):
    ivle_workbin_to_dropbox_job(user_id, 0, 5) 
    return

@celery.task(base=SqlAlchemyTask)
def token_pass_run_dropbox_jobs_flask(user_id, call_no):
    logger.info('queueing initial dropbox jobs for user %s, call number %s', user_id, call_no)
    #timeout
    time = 20 
    loop = 1000
    next_no = call_no + 1
    if call_no == loop:
        next_no = 1

    user_list = [uid for uid, in Job.query.filter(Job.status == 5).values(Job.user_id)]
    user_list = list(set(user_list))
    logger.debug('potential users %s', user_list)
    if not len(user_list):
        next_user = None
        #release the token 
        r.set('token_new_user', 0)
        logger.debug('no next user')
    else:
        sort_small = []
        sort_big = []
        for elem in user_list:
            if elem > user_id:
                sort_big.append(elem)
            else:
                sort_small.append(elem)
        if len(sort_big):
            next_user = sorted(sort_big)[0]
        else:
            next_user = sorted(sort_small)[0]
        logger.debug(sort_big)
        logger.debug(sort_small)
        logger.debug('next user is %s', next_user)

    task_list = [job_id for job_id, in Job.query.filter(Job.user_id == user_id, Job.status == 5).values(Job.job_id)]
    if not len(task_list):
        #skip this user, he/she has no pending jobs
        #might happen because the check does not follow the queue.. i.e. all of the users initial jobs have just been queued.
        logger.debug('user %s has no pending initial jobs left', user_id)
        #use the same call number. because there are no callbacks waiting
        if(next_user):
            token_pass_run_dropbox_jobs_flask.delay(next_user, call_no)
        return
    elif len(task_list) < 10:
        #queue all
        pass
    else:
        random.shuffle(task_list)
        task_list = task_list[:10]
    logger.debug('tasks queued this round %s', task_list)

    #queue ten tasks, queue more when the tasks are completed
    if next_user:
        #direct call so jobs are queued immediately
        upload_dropbox_job_by_list(task_list, token_pass_callback.si(next_user, call_no, next_no))
        #redundant call for token pass callback as fallback
        #good for chunked uploads, failed tasks, so on so forth..
        token_pass_callback.apply_async(args=[next_user, call_no, next_no], countdown=time)
    else:
        #no callback
        upload_dropbox_job_by_list(task_list)

    return

@celery.task(base=SqlAlchemyTask)
def token_pass_callback(next_user, call_no, next_no):
    #is vulnerable to ABA problem. take note!
    if compare_and_swap_int('token_new_user', call_no, next_no):
        logger.debug('CAS succeeded, pass on')
        token_pass_run_dropbox_jobs_flask.delay(next_user, next_no)
    else:
        logger.debug('CAS failed, token has passed')
    return


@celery.task(base=SqlAlchemyTask)
def one_task_callback():
    #countdown of 30 seconds between runs
    one_task_for_them_all.apply_async(countdown=30)
    return
