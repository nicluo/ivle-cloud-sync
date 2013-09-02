from datetime import datetime
import logging

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import IVLEFile, User, IVLEFolder
from ivlemods.ivle import IvleClient
from ivlemods.task import SqlAlchemyTask

logger = logging.getLogger(__name__)

@celery.task(base=SqlAlchemyTask)
def poll_ivle_folders(user_id):
    logger.info("POLL - IVLE files, folders for user %s.", user_id)
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)

    #consolidate values from recursion
    folder_list = []
    file_list = []
    new_items = 0

    #use modules from IVLEModules table
    modules = user.ivle_modules.filter_by(is_deleted = False).all()
    for module in modules:
        courseCode = module.course_code
        workbins = client.get('Workbins', CourseID=module.course_id, Duration=0)
        for workbin in workbins['Results']:
            title = workbin['Title']
            args = {
                'user_id': user_id,
                'course_code': courseCode,
                'ivle_workbin_id': workbin['ID'],
                'path': ' '.join([courseCode.replace("/", "+").strip(), workbin['Title'].strip()])
                }
            result = exploreFolders(workbin, args)
            file_list += result['file_list']
            folder_list += result['folder_list']
            new_items += result['new']

    folder_deleted = user.ivle_folders.filter(IVLEFolder.ivle_id.in_(folder_list), IVLEFolder.is_deleted == True) \
                                      .update({'is_deleted': False, 'checked': datetime.now()}, synchronize_session=False)
    folder_restored = user.ivle_folders.filter(~IVLEFolder.ivle_id.in_(folder_list), IVLEFolder.is_deleted == False)\
                                       .update({'is_deleted': True, 'checked': datetime.now()}, synchronize_session=False)

    file_deleted = user.ivle_files.filter(IVLEFile.ivle_id.in_(file_list), IVLEFile.is_deleted == True) \
                                  .update({'is_deleted': False, 'checked': datetime.now()}, synchronize_session=False)
    file_restored = user.ivle_files.filter(~IVLEFile.ivle_id.in_(file_list), IVLEFile.is_deleted == False) \
                                     .update({'is_deleted': True, 'checked': datetime.now()}, synchronize_session=False)

    db_session.commit()
    return new_items


def exploreFolders(json, args):
    user = User.query.filter(User.user_id == args['user_id']).one()
    client = IvleClient(user.ivle_token)
    folder_list = []
    file_list = []
    new = 0
    for folder in json['Folders']:
        #add to IVLEFolder
        meta = dict.copy(args)
        meta['name'] = folder['FolderName']
        meta['path'] = '/'.join([meta['path'], meta['name'].strip()])
        meta['ivle_id'] = folder['ID']

        db_folder = user.ivle_folders.filter_by(ivle_id = meta['ivle_id'])
        if db_folder.count():
            db_folder.update({'checked' : datetime.now()})
        else:
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

            db_file = user.ivle_files.filter_by(ivle_id = file_id)
            if db_file.count():
                db_file.update({'checked' : datetime.now()}, synchronize_session=False)
            else:
                new_ivle_file = IVLEFile({'user_id': meta['user_id'],\
                                          'course_code': meta['course_code'],\
                                          'ivle_workbin_id': meta['ivle_workbin_id'],\
                                          'ivle_id': file_id,\
                                          'ivle_folder_id': meta['ivle_id'],\
                                          'file_path': meta['path'],\
                                          'file_name': file['FileName'],\
                                          'file_type': file['FileType'],\
                                          'upload_time': datetime.strptime(file['UploadTime_js'][:19], "%Y-%m-%dT%H:%M:%S")})
                db_session.add(new_ivle_file)
                new += 1
            db_session.commit()
            file_list.append(file_id)
        result = exploreFolders(folder, meta)
        folder_list += result['folder_list']
        file_list += result['file_list']
        new += result['new']
    return {'folder_list': folder_list, 'file_list': file_list, 'new': new}

