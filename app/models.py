from datetime import datetime

from sqlalchemy import Column, Date, Integer, String

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


class Jobs(Base):
    __tablename__ = 'dropbox_jobs'

    job_id = Column(Integer, primary_key=True)
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(String(50))
    target_path = Column(String(200))


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

    def __init__(self, job, target_path):
        self.job_id = job.job_id
        self.file_id = job.file_id
        self.http_url = job.http_url
        self.method = job.method
        self.user_id = job.user_id
        self.target_path = target_path

    history_id = Column(Integer, primary_key=True)
    job_id = Column(Integer)
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(String(50))
    target_path = Column(String(200))