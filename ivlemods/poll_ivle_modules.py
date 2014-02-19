import logging
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import IVLEModule, User
from ivlemods.ivle import IvleClient
from ivlemods.task import SqlAlchemyTask

from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

#use case: get_ivle_modules(user_id, duration(in minutes))
#e.g. get_ivle_modules(1, 5)
#returns dictionary of current active mods (deleted mods are omitted)


def get_ivle_modules(user_id, duration=0):
    user = User.query.filter(User.user_id == user_id).one()
    collection = user.ivle_modules.filter(IVLEModule.is_deleted == False)


    if not collection.count() or \
           collection.filter(IVLEModule.checked < datetime.now() - timedelta(minutes=duration)).count():
        poll_ivle_modules(user_id)

    db_user_modules = collection.all()

    user_modules = []
    for mod in db_user_modules:
        user_modules.append({"module_id" : mod.module_id,
                             "course_code" : mod.course_code,
                             "course_id" : mod.course_id,
                             "is_deleted" : mod.is_deleted})
    return user_modules

@celery.task(base=SqlAlchemyTask)
def poll_ivle_modules(user_id):
    logger.info("POLL - IVLE modules for user %s.", user_id)
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)
    modules = client.get('Modules', Duration=0, IncludeAllInfo='false')
    logger.debug(modules)

    #get current modules
    db_user_modules = user.ivle_modules

    user_course_ids = []
    for module in db_user_modules.filter_by(is_deleted = False).all():
        user_course_ids.append(module.course_id)

    #check all modules
    for result in modules['Results']:
        courseCode = result['CourseCode']
        courseId = result['ID']

        logger.debug('Processing %s' % (courseId))

        #fixes buggy response by ivle
        #should remove this if you want to view pending modules as well
        if is_null_module(courseId):
            logger.debug('Continuing %s' % (courseId))
            continue

        logger.debug('Still processing %s' % (courseId))

        if result['isActive'] == 'Y':
            #add missing modules
            if courseId not in user_course_ids:
                #check if the module has been deleted before
                deleted_module = user.ivle_modules.filter_by(course_code = courseCode,
                                                             course_id = courseId,
                                                             is_deleted = True)

                if deleted_module.count():
                    #restore deleted module, sounds great but this should never happen
                    revived_module = deleted_module.first()
                    revived_module.checked = datetime.now()
                    revived_module.is_deleted = False

                else:
                    #add new module
                    logger.info('Adding module %s to %d' % (courseId, user.user_id))
                    db_session.add(IVLEModule(result, user.user_id))

            #update checked modules with current timestamp
            else:
                try:
                    #check for currently active modules
                    #has to match course id to avoid 00000000-0000-0000-0000-000000000000
                    current_module = db_user_modules.filter_by(course_code = courseCode,
                                                               course_id = courseId,
                                                               is_deleted = False).one()
                    current_module.checked = datetime.now()

                except MultipleResultsFound:
                    #too many modules! trim
                    #delete everything
                    db_user_modules.filter_by(course_code = courseCode)\
                            .update({'is_deleted' : True, 'checked' : datetime.now()},
                        synchronize_session = False)

                    #restore only one
                    active_module = db_user_modules.filter_by(course_code = courseCode,
                                                              course_id = courseId).first()
                    logger.debug(active_module)
                    active_module.is_deleted = False

                except NoResultFound:
                    #alter module code
                    #should never happen since we ignore null modules
                    null_module = db_user_modules.filter_by(course_code = courseCode,
                                                            course_id = '00000000-0000-0000-0000-000000000000')
                    if(null_module.count()):
                        change_module = null_module.first()
                        change_module.checked = datetime.now()
                        change_module.course_id = result['ID']
                finally:
                    user_course_ids.remove(courseId)


    #delete all extra modules
    #these modules were not removed from earlier parts
    if(len(user_course_ids)):
        db_user_modules.filter(IVLEModule.course_id.in_(user_course_ids))\
                       .update({'is_deleted' : True, 'checked' : datetime.now()},
                   synchronize_session = False)

    #finally, commit the changes
    db_session.commit()
    
    return

def is_null_module(course_id):
    return course_id == '00000000-0000-0000-0000-000000000000'
