from datetime import datetime
import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread, IVLEFolder
from ivlemods.ivle import IvleClient


logger = logging.getLogger(__name__)

def get_folders(user_id, duration=0):
    logger.info("GET - Folders for user %s.", user_id)
    collection = IVLEFile.query.filter(IVLEFolder.user_id == user_id)\
        .filter(IVLEFile.is_deleted == False)\
        .all()
    poll = False
    for elem in collection:
        time_diff = datetime.now() - elem.checked
        if time_diff.total_seconds() > duration * 60:
            poll = True
    if poll or len(collection) == 0:
        poll_ivle_folders(user_id)
        collection = IVLEFolder.query.filter(IVLEFolder.user_id == user_id)\
            .filter(IVLEFolder.is_deleted == False)\
            .all()
    json = []
    for elem in collection:
        json.append({"type": "folder",
                     "ivle_id": elem.ivle_id,
                     "parent_id": elem.ivle_parent_id,
                     "workbin_id": elem.ivle_workbin_id,
                     "course_code": elem.course_code,
                     "path": elem.path,
                     "name": elem.name
                    })
    return json


@celery.task
def poll_ivle_folders(user_id):
    logger.info("POLL - IVLE folders for user %s.", user_id)
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)

    modules = client.get('Modules', Duration=0, IncludeAllInfo='false')
    for result in modules['Results']:
        courseCode = result['CourseCode']
        if result['isActive'] == 'Y':
            workbins = client.get('Workbins', CourseID=result['ID'], Duration=0)
            for workbin in workbins['Results']:
                title = workbin['Title']
                args = {
                    'user_id': user_id,
                    'course_code': courseCode,
                    'ivle_workbin_id': workbin['ID'],
                    'path': ' '.join([courseCode.replace("/", "+"), workbin['Title']])
                }
                exploreFolders(workbin, args)
        #print "------------"


def exploreFolders(json, args):
    user = User.query.filter(User.user_id == args['user_id']).one()
    client = IvleClient(user.ivle_token)
    for folder in json['Folders']:
        #add to IVLEFolder
        meta = dict.copy(args)
        meta['name'] = folder['FolderName']
        meta['path'] = '/'.join([meta['path'], meta['name']])
        meta['ivle_id'] = folder['ID']
        try:
            elem = IVLEFolder.query\
                .filter(IVLEFolder.user_id == meta['user_id'])\
                .filter(IVLEFolder.ivle_id == meta['ivle_id'])\
                .one()
            elem.checked = datetime.now()
            db_session.commit()
        except MultipleResultsFound as e:
            pass
        except NoResultFound as e:
            new_elem = IVLEFolder(meta)
            db_session.add(new_elem)
            db_session.commit()
        meta['ivle_parent_id'] = meta['ivle_id']
        for file in folder['Files']:
            #add to IVLEFile
            file_id = file['ID']
            file_path = meta['path']
            file_url = client.build_download_url(file_id)
            #print file_path
            #print file
            try:
                db_file = IVLEFile.query\
                .filter(IVLEFile.user_id == meta['user_id'])\
                .filter(IVLEFile.ivle_file_id == file_id)\
                .one()
                db_file.checked = datetime.now()
                db_session.commit()
            except MultipleResultsFound as e:
                pass
            except NoResultFound as e:
                new_ivle_file = IVLEFile({'user_id': meta['user_id'],\
                                          'course_code': meta['course_code'],\
                                          'ivle_workbin_id': meta['ivle_workbin_id'],\
                                          'ivle_file_id': file_id,\
                                          'ivle_folder_id': meta['ivle_id'],\
                                          'file_path': meta['path'],\
                                          'file_name': file['FileName'],\
                                          'file_type': file['FileType'],\
                                          'upload_time': datetime.strptime(file['UploadTime_js'][:19], "%Y-%m-%dT%H:%M:%S")})
                db_session.add(new_ivle_file)
                db_session.commit()
        exploreFolders(folder, meta)