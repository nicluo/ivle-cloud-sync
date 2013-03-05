from datetime import datetime, timedelta
import logging

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import User, Job, IVLEFile, IVLEFolder
from ivlemods.ivle import IvleClient

logger = logging.getLogger(__name__)

@celery.task
def ivle_workbin_to_dropbox_job(user_id, duration=0):
    logger.info("Populating dropbox jobs.")
    user = User.query.get(user_id)
    if user.workbin_checked < datetime.now() - timedelta(minutes=duration):
        user.workbin_checked = datetime.now()
        db_session.commit()

        folders = IVLEFolder.query.filter(IVLEFolder.user_id == user_id)\
                                  .filter(IVLEFolder.sync == True)

        client = IvleClient(user.ivle_token)

        for folder in folders:
            files = IVLEFile.query.filter(IVLEFile.user_id == user_id)\
                                  .filter(IVLEFile.ivle_folder_id == folder.ivle_id)

            for file in files:
                job_count = Job.query.filter(Job.user_id == user_id)\
                                     .filter(Job.file_id == file.ivle_file_id)\
                                     .count()
                if job_count == 0:
                    db_session.add(Job(file.ivle_file_id,\
                                       client.build_download_url(file.ivle_file_id),\
                                       'http',\
                                       user.user_id,\
                                       '/'.join([file.file_path, file.file_name])))
                    db_session.commit()

@celery.task
def halt_user_dropbox_jobs(user_id):
    user = User.query.get(user_id)
    folders = IVLEFolder.query.filter(IVLEFolder.user_id == user_id)\
        .filter(IVLEFolder.sync == False)
    client = IvleClient(user.ivle_token)
    for folder in folders:
        files = IVLEFile.query.filter(IVLEFile.user_id == user_id)\
            .filter(IVLEFile.ivle_folder_id == folder.ivle_id)
        for file in files:
            jobs = Job.query.filter(Job.user_id == user_id)\
            .filter(Job.file_id == file.ivle_file_id)
            for job in jobs:
                job.status = 6
                db_session.commit()

@celery.task
def ivle_workbin_to_dropbox_jobs(duration=0):
    ivle_workbin_to_dropbox_job.starmap(
        [(id, duration) for id, in User.query.filter(
            User.workbin_checked < datetime.now() - timedelta(minutes=duration)
        ).values(User.user_id)]
    ).delay()