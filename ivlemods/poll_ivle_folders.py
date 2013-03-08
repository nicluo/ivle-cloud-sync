from datetime import datetime
import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread, IVLEFolder
from ivlemods.ivle import IvleClient


logger = logging.getLogger(__name__)

def request_folders(user_id, duration=0):
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


@celery.task
def poll_ivle_folders(user_id):
    logger.info("POLL - IVLE files, folders for user %s.", user_id)
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)

    folder_list = []
    file_list = []

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
                result = exploreFolders(workbin, args)
                file_list += result['file_list']
                folder_list += result['folder_list']

    folder_collection = IVLEFolder.query.filter_by(user_id = user_id).all()
    for folder in folder_collection:
        if folder.ivle_id in folder_list:
            folder.is_deleted = False
        else:
            folder.is_deleted = True

    file_collection = IVLEFile.query.filter_by(user_id = user_id).all()
    for file in file_collection:
        if file.ivle_file_id in file_list:
            file.is_deleted = False
        else:
            file.is_deleted = True

    db_session.commit()


def exploreFolders(json, args):
    user = User.query.filter(User.user_id == args['user_id']).one()
    client = IvleClient(user.ivle_token)
    folder_list = []
    file_list = []
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
        folder_list.append(meta['ivle_id'])

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
            file_list.append(file_id)
        result = exploreFolders(folder, meta)
        folder_list += result['folder_list']
        file_list += result['file_list']
    return {'folder_list': folder_list, 'file_list': file_list}