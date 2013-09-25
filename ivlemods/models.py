from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Boolean, Text, BigInteger
from sqlalchemy.orm import backref, relationship
from sqlalchemy.schema import ForeignKey
from sqlalchemy.sql.expression import text

from ivlemods.database import Base

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    ivle_uid = Column(String(8))
    ivle_email = Column(String(32))
    ivle_name = Column(String(64))
    ivle_token = Column(String(416))
    dropbox_uid = Column(Integer)
    dropbox_key = Column(String(16))
    dropbox_secret = Column(String(15))
    dropbox_data_quota = Column(BigInteger)
    dropbox_data_normal = Column(BigInteger)
    dropbox_data_shared = Column(BigInteger)
    dropbox_data_datastores = Column(BigInteger)
    dropbox_quota_checked = Column(DateTime)
    workbin_checked = Column(DateTime)

    def __init__(self, ivle_uid, ivle_email, ivle_name, ivle_token,
            dropbox_key=None, dropbox_secret=None, 
	    quota_info={'shared': None, 'quota':None, 'normal':None, 'datastores':None}):
        self.ivle_uid = ivle_uid
        self.ivle_email = ivle_email
        self.ivle_name = ivle_name
        self.ivle_token = ivle_token
        self.dropbox_key = dropbox_key
        self.dropbox_secret = dropbox_secret
        self.dropbox_data_quota = quota_info['quota'] 
        self.dropbox_data_normal = quota_info['normal']
        self.dropbox_data_shared = quota_info['shared']
        self.dropbox_data_datastores = quota_info['datastores']
        self.workbin_checked = datetime.now()


class IVLEFolder(Base):
    __tablename__ = 'ivle_folder'

    folder_id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('users.user_id'))
    ivle_id = Column(String(36))
    ivle_parent_id = Column(String(36))
    ivle_workbin_id = Column(String(36))
    course_code = Column(String(64))
    name = Column(String(256))
    path = Column(String(256))
    is_deleted = Column(Boolean)
    checked = Column(DateTime)
    sync = Column(Boolean)

    user = relationship("User", backref=backref('ivle_folders', lazy='dynamic'))
    parent_folder = relationship("IVLEFolder", primaryjoin = "and_(IVLEFolder.ivle_parent_id == IVLEFolder.ivle_id, IVLEFolder.user_id == IVLEFolder.user_id)",
                                 foreign_keys = [ivle_parent_id, user_id],
                                 remote_side = [ivle_id, user_id],
                                 backref=backref('folders', lazy='dynamic'))


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
    ivle_id = Column(String(36), nullable=False)
    ivle_folder_id = Column(String(36))
    course_code = Column(String(64))
    file_path = Column(String(256))
    file_name = Column(String(256))
    file_type = Column(String(8))
    upload_time = Column(DateTime)
    dropbox_queued = Column(DateTime)
    dropbox_uploaded_date = Column(DateTime)
    dropbox_rev= Column(String(11))
    is_deleted = Column(Boolean)
    checked = Column(DateTime)

    parent_folder = relationship("IVLEFolder", primaryjoin = "and_(IVLEFile.ivle_folder_id == IVLEFolder.ivle_id,"
                                                             " IVLEFile.user_id == IVLEFolder.user_id)",
                                 foreign_keys = [ivle_folder_id, user_id],
                                 remote_side = [IVLEFolder.ivle_id, IVLEFolder.user_id],
                                 backref=backref('files', lazy='dynamic'))

    user = relationship(User, backref=backref('ivle_files', lazy='dynamic'))

    def __init__(self, meta):
        self.user_id = meta['user_id']
        self.course_code = meta['course_code']
        self.ivle_workbin_id = meta['ivle_workbin_id']
        self.ivle_id = meta['ivle_id']
        self.ivle_folder_id = meta['ivle_folder_id']
        self.file_path = meta['file_path']
        self.file_name = meta['file_name']
        self.checked = datetime.now()
        self.is_deleted = False
        self.upload_time = meta['upload_time']
        self.file_type = meta['file_type']

class Cache(Base):
    __tablename__ = 'file_cache'

    cache_id = Column(Integer, primary_key=True)
    file_id = Column(String(36))
    http_url = Column(String(1024))
    method = Column(String(4))
    download_user_id = Column(Integer, ForeignKey('users.user_id'))
    date_added = Column(DateTime, default = datetime.now)
    path = Column(String(1024))
    status = Column(Integer, server_default=text('0'))
    status_update = Column(DateTime, default = datetime.now, onupdate = datetime.now)
    status_started = Column(DateTime)
    status_completed = Column(DateTime)
    status_fail = Column(Integer, server_default=text('0'))
    status_retries = Column(Integer, server_default=text('0'))
    file_size = Column(BigInteger)

    user = relationship("User")

    def __init__(self, meta):
        self.file_id = meta['file_id']
        self.http_url = meta['http_url']
        self.method = meta['method']
        self.download_user_id = meta['download_user_id']
        self.file_size = meta['file_size']

class Job(Base):
    __tablename__ = 'dropbox_jobs'

    job_id = Column(Integer, primary_key=True)
    file_id = Column(String(36))
    http_url = Column(String(1024))
    method = Column(String(4))
    user_id = Column(Integer, ForeignKey('users.user_id'))
    target_path = Column(String(256))
    date_added = Column(DateTime, default=datetime.now)
    status_update = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    status_started = Column(DateTime)
    status_retry = Column(DateTime)
    status_completed = Column(DateTime)
    status = Column(Integer, server_default=text('0'))
    status_retries = Column(Integer, server_default = text('0'))
    status_upload = Column(Integer, server_default=text('0'))
    status_copy_ref = Column(Integer, server_default=text('0'))
    status_paused = Column(Integer, server_default=text('0'))

    ivle_file = relationship("IVLEFile",
                             primaryjoin = "and_(Job.file_id == IVLEFile.ivle_id, Job.user_id == IVLEFile.user_id)",
                             foreign_keys = [file_id, user_id],
                             remote_side = [IVLEFile.ivle_id, IVLEFile.user_id],
                             backref = backref('jobs', lazy='dynamic'))
    user = relationship("User", backref=backref('jobs', lazy='dynamic'))
    cache = relationship("Cache",
                         primaryjoin = "Job.file_id == Cache.file_id",
                         foreign_keys = [file_id],
                         remote_side = [Cache.file_id],
                         backref = backref('jobs', lazy='dynamic'))

    def __init__(self, file_id, http_url, method, user_id, target_path, status=0):
        self.file_id = file_id
        self.http_url = http_url
        self.method = method
        self.user_id = user_id
        self.target_path = target_path
        self.status = status



class OnlineStore(Base):
    __tablename__ = 'dropbox_store'

    store_id = Column(Integer, primary_key=True)
    file_id = Column(String(50))
    dropbox_copy_ref = Column(String(100))
    dropbox_copy_ref_expiry = Column(Date)
    source_file_path = Column(String(200))
    source_uploaded_path = Column(String(200))
    source_user_id = Column(Integer, ForeignKey('users.user_id'))
    source_file_rev= Column(String(11))
    is_valid = Column(Boolean, server_default =text('0'), default=True)
    date_added = Column(DateTime, default = datetime.now)

    def __init__(self, job, copy_ref, uploaded_file_metadata):
        self.file_id = job.file_id
        self.dropbox_copy_ref = copy_ref["copy_ref"]
        self.dropbox_copy_ref_expiry = datetime.strptime(
            copy_ref['expires'][:25], "%a, %d %b %Y %H:%M:%S")
        self.source_file_path = job.target_path 
        self.source_uploaded_path = uploaded_file_metadata["path"]
        self.source_user_id = job.user_id
        self.source_file_rev= uploaded_file_metadata["rev"]


class IVLEModule(Base):
    __tablename__ = 'ivle_module'

    module_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    course_code = Column(String(64))
    course_id = Column(String(36))
    checked = Column(DateTime, default=datetime.now)
    is_deleted = Column(Boolean, server_default=text('0'), default=False)

    user = relationship("User", backref=backref('ivle_modules', lazy='dynamic'))

    def __init__(self, module, user_id):
        self.user_id = user_id
        self.course_code = module['CourseCode']
        self.course_id = module['ID']


class IVLEAnnouncement(Base):
    __tablename__ = 'ivle_announcement'

    announcement_id = Column(Integer, primary_key=True)
    ivle_id = Column(String(36))
    user_id = Column(Integer)
    course_code = Column(String(64))
    created_date = Column(DateTime)
    announcement_creator = Column(String(256))
    announcement_title = Column(String(256))
    announcement_body = Column(Text)
    modified_timestamp = Column(DateTime)
    is_read = Column(Boolean)
    is_deleted = Column(Boolean, server_default=text('0'), default=False)
    checked = Column(DateTime, default=datetime.now)

    def __init__(self, announcement, course_code, user_id):
        self.user_id = user_id
        self.course_code = course_code
        self.created_date = datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
        self.ivle_id = announcement['ID']
        self.announcement_creator = announcement["Creator"]["Name"]
        self.announcement_title =  announcement["Title"]
        self.announcement_body = announcement["Description"]
        self.is_read = announcement["isRead"]

class IVLEForumHeading(Base):
    __tablename__ = 'ivle_forum_heading'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    course_code = Column(String(64))
    ivle_forum_id = Column(String(36))
    ivle_heading_id = Column(String(36))
    forum_title = Column(String(200))
    heading_title = Column(String(200))
    modified_timestamp = Column(DateTime)
    is_deleted = Column(Boolean, server_default=text('0'), default=False)
    checked = Column(DateTime, default=datetime.now)

    def __init__(self, forum, heading, course_code, user_id):
        self.user_id = user_id
        self.course_code = course_code
        self.ivle_forum_id = forum['ID']
        self.ivle_heading_id = heading['ID']
        self.forum_title = forum['Title']
        self.heading_title = heading['Title']
        self.modified_timestamp = datetime.now()


class IVLEForumThread(Base):
    __tablename__ = 'ivle_forum_thread'

    id = Column(Integer, primary_key=True)
    ivle_id = Column(String(36))
    user_id = Column(Integer)
    course_code = Column(String(64))
    created_date = Column(DateTime)
    post_creator = Column(String(256))
    post_title = Column(String(256))
    post_body = Column(Text)
    parent_heading_id = Column(Integer)
    parent_thread_id = Column(Integer)
    modified_timestamp = Column(DateTime)
    is_deleted = Column(Boolean, server_default=text('0'), default=False)
    checked = Column(DateTime, default=datetime.now)

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
