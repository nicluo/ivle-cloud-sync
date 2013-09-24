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
import ivlemods.tasks_dropbox
from ivlemods.task import SqlAlchemyTask
from ivlemods.error import DropboxNoCredentials, CacheMutex, DropboxExceedQuota

from ivlemods.dropbox_session import SessionHandler

logger = logging.getLogger(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)

def try_lock(lock, fail_message):
    logger.debug('trying for lock %s', lock)
    mutex_is_locked = r.getset(lock, '1') == '1'
    if mutex_is_locked:
        raise CacheMutex(lock, fail_message) 

def release_lock(lock):
    logger.debug('release lock %s', lock)
    r.set(lock, 'None')

def check_dropbox_quota(user_id):
    ivlemods.tasks_dropbox.update_user_dropbox_quota(user_id)
    user = User.query.get(user_id)
    return user.dropbox_data_quota - user.dropbox_data_shared - user.dropbox_data_normal

class CacheFetch():
    def __init__(self, job):
        self.job = job
        if not self.job.cache == None:
            return
        else:
            #check entry, check mutex and wait
            if self.job.cache == None:
                try_lock(self.job.file_id, "FileCopier - File not cached, some other job is downloading, wait.")
                #mutex is yours
                try:
                    #check again that there is no entry
                    if self.job.cache == None:
                        #go ahead and download
                        if self.job.method == 'http':
                            self.download_from_http()
                        #create cache entry
                        self.create_cache_entry()
                except:
                    release_lock(self.job.file_id)
                    raise
                else:
                    release_lock(self.job.file_id)
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
        self.check_rev= 0
        self.check_path = check_path

        self.sh = SessionHandler(user_id)
        self.cli = self.sh.client

        self.check_path_original = self.check_path
        self.return_path = ""
        self.return_rev = 0
        self.return_method = 'auto'

        #should only have one, or none latest
        latest = OnlineStore.query.filter(OnlineStore.source_file_path == self.check_path)\
                                  .filter(OnlineStore.source_user_id == self.check_user_id)\
                                  .filter(OnlineStore.is_valid == True).first()
        rev = self.target_file_rev(self.check_path)
        if latest:
            alternate_rev = self.target_file_rev(latest.source_uploaded_path)
        if rev:
            self.return_method = 'upload'
            if latest and latest.source_file_rev == alternate_rev:
                logger.debug("FileProcessOverwrite - Overwrite, fallback to normal upload")
                self.return_path = latest.source_uploaded_path
                self.return_rev = latest.source_file_rev
            elif latest:
                logger.debug("FileProcessOverwrite - File modified, fallback to normal upload")
                self.return_path = self.check_path
            else:
                logger.debug("FileProcessOverwrite - Mystery file for which we have no record of exists, let dropbox make new filename")
                self.return_path = self.check_path
        else:
            logger.debug("FileProcessOverwrite - target file doesnt exist, no need to overwrite")
            self.return_path = self.check_path

    def target_file_rev(self, path):
        #check for existing file
        #returns rev if file exists
        try:
            meta = self.sh.ignore_timeout(self.cli.metadata)(path)
            if 'is_deleted' in meta.keys():
                if meta['is_deleted']:
                    return False
            return meta['rev']
        except rest.ErrorResponse as e:
            return False

    def get_target_file_path(self):
        #remove preceding '/' in paths.
        return trim_path(self.return_path) 

    def get_target_method(self):
        return self.return_method

    def get_target_file_rev(self):
        return self.return_rev

class FileCopier():
    def __init__(self, job_id):
        self.job_id = job_id

    def start(self):
        logger.info("FileCopier - Accept job(%s).", self.job_id)
        #check that job still freaking exists
        self.job = Job.query.filter_by(job_id = self.job_id).first()
        if self.job == None:
            logger.warning('job does not exist anymore. Have you cleared the database but not the message queue?')
            return

        logger.info("FileCopier - Preliminary checks for job id(%s) file id(%s) for User %s", self.job.job_id, self.job.file_id, self.job.user_id)
        try:
            #check that it hasn't been paused in the meantime
            if self.job.status == 6:
                logger.info("job has been paused.")
                return

            #check that the cache entry exists before formally starting
            CacheFetch(self.job)

            #mark that we have started the job, and increment retries
            logger.info("FileCopier - Starting job id(%s) file id(%s) for User %s", self.job.job_id, self.job.file_id, self.job.user_id)
            if self.job.status_started == None:
                self.job.status_started = datetime.now()
            else:
                self.job.status_update = datetime.now()
                self.job.status_retry = datetime.now()
                self.job.status_retries += 1
            db_session.commit()

            #get the upload strategy, target path and target parent rev
            fpo = FileProcessOverwrite(self.job.user_id, self.job.target_path)
            self.method = fpo.get_target_method()
            self.file_path = fpo.get_target_file_path()
            self.file_rev = fpo.get_target_file_rev()

            #provide dropbox client
            self.sh = SessionHandler(self.job.user_id)
            self.cli = self.sh.client

            #encode to utf-8 to for dropbox uploads
            self.file_path = self.file_path.encode('utf-8')

            #try to upload copy ref
            if self.method == 'auto':
                if self.try_copy_ref():
                    logger.info("Copy - copy ref successful")
                    self.job.status_copy_ref = 1
                    self.job.status = 3
                    self.job.status_update = datetime.now()
                    self.job.status_completed = datetime.now()
                    db_session.commit()
                    return;

            #upload normal file
            self.upload_file()
            self.job.status_upload = 1
            self.job.status = 2
            self.job.status_update = datetime.now()
            self.job.status_completed = datetime.now()
            db_session.commit()

        #catch exceptions, paused jobs, logging,
        except DropboxNoCredentials, e:
            logger.warning("FileCopier - No Dropbox Credentials")
            logger.warning(e.value)
            #job status 10 is for jobs without dropbox credentials
            self.job.status = 10
            self.job.status_update = datetime.now()
            db_session.commit()
            return
        except CacheMutex, e:
            logger.info('Lock conflict: lock - %s, message - %s', e.lock, e.value)
            ivlemods.tasks_dropbox.wait_dropbox_job.delay(self.job_id, 20)
            return
        except DropboxExceedQuota, e:
            logger.info('User has exceeded Dropbox quota. File: %s, Quota: %s', e.file_size, e.quota)
            self.job.status = 12
            self.job.status_update = datetime.now()
            db_session.commit()
            return
        except Exception, e:
            logger.critical("dist failed")
            logger.critical(e.args)
            logger.critical(e.message)
            logger.critical(traceback.format_exc())
            #job status 11 is for jobs with mysterious errors
            self.job.status = 11
            self.job.status_update = datetime.now()
            db_session.commit()
            raise e

    def try_copy_ref(self):
        for entry in self.fetch_copy_ref_db(self.job.file_id):
            if self.check_copy_ref_validity(entry):
                try:
                    self.upload_copy_ref(entry.dropbox_copy_ref)
                    db_session.commit()
                    return True
                except rest.ErrorResponse as e:
                    logger.info("Copy - copy ref failed.")
                    return False


    def upload_file(self):
        logger.debug("Copy - NORMAL UPLOAD")
        file_size = os.stat('cache/' + self.job.file_id).st_size
        #40 mb
        if file_size > 41943040:
            response = self.upload_file_chunked()
        else:
            response = self.upload_file_put()
        self.post_upload_actions(response)

    def upload_file_chunked(self):
        logger.debug("Copy - CHUNKA UPLOAD")
        try_lock('chunk', 'Copy - Chunk upload lock failed')
        try:
            file_size = os.stat('cache/' + self.job.file_id).st_size
            free_space = check_dropbox_quota(self.job.user_id)
            if file_size > free_space:
                raise DropboxExceedQuota(file_size, free_space)    
            f = open('cache/' + self.job.file_id, 'rb')
            uploader = self.cli.get_chunked_uploader(f, file_size)
            while uploader.offset < file_size:
                try:
                    upload = uploader.upload_chunked()
                except rest.ErrorResponse, e:
                    # perform error handling and retry logic
                    logger.warning(e)
                    # ignore first
            f.close()

            #commit chunked uploader
            if self.file_rev:
                response = uploader.finish(self.file_path, parent_rev = self.file_rev)
            else:
                response = uploader.finish(self.file_path)
            release_lock('chunk')

        except Exception, e:
            release_lock('chunk')
            raise e

        return response

    def upload_file_put(self):
        logger.debug("Copy - PUT UPLOAD")
        f = open('cache/' + self.job.file_id, 'rb')
        if self.file_rev:
            response = self.cli.put_file(self.file_path, f, parent_rev = self.file_rev)
        else:
            response = self.cli.put_file(self.file_path, f)
        f.close()
        return response

    def upload_copy_ref(self, copy_ref_entry):
        try:
            meta = self.sh.ignore_timeout(self.cli.metadata)(self.file_path)
            if "is_deleted" in meta.keys():
                if not meta["is_deleted"]:
                    raise Exception("Copy - file exists in remote folder (should be detected by FileProcessOverwirte)")
                else:
                    logger.debug("Copy - file doesnt exist in remote folder (deleted). go ahead upload")
                    response = self.sh.ignore_timeout(self.cli.add_copy_ref)(copy_ref_entry, self.file_path)
                    self.post_upload_actions(response)
        except rest.ErrorResponse as e:
            logger.debug(e)
            logger.debug("Copy - file doesnt exist in remote folder. go ahead upload")
            response = self.cli.add_copy_ref(copy_ref_entry, self.file_path)
            self.post_upload_actions(response)

    def post_upload_actions(self, metadata):
        logger.debug(metadata)
        metadata["path"] = trim_path(metadata["path"])
        self.invalidate_latest_store_entry(metadata['path'])
        self.put_into_copy_ref_store(metadata)
        self.log_file_copy(metadata)
        logger.info('%d COMPLETE', self.job.job_id)

    def fetch_copy_ref_db(self, file_id):
        results = OnlineStore.query.filter(OnlineStore.file_id == file_id)\
                                   .filter(OnlineStore.is_valid == True)
        return results

    def remove_copy_ref_db(self, store_obj):
        store_obj.is_valid = False
        db_session.commit()

    def check_copy_ref_validity(self, copy_ref_entry):
        try:
            logger.info("check copy ref - logging in as %s", copy_ref_entry.source_user_id)
            source_sh = SessionHandler(copy_ref_entry.source_user_id)
            meta = source_sh.ignore_timeout(source_sh.client.metadata)(copy_ref_entry.source_file_path)
            if meta["rev"] == copy_ref_entry.source_file_rev:
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

    def invalidate_latest_store_entry(self, path):
        #should only have one, or none for the particular upload path
        latest = OnlineStore.query.filter(OnlineStore.source_file_path == self.job.target_path)\
                                  .filter(OnlineStore.source_user_id == self.job.user_id)\
                                  .filter(OnlineStore.is_valid == True).first()
        if latest:
            latest.is_valid = False
            db_session.commit()

    def put_into_copy_ref_store(self, meta):
        c_ref = self.sh.ignore_timeout(self.cli.create_copy_ref)(meta["path"])
        new_store = OnlineStore(self.job, c_ref, meta)
        db_session.add(new_store)
        db_session.commit()

    def log_file_copy(self, meta):
        #updates succesful uploads into ivle_file
        file = IVLEFile.query.filter_by(user_id = self.job.user_id, ivle_id = self.job.file_id).first()
        file.dropbox_uploaded_date = datetime.now()
        file.dropbox_rev= meta["rev"]
        db_session.commit()


def trim_path(path):
     #remove first / in path
     return path[path[0] == '/' :]


