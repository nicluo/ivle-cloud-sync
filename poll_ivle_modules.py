from app.database import db_session
from app.models import IVLEModule
from app.ivle import IvleClient
from datetime import datetime


def poll_ivle_modules(user):
    user = user
    client = IvleClient(user.ivle_token)
    db_user_modules = IVLEModule.query.filter(IVLEModule.user_id == user.user_id).all()
    user_course_codes = []
    for module in db_user_modules:
        user_course_codes.append(module.course_code)

    modules = client.get('Modules', Duration=0, IncludeAllInfo='false')

    for result in modules['Results']:
        courseCode = result['CourseCode']
        if result['isActive'] == 'Y':
            if courseCode not in user_course_codes:
                db_session.add(IVLEModule(result, user.user_id))
                db_session.commit()
            elif courseCode in user_course_codes:
                ivle_module = IVLEModule.query.\
                    filter(IVLEModule.user_id == user.user_id).\
                    filter(IVLEModule.course_code == courseCode).one()
                ivle_module.checked = datetime.now()
                user_course_codes.remove(courseCode)
                db_session.commit()

    #delete all extra modules
    #these modules were not removed
    for course_code in user_course_codes:
        ivle_module = IVLEModule.query.\
                        filter(IVLEModule.user_id == user.user_id).\
                        filter(IVLEModule.course_code == course_code).one()
        ivle_module.is_deleted = True
        db_session.commit()