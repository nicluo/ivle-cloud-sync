from datetime import datetime, timedelta
import logging

from ivlemods.celery import celery
from ivlemods.dist import upload_dropbox_jobs, upload_user_dropbox_jobs
from ivlemods.database import db_session
from ivlemods.models import User, Job, IVLEFile, IVLEFolder
from ivlemods.poll_ivle_folders import poll_ivle_folders
from ivlemods.poll_ivle_modules import poll_ivle_modules
from ivlemods.ivle import IvleClient

logger = logging.getLogger(__name__)

@celery.task
def ivle_workbin_to_dropbox_job(user_id, duration=0):
    logger.info("Populating dropbox jobs.")
    user = User.query.get(user_id)
    if user.workbin_checked < datetime.now() - timedelta(minutes=duration):
        user.workbin_checked = datetime.now()
        db_session.commit()

        client = IvleClient(user.ivle_token)
        new_files = user.ivle_files.filter(IVLEFile.parent_folder.has(sync = True))\
                                   .filter(~IVLEFile.jobs.any()).all()

        for file in new_files:
            db_session.add(Job(file.ivle_id,\
                           client.build_download_url(file.ivle_id),\
                           'http',\
                           user.user_id,\
                           '/'.join([file.file_path, file.file_name])))
            file.dropbox_queued = datetime.now()
        db_session.commit()

@celery.task
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

@celery.task
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

@celery.task
def dropbox_login_resume_jobs(user_id):
    #resumes jobs that were paused because of missing dropbox login
    logger.info("Resuming file transfers for user %s because He/She had relogged in", user_id)
    for entry in Job.query.filter_by(status = 10).filter_by(user_id = user_id).all():
        entry.status = 0
        db_session.commit()
    upload_user_dropbox_jobs(user_id).delay()


@celery.task
def ivle_workbin_to_dropbox_jobs(duration=0):
    ivle_workbin_to_dropbox_job.starmap(
        [(id, duration) for id, in User.query.filter(
            User.workbin_checked < datetime.now() - timedelta(minutes=duration)
        ).values(User.user_id)]
    ).delay()

@celery.task
def poll_ivle_folders_for_all_users():
    poll_ivle_folders.map(
        [id for id, in User.query.values(User.user_id)]
    ).delay()

@celery.task
def poll_ivle_modules_for_all_users():
    poll_ivle_modules.map(
        [id for id, in User.query.values(User.user_id)]
    ).delay()

@celery.task
def one_task_to_rule_them_all():
    (poll_ivle_modules_for_all_users.si() | poll_ivle_folders_for_all_users.si() | ivle_workbin_to_dropbox_jobs.si(0) |
    upload_dropbox_jobs.si()).delay()
