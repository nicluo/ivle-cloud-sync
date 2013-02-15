from datetime import datetime, timedelta

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import User, Job
from ivlemods.ivle import IvleClient

def explore_folders(user, client, json, parents):
    for folder in json['Folders']:
        folderName = folder['FolderName']
        for file in folder['Files']:
            fileName = file['FileName']
            fileID = file['ID']
            filePath = '/'.join(parents + [folderName] + [fileName])
            fileURL = client.build_download_url(fileID)
            db_session.add(Job(fileID, fileURL, 'http', user.user_id,
                filePath))
            db_session.commit()
        explore_folders(user, client, folder, parents + [folderName])


@celery.task
def ivle_workbin_to_dropbox_job(user_id, duration=0):
    user = User.query.get(user_id)
    if user.workbin_checked < datetime.now() - timedelta(minutes=duration):
        user.workbin_checked = datetime.now()
        db_session.commit()

        client = IvleClient(user.ivle_token)
        modules = client.get('Modules', Duration=0, IncludeAllInfo='false')
        for result in modules['Results']:
            courseCode = result['CourseCode']
            if result['isActive'] == 'Y':
                workbins = client.get('Workbins', CourseID=result['ID'],
                    Duration=0)
                for workbin in workbins['Results']:
                    title = workbin['Title']
                    explore_folders(user, client, workbin,
                        [courseCode + ' ' + title])


@celery.task
def ivle_workbin_to_dropbox_jobs(duration=0):
    ivle_workbin_to_dropbox_job.starmap(
        [(id, duration) for id, in User.query.filter(
            User.workbin_checked < datetime.now() - timedelta(minutes=duration)
        ).values(User.user_id)]
    ).delay()