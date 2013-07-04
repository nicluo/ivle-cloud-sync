import os
import logging
import requests
import traceback
import redis

from dropbox import client, rest, session
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from datetime import datetime

from ivlemods import app
from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import User, Job, OnlineStore, IVLEFile, Cache

logger = logging.getLogger(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)

class SessionHandler():
    def __init__(self, user_id):
        user = User.query.get(user_id)
        logger.debug("Session - logging in as user %s", user.user_id)
        if user.dropbox_key == None or user.dropbox_secret == None:
            raise Exception("DROPBOX_USR_ERR")

        sess = session.DropboxSession(app.config['DROPBOX_APP_KEY'],
            app.config['DROPBOX_APP_SECRET'], app.config['DROPBOX_ACCESS_TYPE'])
        sess.set_token(user.dropbox_key, user.dropbox_secret)
        self.client = client.DropboxClient(sess)
    
    def ignore_timeout(self, func):
        def retry(*args, **kwargs):
            complete = False
            while not complete:
                try:
                    meta = func(*args, **kwargs)
                    return meta
                except rest.RESTSocketError as e:
                    logger.debug('TIMEOUT DETECTED')
                    #ignore timeouts
                    pass
        return retry


class FileFetch():
    def __init__(self, job):
        self.job = job
        if not self.job.cache == None:
            return
        else:
            #check entry, check mutex and wait
            while self.job.cache == None:
                mutex_is_locked = r.getset(self.job.file_id, '1') == '1'
                if mutex_is_locked:
                    sleep(2)
                else:
                    #mutex is yours
                    try:
                        if self.job.cache == None:
                            #go ahead and download
                            if self.job.method == 'http':
                                self.download_from_http()
                            #there is no entry
                            #create cache entry
                            self.create_cache_entry()
                            #commit cache entry
                    except:
                        r.set(self.job.file_id, 'None')
                        raise
                    else:
                        r.set(self.job.file_id, 'None')
                        return

    def create_cache_entry(self):
        new_cache = Cache({'file_id':self.job.file_id,
                           'http_url':self.job.http_url,
                           'method':self.job.method,
                           'download_user_id':self.job.user_id})
        db_session.add(new_cache)
        db_session.commit()

    def download_from_http(self):
        download = requests.get(self.job.http_url)
        download.raise_for_status()
        logger.debug(download.headers)

        #ensure proper, empty temp file for the cache to use
        cache_path = 'cache/tmp'
        self.ensure_directory(cache_path)
        cache_path = self.find_unused(cache_path)
        out = open(cache_path, 'wb')
        out.write(download.content)
        out.close()
        logger.debug(self.job.target_path + " downloaded to " + cache_path + ".")
        self.delete_if_exists('cache/' + self.job.file_id)
        os.renames(cache_path, 'cache/' + self.job.file_id)

    def ensure_directory(self, f):
        d = os.path.dirname(f)
        if not os.path.exists(d):
            os.makedirs(d)

    def delete_if_exists(self, path):
        if os.path.exists(path):
            os.remove(path)
            logger.debug("Cache - have to delete existing file.")
        return

    def find_unused(self, original_path):
        check_path = original_path
        conflict_num = 0
        while(os.path.exists(check_path)):
            title, ext = os.path.splitext(original_path)
            check_path = title + str(conflict_num) + ext
        return check_path

class FileProcessOverwrite():
    def __init__(self, user_id, check_path):
        self.check_user_id = user_id
        self.check_revision = 0
        self.check_path = check_path

        self.sh = SessionHandler(user_id)
        self.cli = self.sh.client


        #self.check_path_original used for generating new renames
        self.check_path_original = self.check_path
        self.return_path = ""

        self.conflict_num = 0
        self.find_available_path()

    def find_available_path(self):
        logger.debug(self.check_path)
        if not self.target_file_exists():
            logger.debug("FileProcessOverwrite - target file doesnt exist, no need to overwrite")
            self.return_path = self.check_path
        else:
            logger.debug("FileProcessOverwrite - target file exists")
            if self.target_file_modified():
                logger.debug("FileProcessOverwrite - do not overwrite")
                self.make_new_path()
                self.find_available_path()
            else:
                logger.debug("FileProcessOverwrite - overwrite")
                self.return_path = self.check_path
                self.delete_target_file_path(self.check_path)

    def make_new_path(self):
        title, ext = os.path.splitext(self.check_path_original)
        self.conflict_num += 1
        self.check_path = title + str(self.conflict_num) + ext

    def target_file_exists(self):
        #checks if file exists in the user dropbox directory
        try:
            meta = self.sh.ignore_timeout(self.cli.metadata)(self.check_path)
            if unicode('is_deleted') in meta.keys():
                if meta[unicode("is_deleted")]:
                    return False
            return True
        except rest.ErrorResponse as e:
            return False

    def target_file_modified(self):
        #if the file is in online store, and copy ref validates - file was never modified by user.
        meta = self.sh.ignore_timeout(self.client.metadata)(self.check_path)
        try:
            result = OnlineStore.query\
                      .filter(OnlineStore.source_user_id == self.check_user_id)\
                      .filter(OnlineStore.source_file_path == self.check_path)\
                      .one()

            self.check_revision = result.source_file_revision
            if meta["revision"] == self.check_revision:
                #the revision is consistent with the one we uploaded
                #the user has not modified
                logger.debug("FileProcessOverwrite - file not modified by user")
                return False
            else:
                #revision is inconsistent
                #user has modified
                logger.debug("FileProcessOverwrite - file modified by user")
                return True

        except MultipleResultsFound as e:
            #Shouldn't reach here
            #TODO: delete entries
            logger.critical("FileProcessOverwrite - duplicate file entry")
            return True

        except NoResultFound as e:
            #file isn't in online store - either
            #1 we didn't upload it
            #2 it was already modified by the user
            #result - do not upload
            logger.warning("FileProcessOverwrite - no file entry found")
            return True

    def delete_target_file_path(self, path):
        logger.debug("FileProcessOverwrite - deleting file...")
        meta = self.cli.file_delete(path)
        logger.debug("FileProcessOverwrite - file deleted")
        result = OnlineStore.query\
                      .filter(OnlineStore.source_user_id == self.check_user_id)\
                      .filter(OnlineStore.source_file_path == self.check_path)
        if result.count():
            for r in result.all():
                db_session.delete(r)
            db_session.commit()
            logger.debug("FileProcessOverwrite - file entry deleted")

    def get_target_file_path(self):
        #remove preceding '/' in paths.
        return trim_path(self.return_path) 



class FileCopier():
    def __init__(self, job_id):
        self.job_id = job_id

    @celery.task
    def start(self):
        try:
            self.job = Job.query.filter_by(job_id = self.job_id).first()
            if self.job == None:
                logger.warning('job does not exist anymore. Have you cleared the database but not the message queue?')
                return

            #check that it hasn't been paused in the meantime
            if self.job.status == 6:
                logger.info("job has been paused.")
                return

            if self.job.status_started == None:
                self.job.status_started = datetime.now()
            else:
                self.job.status_retries = self.job.status_retries + 1
            db_session.commit()
            logger.info("FileCopier - Starting file transfer %s for User %s", self.job.file_id, self.job.user_id)



            self.sh = SessionHandler(self.job.user_id)
            self.cli = self.sh.client
            self.processed_path = FileProcessOverwrite(self.job.user_id, self.job.target_path).get_target_file_path()
            for entry in self.fetch_copy_ref_db(self.job.file_id):
                if self.check_copy_ref_validity(entry):
                    try:
                        self.upload_copy_ref(entry.dropbox_copy_ref)
                        logger.info("Copy - copy ref successful")
                        self.job.status_copy_ref = 1
                        #status 3 for copy ref uploads
                        self.job.status = 3
                        self.job.status_completed = datetime.now()
                        db_session.commit()
                        return
                    except rest.ErrorResponse as e:
                        logger.info("Copy - copy ref failed.")
            self.upload_file()
            #status 2 for normal uploads
            self.job.status = 2
            self.job.status_upload = 1
            self.job.status_completed = datetime.now()
            db_session.commit()

        #catch exceptions, paused jobs, logging,
        except Exception, e:
            if isinstance(e, (list, tuple)) and e.args[0] == "DROPBOX_USR_ERR":
                logger.warning("dropbox auth not found, pausing job.")
                self.job.status = 6
                db_session.commit()
                return
            else:
                logger.critical("dist failed")
                logger.critical(e.args)
                logger.critical(e.message)
                logger.critical(traceback.format_exc())
                raise e


    def upload_file(self):
        logger.debug("Copy - Uploading Normally.")
        FileFetch(self.job)
        f = open("cache/" + self.job.file_id, 'rb')
        response = self.cli.put_file(self.processed_path, f)
        f.close()

        self.put_into_copy_ref_store(response)
        self.log_file_copy(response)


    def upload_copy_ref(self, copy_ref_entry):
        try:
            meta = self.sh.ignore_timeout(self.cli.metadata)(self.processed_path)
            if "is_deleted" in meta.keys():
                if not meta["is_deleted"]:
                    raise Exception("Copy - file exists in remote folder (should be detected by FileProcessOverwirte)")
                else:
                    logger.debug("Copy - file doesnt exist in remote folder (deleted). go ahead upload")
                    response = self.cli.add_copy_ref(copy_ref_entry, self.processed_path)
                    self.put_into_copy_ref_store(response)
                    self.log_file_copy(response)
        except rest.ErrorResponse as e:
            logger.debug(e)
            logger.debug("Copy - file doesnt exist in remote folder. go ahead upload")
            response = self.cli.add_copy_ref(copy_ref_entry, self.processed_path)
            self.put_into_copy_ref_store(response)
            self.log_file_copy(response)


    def fetch_copy_ref_db(self, file_id):
        results = OnlineStore.query.filter(OnlineStore.file_id == file_id)
        return results

    def remove_copy_ref_db(self, store_obj):
        db_session.delete(store_obj)
        db_session.commit()

    def check_copy_ref_validity(self, copy_ref_entry):
        try:
            logger.info("check copy ref - logging in as %s", copy_ref_entry.source_user_id)
            source_sh = SessionHandler(copy_ref_entry.source_user_id)
            meta = source_sh.ignore_timeout(source_sh.client.metadata)(copy_ref_entry.source_file_path)
            if meta["revision"] == copy_ref_entry.source_file_revision:
                logger.info("Copy - copy-ref is valid!")
                return True
            else:
                logger.info("Copy - copy-ref is not valid!")
                self.remove_copy_ref_db(copy_ref_entry)
                return False
        except rest.ErrorResponse as e:
            logger.warning(e)
            logger.warning("Copy - copy-ref error response...")
            return False
        except Exception, e:
            if len(e.args) > 0 and e.args[0] == "DROPBOX_USR_ERR":
                logger.warning("Dropbox Auth not found.")
                return False
            else:
                logger.warning("Copy - copy-ref validation error")
                logger.warning(e)
                return False

    def put_into_copy_ref_store(self, meta):
        c_ref = self.sh.ignore_timeout(self.cli.create_copy_ref)(meta["path"])
        meta["path"] = trim_path(meta["path"])
        new_store = OnlineStore(self.job, c_ref, meta)
        db_session.add(new_store)
        db_session.commit()

    def log_file_copy(self, meta):
        #updates succesful uploads into ivle_file
        file = IVLEFile.query.filter_by(user_id = self.job.user_id, ivle_id = self.job.file_id).first()
        file.dropbox_uploaded_date = datetime.now()
        file.dropbox_revision = meta["revision"]
        db_session.commit()

def trim_path(path):
     #remove first / in path
     return path[path[0] == '/' :]



@celery.task
def upload_dropbox_jobs():
    logger.info("Queueing file transfers for all users")
    for entry in Job.query.filter_by(status = 0).all():
        entry.status = 1
        db_session.commit()
        fc = FileCopier(entry.job_id)
        FileCopier.start.delay(fc)

@celery.task
def upload_user_dropbox_jobs(user_id):
    logger.info("Queueing file transfers for user %s", user_id)
    for entry in Job.query.filter_by(status = 0).filter_by(user_id = user_id).all():
        entry.status = 1
        db_session.commit()
        fc = FileCopier(entry.job_id)
        FileCopier.start.delay(fc)

