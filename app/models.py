from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, Boolean

from app.database import Base

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

    def __init__(self, ivle_uid, ivle_email, ivle_name, ivle_token,
                 dropbox_key, dropbox_secret):
        self.ivle_uid = ivle_uid
        self.ivle_email = ivle_email
        self.ivle_name = ivle_name
        self.ivle_token = ivle_token
        self.dropbox_key = dropbox_key
        self.dropbox_secret = dropbox_secret

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


class History(Base):
    __tablename__ = 'dropbox_upload_history'

    history_id = Column(Integer, primary_key=True)
    job_id = Column(Integer)
    file_id = Column(String(36))
    http_url = Column(String(1024))
    method = Column(String(4))
    user_id = Column(Integer)
    target_path = Column(String(256))

    def __init__(self, job, target_path):
        self.job_id = job.job_id
        self.file_id = job.file_id
        self.http_url = job.http_url
        self.method = job.method
        self.user_id = job.user_id
        self.target_path = target_path


class IVLEFile(Base):
    __tablename__ = 'ivle_file'

    ivle_file_id = Column(Integer, primary_key=True)
    course_code = Column(String(16))
    created_date = Column(DateTime())
    file_id = Column(String(36))
    file_path = Column(String(256))
    file_type = Column(String(16))
    friendly_path = Column(String(256))

    def __init__(self, file):
        self.course_code = file['CourseCode']
        self.created_date = datetime.fromtimestamp(float(file['CreatedDate'][6:-2]) / 1000.0)
        self.file_id = file['FileID']
        self.file_path = file['FilePath']
        self.file_type = file['FileType']
        self.friendly_path = file['FriendlyPath']


class IVLEAnnouncement(Base):
    __tablename__ = 'ivle_announcement'

    ivle_announcement_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    course_code = Column(String(16))
    created_date = Column(DateTime())
    announcement_creator = Column(String(256))
    announcement_title = Column(String(256))
    announcement_body = Column(String(2048))
    modified_timestamp = Column(DateTime())
    is_deleted = Column(Boolean)

    def __init__(self, announcement, course_code, user_id):
        self.course_code = course_code
        self.created_date = datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
        self.ivle_announcement_id = announcement['ID']
        self.announcement_creator = announcement["Creator"]["Name"]
        self.announcement_title =  announcement["Title"]
        self.announcement_body = announcement["Description"]
        self.modified_timestamp = datetime.now()
        self.is_deleted = False


class IVLEForum(Base):
    __tablename__ = 'ivle_forum'

    ivle_forum_id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    course_code = Column(String(16))
    created_date = Column(DateTime())
    post_creator = Column(String(256))
    post_title = Column(String(256))
    post_body = Column(String(2048))
    parent_id = Column(Integer)
    modified_timestamp = Column(DateTime())
    is_deleted = Column(Boolean)

    def __init__(self, post, course_code, user_id, parent_id = 0):
        self.course_code = course_code
        self.created_date = datetime.fromtimestamp(int(announcement["CreatedDate"][6:16]))
        self.ivle_forum_id = post['ID']
        self.announcement_creator = psot["Creator"]["Name"]
        self.announcement_title =  post["Title"]
        self.announcement_body = post["Description"]
        self.modified_timestamp = datetime.now()
        self.parent_id = parent_id
        self.is_deleted = False
