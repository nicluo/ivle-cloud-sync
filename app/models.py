from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String

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


class Job(Base):
    __tablename__ = 'dropbox_jobs'

    job_id = Column(Integer, primary_key=True)
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(Integer)
    target_path = Column(String(200))
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
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(String(50))
    target_path = Column(String(200))

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
