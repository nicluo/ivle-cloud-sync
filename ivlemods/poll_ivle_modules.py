import logging

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

    #get current modules
    db_user_modules = user.ivle_modules.filter_by(is_deleted = False)

    user_course_codes = []
    for module in db_user_modules.all():
        user_course_codes.append(module.course_code)

    #check all modules
    for result in modules['Results']:
        courseCode = result['CourseCode']
        if result['isActive'] == 'Y':
            #add missing modules
            if courseCode not in user_course_codes:
                #check if the module has been deleted before
                deleted_module = user.ivle_modules.filter_by(course_code = courseCode,
                                                             is_deleted = True,
                                                             course_id = result['ID'])
                if deleted_module.count():
                    #restore deleted module, sounds great but this should never happen
                    deleted_module.update({'is_deleted' : False, 'checked' : datetime.now()}, 
					  synchronize_session=False)
                else:
                    #add new module
                    db_session.add(IVLEModule(result, user.user_id))

            #update checked modules with current timestamp
            elif courseCode in user_course_codes:
                #check for unopened modules
                null_module = db_user_modules.filter_by(course_code = courseCode)\
                                             .filter_by(course_id = '00000000-0000-0000-0000-000000000000')
                if(null_module.count()):
                    null_module.update({'course_id':result['ID']}, synchronize_session=False)
                db_user_modules.filter_by(course_code = courseCode)\
                               .update({'checked' : datetime.now()},
					synchronize_session = False)
                user_course_codes.remove(courseCode)

    #delete all extra modules
    #these modules were not removed from earlier parts
    db_user_modules.filter(IVLEModule.course_code.in_(user_course_codes))\
                   .update({'is_deleted' : True, 'checked' : datetime.now()},
			   synchronize_session = False)

    #finally, commit the changes
    db_session.commit()
    
    return

def is_null_module(course_id):
    return course_id == '00000000-0000-0000-0000-000000000000'
