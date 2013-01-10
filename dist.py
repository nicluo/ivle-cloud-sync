import cmd
import locale
import os
import pprint
import shlex
from datetime import datetime


import requests
from sqlalchemy import create_engine, Column, Integer, Date, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dropbox import client, rest, session


APP_KEY = 'f95et7cfm63kmay'
APP_SECRET = 'fasqu1bdz2w80pj'
ACCESS_TYPE = 'app_folder'

engine = create_engine('mysql+mysqldb://root:mieumieu@127.0.0.1:3306/dbdrop')
Session = sessionmaker(bind=engine)

class SessionHandler():
    def __init__(self, user_id):
        if APP_KEY == '' or APP_SECRET == '':
            exit("You need to set your APP_KEY and APP_SECRET!")
        self.sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
        if not self.fetch_authorization(user_id):
            self.handle_first_authorization()
        
    def fetch_authorization(self, user_id):
        self.session = Session()
        
        for entry in self.session.query(Auth).\
        filter(Auth.user_id == user_id):
            #try:
            self.sess.set_token(entry.dropbox_key, entry.dropbox_secret);
            self.client = client.DropboxClient(self.sess)
            #except Error as e:
            #    pass
            print "user %s loaded." % (self.client.account_info()["uid"])
            self.session.close()
            return True
        return False
    
    def handle_first_authorization(self):
        #produce the authorisation URL
        self.request_token = self.sess.obtain_request_token()

        #wait for authorization
        url = self.sess.build_authorize_url(self.request_token)
        print "url:", url
        print "Please press the 'Allow' button yo. Then press Enter to continue."
        raw_input()

        # This will fail if the user didn't visit the above URL and hit 'Allow'
        self.access_token = self.sess.obtain_access_token(self.request_token)
        print self.access_token.key, self.access_token.secret

        self.client = client.DropboxClient(self.sess)

        self.session = Session()
        new_user = Auth(self.client.account_info()["uid"], self.access_token.key, self.access_token.secret)

        self.session.add(new_user)
        self.session.commit()
        session.close()
        
    def get_client(self):
        return client.DropboxClient(self.sess)
        
Base = declarative_base()
class Auth(Base):
    __tablename__ = 'auth';

    user_id = Column(Integer, primary_key=True)
    dropbox_uid = Column(Integer)
    dropbox_key = Column(String(45))
    dropbox_secret = Column(String(45))

    def __init__(self, uid, key, secret):
        self.dropbox_uid = uid
        self.dropbox_key = key
        self.dropbox_secret = secret

    def __repr__(self):
        return "<User('%s','%s', '%s')>" % (self.dropbox_uid, self.dropbox_key, self.dropbox_secret)

class Jobs(Base):
    __tablename__ = 'dropbox_jobs'

    job_id = Column(Integer, primary_key = True)
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(String(50))
    target_path = Column(String(200))
    
    def __repr__(self):
        return "<Job('%s','%s', '%s')>" % (self.file_id, self.method, self.user_id)

class OnlineStore(Base):
    __tablename__ = 'dropbox_copy_ref_store'

    def __init__(self, job, copy_ref, uploaded_file_metadata):
        self.file_id = job.file_id
        self.dropbox_copy_ref = copy_ref["copy_ref"]
        self.dropbox_copy_ref_expiry = datetime.strptime(copy_ref['expires'][:25], "%a, %d %b %Y %H:%M:%S")
        self.source_file_path = uploaded_file_metadata["path"]
        self.source_user_id = job.user_id
        self.source_file_revision = uploaded_file_metadata["revision"]

    store_id = Column(Integer, primary_key = True)
    file_id = Column(String(50))
    dropbox_copy_ref = Column(String(100))
    dropbox_copy_ref_expiry = Column(Date)
    source_file_path = Column(String(200))
    source_user_id = Column(Integer)
    source_file_revision = Column(Integer)
    

class History(Base):
    __tablename__ = 'dropbox_upload_history'

    def __init__(self, job, target_path):
        self.job_id = job.job_id
        self.file_id = job.file_id
        self.http_url = job.http_url
        self.method = job.method
        self.user_id = job.user_id
        self.target_path = target_path

    history_id = Column(Integer, primary_key = True)
    job_id = Column(Integer)
    file_id = Column(String(50))
    http_url = Column(String(100))
    method = Column(String(10))
    user_id = Column(String(50))
    target_path = Column(String(200))
    
class FileFetch():
    def __init__(self, job):
        self.job = job
        if self.job.method == 'http':
             self.download_from_http()
        elif self.job.method == 'ivle':
             self.download_from_ivle()

    def check_cache(self):
        pass

    def add_to_cache(self):
        pass
    
    def download_from_http(self):
        print self.job.target_path + " downloading."
        r = requests.get(self.job.http_url)
        r.raise_for_status()
        print r.headers
        out = open('cache/tmp', 'wb')
        out.write(r.content)
        out.close()
        print self.job.target_path + " downloaded."
        try:
            with open('cache/'+self.job.target_path) as f:
                f.close()
                os.remove('cache/'+self.job.target_path)
                print "WARNING: have to delete existing file."
        except IOError as e:
            pass
        os.renames('cache/tmp', 'cache/'+self.job.target_path)

class FileProcessOverwrite():
    def __init__():
        pass

    def target_file_exists():
        pass

    def target_file_modified():
        pass

    

class FileCopier():
    def __init__(self, job):
        self.session = Session()
        self.job = job
        self.SH = SessionHandler(1)
        self.cli = self.SH.get_client()
        for entry in self.fetch_copy_ref_db(self.job.file_id):
            if self.check_copy_ref_validity(entry):
                try:
                    self.upload_copy_ref(entry.dropbox_copy_ref)
                    print "Copy: copy ref successful"
                    self.session.close()
                    return
                except rest.ErrorResponse as e:
                    print "EX: copy ref failed."
                    self.remove_copy_ref_db(entry)
                    print "EX: Invalid entry removed."
            else:
                self.remove_copy_ref_db(entry)
        self.upload_file()
        self.session.close()
        
    def upload_file(self):
        print "Copy: Uploading Normally."
        FileFetch(self.job)
        f = open("cache/" + self.job.target_path, 'rb')
        response = self.cli.put_file(self.job.target_path, f)
        print response
        f.close()
        
        self.put_into_copy_ref_store(response)
        self.log_file_copy(response["path"])

    def upload_copy_ref(self, copy_ref_entry):
        #TODO: check for existing file
        try:
            response = self.cli.metadata(self.job.target_path)
            print "Copy-Ref-Upload: File exists in target folder"
            print response
        except rest.ErrorResponse as e:
            print e
            print "file doesnt exist. go ahead upload"
            response = self.cli.add_copy_ref(copy_ref_entry.copy_ref, self.job.target_path)
            print response
            self.put_into_copy_ref_store(response)
            self.log_file_copy(response["path"])    
        

    def fetch_copy_ref_db(self, file_id):
        results = self.session.query(OnlineStore).filter(OnlineStore.file_id == file_id)
        return results

    def remove_copy_ref_db(self, store_obj):
        self.session.delete(store_obj)
        self.session.commit()
    
    def check_copy_ref_validity(self, copy_ref_entry):
        try:
            SH = SessionHandler(copy_ref_entry.source_user_id)
            meta = SH.get_client().metadata(copy_ref_entry.source_file_path)
            if meta["revision"] == copy_ref_entry.source_file_revision:
                print "copy-ref is valid!"
                return True
            else:
                print "copy-ref is not valid!"
                return False
        except rest.ErrorResponse as e:
            print "copy-ref error response..."
            return False

    def put_into_copy_ref_store(self, file_metadata):
        c_ref = self.cli.create_copy_ref(file_metadata["path"])
        new_store = OnlineStore(self.job, c_ref, file_metadata)

        self.session.add(new_store)
        self.session.commit()
                
    def log_file_copy(self, target_path):
        new_history = History(self.job, target_path)
        self.session.add(new_history)
        self.session.commit()

class Worker():
    def __init__(self):
        self.session = Session()
        for entry in self.session.query(Jobs):
           FileCopier(entry)
        self.session.close()

def main():
##    SH = SessionHandler(1)
##    c_ref = SH.get_client().create_copy_ref("/file2.txt")["copy_ref"]
##    c_ref2 = SH.get_client().create_copy_ref("/file2.txt")["copy_ref"]
##    print SH.get_client().metadata("/file2.txt")
##    print c_ref
##    print c_ref2
##    print "edit"
##    raw_input()
##    
##    print SH.get_client().metadata("/file2.txt")
##    print SH.get_client().add_copy_ref(c_ref, "/try/file2.txt")
##    raw_input()

    #folder_metadata = cli.metadata('/')
    #print folder_metadata

    #copy_ref = cli.create_copy_ref("/file2.txt")['copy_ref']
    #print copy_ref
    #response = cli.add_copy_ref(copy_ref, "/hello.txt")

    #f, metadata = cli.get_file_and_metadata('/file2.txt')
    #out = open('magnum-opus.txt', 'w')
    #out.write(f.read())
    #out.close()

    #f = open('files/file2.txt', 'rb')
    #response = cli.put_file('/file2.txt', f)
    
    Worker()
    
if __name__ == '__main__':
    main()
