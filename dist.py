import os

import requests

from app.database import db_session
from app.models import User, Job, OnlineStore, History
from dropbox import client, rest, session

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
            with open('cache/' + self.job.target_path) as f:
                f.close()
                os.remove('cache/' + self.job.target_path)
                print "WARNING: have to delete existing file."
        except IOError as e:
            pass
        os.renames('cache/tmp', 'cache/' + self.job.target_path)


class FileProcessOverwrite():
    def __init__(self):
        pass

    def target_file_exists(self):
        pass

    def target_file_modified(self):
        pass


class FileCopier():
    def __init__(self, job):
        self.job = job
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
            response = self.cli.add_copy_ref(copy_ref_entry.copy_ref,
                self.job.target_path)
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
        for entry in Job.query.all():
            FileCopier(entry)


def main():
    Worker()

if __name__ == '__main__':
    main()
