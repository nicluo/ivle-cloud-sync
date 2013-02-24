from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Boolean, Text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import ForeignKey

from ivlemods.database import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    ivle_uid = Column(String(8))
    ivle_email = Column(String(32))
    ivle_name = Column(String(64))
    ivle_token = Column(String(416))
    dropbox_uid = Column(Integer)
    dropbox_key = Column(String(15))
    dropbox_secret = Column(String(15))
    workbin_checked = Column(DateTime)

    def __init__(self, ivle_uid, ivle_email, ivle_name, ivle_token,
                 dropbox_key=None, dropbox_secret=None):
        self.ivle_uid = ivle_uid
        self.ivle_email = ivle_email
        self.ivle_name = ivle_name
        self.ivle_token = ivle_token
        self.dropbox_key = dropbox_key
        self.dropbox_secret = dropbox_secret
        self.workbin_checked = datetime.now()

class Job(Base):
    __tablename__ = 'dropbox_jobs'

    job_id = Column(Integer, primary_key=True)
    file_id = Column(String(36))
    http_url = Column(String(1024))
    method = Column(String(4))
    user_id = Column(Integer)
    target_path = Column(String(256))
    status = Column(Integer)

    def __init__(self, file_id, http_url, method, user_id, target_path):
        self.file_id = file_id
        self.http_url = http_url
        self.method = method
        self.user_id = user_id
        self.target_path = target_path
        self.status = 0

class OnlineStore(Base):
    __tablename__ = 'dropbox_copy_ref_store'

    store_id = Column(Integer, primary_key=True)
    file_id = Column(String(50))
    dropbox_copy_ref = Column(String(100))
    dropbox_copy_ref_expiry = Column(Date)
    source_file_path = Column(String(200))
    source_user_id = Column(Integer)
    source_file_revision = Column(Integer)

    def __init__(self, job, copy_ref, uploaded_file_metadata):
        self.file_id = job.file_id
        self.dropbox_copy_ref = copy_ref["copy_ref"]
        self.dropbox_copy_ref_expiry = datetime.strptime(
            copy_ref['expires'][:25], "%a, %d %b %Y %H:%M:%S")
        self.source_file_path = uploaded_file_metadata["path"]
        self.source_user_id = job.user_id
        self.source_file_revision = uploaded_file_metadata["revision"]


class IVLEModule(Base):
    __tablename__ = 'ivle_module'

    module_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    course_code = Column(String(16))
    course_id = Column(String(36))
    checked = Column(DateTime)
    is_deleted = Column(Boolean)

    def __init__(self, module, user_id):
        self.user_id = user_id
        self.course_code = module["CourseCode"]
        self.course_id = module["ID"]
        self.checked = datetime.now()
        self.is_deleted = False


class IVLEFolder(Base):
    __tablename__ = 'ivle_folder'

    folder_id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.user_id'))
    ivle_id = Column(String(36))
    ivle_parent_id = Column(String(36))
    ivle_workbin_id = Column(String(36))
    course_code = Column(String(32))
    name = Column(String(256))
    path = Column(String(256))
    is_deleted = Column(Boolean)
    checked = Column(DateTime)
    sync = Column(Boolean)

    user = relationship(User, backref=backref('ivle_folders', lazy='dynamic'))

    def __init__(self, meta):
        if 'ivle_parent_id' in meta.keys():
            self.ivle_parent_id = meta['ivle_parent_id']
        self.user_id = meta['user_id']
        self.course_code = meta['course_code']
        self.ivle_id = meta['ivle_id']
        self.ivle_workbin_id = meta['ivle_workbin_id']
        self.course_code = meta['course_code']
        self.name = meta['name']
        self.path = meta['path']
        self.is_deleted = False
        self.checked = datetime.now()
        self.sync = True


class IVLEFile(Base):
    __tablename__ = 'ivle_file'

    file_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    ivle_workbin_id = Column(String(36))
    ivle_file_id = Column(String(36))
    ivle_folder_id = Column(String(36))
    course_code = Column(String(32))
    file_path = Column(String(256))
    file_name = Column(String(256))
    file_type = Column(String(8))
    upload_time = Column(DateTime)
    dropbox_uploaded_date = Column(DateTime)
    dropbox_revision = Column(Integer)
    is_deleted = Column(Boolean)
    checked = Column(DateTime)

    user = relationship(User, backref=backref('ivle_files', lazy='dynamic'))

    def __init__(self, meta):
        self.user_id = meta['user_id']
        self.course_code = meta['course_code']
        self.ivle_workbin_id = meta['ivle_workbin_id']
        self.ivle_file_id = meta['ivle_file_id']
        self.ivle_folder_id = meta['ivle_folder_id']
        self.course_code = meta['course_code']
        self.file_path = meta['file_path']
        self.file_name = meta['file_name']
        self.checked = datetime.now()
        self.is_deleted = False
        self.upload_time = meta['upload_time']
        self.file_type = meta['file_type']


class IVLEAnnouncement(Base):
    __tablename__ = 'ivle_announcement'

    announcement_id = Column(Integer, primary_key=True)
    ivle_id = Column(String(36))
    user_id = Column(Integer)
    course_code = Column(String(32))
    created_date = Column(DateTime)
    announcement_creator = Column(String(256))
    announcement_title = Column(String(256))
    announcement_body = Column(Text)
    modified_timestamp = Column(DateTime)
    is_read = Column(Boolean)
    is_deleted = Column(Boolean)
    checked = Column(DateTime)

    def __init__(self, announcement, course_code, user_id):
        self.user_id = user_id
        self.course_code = course_code
        self.created_date = datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
        self.ivle_id = announcement['ID']
        self.announcement_creator = announcement["Creator"]["Name"]
        self.announcement_title =  announcement["Title"]
        self.announcement_body = announcement["Description"]
        self.is_read = announcement["isRead"]
        self.modified_timestamp = datetime.now()
        self.is_deleted = False
        self.checked = datetime.now()

class IVLEForumHeading(Base):
    __tablename__ = 'ivle_forum_heading'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    course_code = Column(String(32))
    ivle_forum_id = Column(String(36))
    ivle_heading_id = Column(String(36))
    forum_title = Column(String(200))
    heading_title = Column(String(200))
    modified_timestamp = Column(DateTime)
    is_deleted = Column(Boolean)
    checked = Column(DateTime)

    def __init__(self, forum, heading, course_code, user_id):
        self.user_id = user_id
        self.course_code = course_code
        self.ivle_forum_id = forum['ID']
        self.ivle_heading_id = heading['ID']
        self.forum_title = forum['Title']
        self.heading_title = heading['Title']
        self.modified_timestamp = datetime.now()
        self.checked = datetime.now()
        self.is_deleted = False


class IVLEForumThread(Base):
    __tablename__ = 'ivle_forum_thread'

    id = Column(Integer, primary_key=True)
    ivle_id = Column(String(36))
    user_id = Column(Integer)
    course_code = Column(String(32))
    created_date = Column(DateTime)
    post_creator = Column(String(256))
    post_title = Column(String(256))
    post_body = Column(Text)
    parent_heading_id = Column(Integer)
    parent_thread_id = Column(Integer)
    modified_timestamp = Column(DateTime)
    is_deleted = Column(Boolean)
    checked = Column(DateTime)

    def __init__(self, thread, user_id, parent_heading_id, parent_thread_id, course_code):
        self.created_date = datetime.fromtimestamp(int(thread["PostDate"][6:16]))
        self.ivle_id = thread['ID']
        self.user_id = user_id
        self.course_code = course_code
        self.post_creator = thread["Poster"]["Name"]
        self.post_title = thread["PostTitle"]
        self.post_body = thread["PostBody"]
        self.parent_thread_id = parent_thread_id
        self.parent_heading_id = parent_heading_id
        self.modified_timestamp = datetime.now()
        self.checked = datetime.now()
        self.is_deleted = False
