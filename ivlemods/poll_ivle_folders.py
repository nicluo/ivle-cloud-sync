from ivlemods.database import db_session
from ivlemods.models import IVLEFile, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread, IVLEFolder
from ivlemods.ivle import IvleClient
from datetime import datetime
import logging

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

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
    meta = dict.copy(args)
    for folder in json['Folders']:
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
        exploreFolders(folder, meta)