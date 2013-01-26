from app.database import db_session
from app.models import IVLEModule, User
from app.ivle import IvleClient
from datetime import datetime


#use case: get_ivle_modules(user_id, duration(in minutes))
#e.g. get_ivle_modules(1, 5)
#returns dictionary of current active mods (deleted mods are omitted)


def get_ivle_modules(user_id, duration):
    db_user_modules = IVLEModule.query.filter(IVLEModule.user_id == user_id)\
                                      .filter(IVLEModule.is_deleted == False)\
                                      .all()
    poll = False
    #check if stored values are expired
    for mod in db_user_modules:
        time_diff = datetime.now() - mod.checked
        if time_diff.total_seconds() > duration*60:
            poll = True
    #poll if stored values are expired
    if poll or len(db_user_modules) == 0:
        poll_ivle_modules(user_id)
        db_user_modules = IVLEModule.query.filter(IVLEModule.user_id == user_id)\
                                          .filter(IVLEModule.is_deleted == False)\
                                          .all()
    #populate the array of modules
    user_modules = []
    for mod in db_user_modules:
        user_modules.append({"module_id" : mod.module_id,
                             "course_code" : mod.course_code,
                             "course_id" : mod.course_id,
                             "is_deleted" : mod.is_deleted})
    #debug print user_modules
    return user_modules


def poll_ivle_modules(user_id):
    #get server values
    user = User.query.filter(User.user_id == user_id).one()
    client = IvleClient(user.ivle_token)
    modules = client.get('Modules', Duration=0, IncludeAllInfo='false')

    #get local values
    db_user_modules = IVLEModule.query.filter(IVLEModule.user_id == user_id)\
                                      .filter(IVLEModule.is_deleted == False)\
                                      .all()
    user_course_codes = []
    for module in db_user_modules:
        user_course_codes.append(module.course_code)

    #check all modules
    for result in modules['Results']:
        courseCode = result['CourseCode']
        if result['isActive'] == 'Y':
            #add missing modules
            if courseCode not in user_course_codes:
                db_session.add(IVLEModule(result, user.user_id))
                db_session.commit()
            #update checked modules with current timestamp
            elif courseCode in user_course_codes:
                ivle_module = IVLEModule.query.\
                    filter(IVLEModule.user_id == user.user_id).\
                    filter(IVLEModule.course_code == courseCode).one()
                ivle_module.checked = datetime.now()
                db_session.commit()
                user_course_codes.remove(courseCode)

    #delete all extra modules
    #these modules were not removed
    for course_code in user_course_codes:
        ivle_module = IVLEModule.query.\
                        filter(IVLEModule.user_id == user.user_id).\
                        filter(IVLEModule.course_code == course_code).one()
        ivle_module.is_deleted = True
        db_session.commit()