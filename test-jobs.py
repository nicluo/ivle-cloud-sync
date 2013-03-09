from ivlemods import tasks
from ivlemods import poll_ivle_folders
from ivlemods.database import db_session
from ivlemods.models import IVLEFile, IVLEFolder, User, Job, IVLEAnnouncement, IVLEForumHeading, IVLEForumThread
from datetime import datetime
import time

from ivlemods.dist import *

from ivlemods.celery import celery

if User.query.filter(User.user_id == 1).count():
    print("using user 1")

    test_job = Job(10, "http://www.nicluo.com/html/test_cloud_sync/test_file.jpg", "http", 1, '/test_course/test_folder/test_file.jpg')
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

    # pause all pending jobs
    jobs = Job.query.filter_by(user_id = 1).filter_by(status = 0).all()
    for job in jobs:
        job.status = 6

    db_session.add(test_folder)
    db_session.add(test_file)
    db_session.add(test_job)
    db_session.commit()

    test_job.status = 0
    db_session.commit()

    user = User.query.filter_by(user_id = 1).first()
    key = user.dropbox_key
    secret = user.dropbox_secret
    user.dropbox_key = None
    user.dropbox_secret = None
    db_session.commit()
    upload_user_dropbox_jobs.delay(1)
    #should wait for task to complete
    time.sleep(10)

    user.dropbox_key = key
    user.dropbox_secret = secret
    db_session.commit()

    test_job = Job.query.filter_by(user_id = 1).filter_by(file_id = 10).first()
    print("1 Test for missing dropbox auth")
    if(test_job.status == 6):
        print("SUCCESS")
    else:
        print("FAILURE")

    test_folder = IVLEFolder.query.filter_by(user_id = 1).filter_by(ivle_id = 1).first()
    test_file = IVLEFile.query.filter_by(user_id = 1).filter_by(ivle_file_id = 10).first()

    print("Cleaning up test entries")
    #resume all pending jobs
    for job in jobs:
        job.status = 0
    db_session.delete(test_file)
    db_session.delete(test_folder)
    db_session.delete(test_job)
    db_session.commit()


    test_job = Job(10, "http://www.nicluo.com/html/test_cloud_sync/test_file.jpg", "http", 1, '/test_course/test_folder')
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

    # pause all pending jobs
    jobs = Job.query.filter_by(user_id = 1).filter_by(status = 0).all()
    for job in jobs:
        job.status = 6

    db_session.add(test_folder)
    db_session.add(test_file)
    db_session.add(test_job)
    db_session.commit()

    test_job.status = 6
    db_session.commit()

    upload_user_dropbox_jobs.delay(1)
    #should wait for task to complete
    time.sleep(20)

    test_job = Job.query.filter_by(user_id = 1).filter_by(file_id = 10).first()
    print("2 Test for job pause")
    if(test_job.status == 6):
        print("SUCCESS")
    else:
        print("FAILURE")

    test_folder = IVLEFolder.query.filter_by(user_id = 1).filter_by(ivle_id = 1).first()
    test_file = IVLEFile.query.filter_by(user_id = 1).filter_by(ivle_file_id = 10).first()

    print("Cleaning up test entries")
    #resume all pending jobs
    for job in jobs:
        job.status = 0
    db_session.delete(test_file)
    db_session.delete(test_folder)
    db_session.delete(test_job)
    db_session.commit()


    test_job = Job(10, "http://www.nicluo.com/html/test_cloud_sync/test_file.jpg", "http", 1, '/test_course/test_folder/test_file.jpg')
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

    # pause all pending jobs
    jobs = Job.query.filter_by(user_id = 1).filter_by(status = 0).all()
    for job in jobs:
        job.status = 6

    db_session.add(test_folder)
    db_session.add(test_file)
    db_session.add(test_job)
    db_session.commit()

    test_job.status = 0
    db_session.commit()

    upload_user_dropbox_jobs.delay(1)
    #should wait for task to complete
    time.sleep(60)

    test_job = Job.query.filter_by(user_id = 1).filter_by(file_id = 10).first()
    print("3 Test for job upload")
    if test_job.status == 2 or test_job.status == 3:
        print("SUCCESS")
    else:
        print("FAILURE")

    test_folder = IVLEFolder.query.filter_by(user_id = 1).filter_by(ivle_id = 1).first()
    test_file = IVLEFile.query.filter_by(user_id = 1).filter_by(ivle_file_id = 10).first()

    print("Cleaning up test entries")
    #resume all pending jobs
    for job in jobs:
        job.status = 0
    print(test_job.status)
    db_session.delete(test_file)
    db_session.delete(test_folder)
    db_session.delete(test_job)
    db_session.commit()
