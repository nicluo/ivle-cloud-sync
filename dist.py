import os

import requests

from app.database import db_session
from app.models import User, Job, OnlineStore, History
from dropbox import client, rest, session

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

APP_KEY = 'br678pfbbwqbi1y'
APP_SECRET = '***REMOVED***'
ACCESS_TYPE = 'app_folder'

class SessionHandler():
    def __init__(self, user_id):
        user = User.query.get(user_id)
        sess = session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)
        sess.set_token(user.dropbox_key, user.dropbox_secret)
        self.client = client.DropboxClient(sess)


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
            with open('cache/' + self.job.file_id) as f:
                f.close()
                os.remove('cache/' + self.job.file_id)
                print "CACHE WARNING: have to delete existing file."
        except IOError as e:
            pass
        os.renames('cache/tmp', 'cache/' + self.job.file_id)


class FileProcessOverwrite():
    def __init__(self, dropbox_user_id, check_path):
        self.check_user_id = dropbox_user_id
        self.check_revision = 0
        self.check_path = "/" + check_path
        #self.check_path_original used for generating new renames
        self.check_path_original = self.check_path
        self.return_path = ""

        self.conflict_num = 0
        self.find_available_path()

    def find_available_path(self):
        print self.check_path
        if not self.target_file_exists():
            print "FileProcessOverwrite - target file doesnt exist, no need to overwrite"
            self.return_path = self.check_path
        else:
            print "FileProcessOverwrite - target file exists"
            if self.target_file_modified():
                print "FileProcessOverwrite - do not overwrite"
                self.make_new_path()
                self.find_available_path()
            else:
                print "FileProcessOverwrite - overwrite"
                self.return_path = self.check_path
                self.delete_target_file_path(self.check_path)

    def make_new_path(self):
        title, ext = os.path.splitext(self.check_path_original)
        self.conflict_num += 1
        self.check_path = title + " [renamed due to conflict: "\
                            + unicode(self.conflict_num)\
                            + "]" \
                            + ext
    
    def target_file_exists(self):
        SH = SessionHandler(self.check_user_id)
        try:
            meta = SH.client.metadata(self.check_path)
            if unicode('is_deleted') in meta.keys():
                if meta[unicode("is_deleted")]:
                    return False
            return True
        except rest.ErrorResponse as e:
            print e
            return False

        
    def target_file_modified(self):
        #if the file is in online store, and copy ref validates - file was never modified by user.
        SH = SessionHandler(self.check_user_id)
        meta = SH.client.metadata(self.check_path)
        print self.check_path
        try:
            result = OnlineStore.query\
                      .filter(OnlineStore.source_user_id == self.check_user_id)\
                      .filter(OnlineStore.source_file_path == self.check_path)\
                      .one()
                      
            self.check_revision = result.source_file_revision
            if meta["revision"] == self.check_revision:
                #the revision is consistent with the one we uploaded
                #the user has not modified
                print "FileProcessOverwrite: file not modified by user"
                return False
            else:
                #revision is inconsistent
                #user has modified
                print "FileProcessOverwrite: file modified by user"
                return True
            
        except MultipleResultsFound as e:
            #Shouldn't reach here
            #TODO: delete entries
            print "FileProcessOverwrite: Error - duplicate file entry"
            return True
        
        except NoResultFound as e:
            #file isn't in online store - either
            #1 we didn't upload it
            #2 it was already modified by the user
            #result - do not upload
            print "FileProcessOverwrite: no file entry found"
            return True

    def delete_target_file_path(self, path):
        SH = SessionHandler(self.check_user_id)
        print "FileProcessOverwrite - deleting file..."
        meta = SH.client.file_delete(path)
        print meta
        print "FileProcessOverwrite - file deleted"
        try:
            result = OnlineStore.query\
                      .filter(OnlineStore.source_user_id == self.check_user_id)\
                      .filter(OnlineStore.source_file_path == self.check_path)\
                      .one()
            db_session.delete(result)
            db_session.commit()
            print "FileProcessOverwrite - file entry deleted"
        except MultipleResultsFound as e:
            pass
        except NoResultFound as e:
            pass

    def get_target_file_path(self):
        return self.return_path[1:]
    


class FileCopier():
    def __init__(self, job):
        self.job = job
        self.job.status = 1
        FPO = FileProcessOverwrite(job.user_id, job.target_path)
        self.processed_path = FPO.get_target_file_path()
        
        self.SH = SessionHandler(1)
        self.cli = self.SH.client
        for entry in self.fetch_copy_ref_db(self.job.file_id):
            if self.check_copy_ref_validity(entry):
                try:
                    self.upload_copy_ref(entry.dropbox_copy_ref)
                    print "Copy: copy ref successful"
                    return
                except rest.ErrorResponse as e:
                    print "EX: copy ref failed."
                    self.remove_copy_ref_db(entry)
                    print "EX: Invalid entry removed."
            else:
                self.remove_copy_ref_db(entry)
        self.upload_file()


    def upload_file(self):
        print "Copy: Uploading Normally."
        FileFetch(self.job)
        f = open("cache/" + self.job.file_id, 'rb')
        response = self.cli.put_file(self.processed_path, f)
        print response
        f.close()

        self.put_into_copy_ref_store(response)
        self.log_file_copy(response["path"])

    def upload_copy_ref(self, copy_ref_entry):
        try:
            meta = self.cli.metadata(self.processed_path)
            if unicode('is_deleted') in meta.keys():
                if not meta[unicode("is_deleted")]:
                    print "Copy-Ref-Upload: Error - file exists in target folder"
                else:
                    print "file doesnt exist (deleted). go ahead upload"
                    response = self.cli.add_copy_ref(copy_ref_entry, self.processed_path)
                    print response
                    self.put_into_copy_ref_store(response)
                    self.log_file_copy(response["path"])
        except rest.ErrorResponse as e:
            print e
            print "file doesnt exist. go ahead upload"
            response = self.cli.add_copy_ref(copy_ref_entry, self.processed_path)
            print response
            self.put_into_copy_ref_store(response)
            self.log_file_copy(response["path"])


    def fetch_copy_ref_db(self, file_id):
        results = OnlineStore.query.filter(OnlineStore.file_id == file_id)
        return results

    def remove_copy_ref_db(self, store_obj):
        db_session.delete(store_obj)
        db_session.commit()

    def check_copy_ref_validity(self, copy_ref_entry):
        try:
            SH = SessionHandler(copy_ref_entry.source_user_id)
            meta = SH.client.metadata(copy_ref_entry.source_file_path)
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

        db_session.add(new_store)
        db_session.commit()

    def log_file_copy(self, target_path):
        new_history = History(self.job, target_path)
        db_session.add(new_history)
        db_session.commit()


class Worker():
    def __init__(self):
        for entry in Job.query\
            .filter(Job.status == 0)\
            .all():
            FileCopier(entry)


def main():
    Worker()

if __name__ == '__main__':
    main()
