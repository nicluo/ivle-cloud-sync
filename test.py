from ivlemods import tasks
from ivlemods import poll_ivle_folders
from ivlemods.database import db_session
from ivlemods.models import IVLEFile, IVLEFolder, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread
from datetime import datetime
import time

from ivlemods.celery import celery

if User.query.filter(User.user_id == 1).count():
    print("using user 1")

    test_folder = IVLEFolder({
        'user_id': 1,
        'course_code': 'test_course',
        'ivle_id': 1,
        'ivle_workbin_id': 2,
        'name': 'test_folder',
        'path': '/test_course'
    })
    test_file = IVLEFile({
        'user_id': 1,
        'course_code': 'test_course',
        'ivle_workbin_id': 2,
        'ivle_file_id': 10,
        'ivle_folder_id': 1,
        'file_path': '/test_course/test_folder',
        'file_name': 'test_file.jpg',
        'upload_time': datetime.now(),
        'file_type': 'jpg'
    })
    db_session.add(test_folder)
    db_session.add(test_file)
    db_session.commit()
    result = poll_ivle_folders.poll_ivle_folders.delay(1)
    #should wait for task to complete
    time.sleep(20)

    test_folder = IVLEFolder.query.filter_by(user_id = 1).filter_by(ivle_id = 1).first()
    print("1 Test for folder removal from ivle")
    if test_folder.is_deleted == True:
        print("SUCCESS")
    else:
        print("FAILURE")

    print("2 Test for file removal from ivle")
    if test_file.is_deleted == True:
        print("SUCCESS")
    else:
        print("FAILURE")

    print("Cleaning up test entries")
    db_session.delete(test_file)
    db_session.delete(test_folder)
    db_session.commit()


