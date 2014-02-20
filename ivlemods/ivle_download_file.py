import os
import logging
import requests
from datetime import datetime

from ivlemods import app
from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.task import SqlAlchemyTask

from ivlemods.models import User, Job, Cache
from ivlemods.lock import try_lock, release_lock
from ivlemods.error import CacheMutex

logger = logging.getLogger(__name__)

class InvalidFile(Exception):
    def __init__(self, file_id):
        self.file_id = file_id 
    def __str__(self):
        return repr(self.file_id)

class NoLocalCopy(Exception):
    def __init__(self, job_id):
        self.job_id = job_id 
    def __str__(self):
        return repr(self.job_id)

@celery.task(base=SqlAlchemyTask)
def ivle_check_file_downloaded(job_id):
    logger.info('Checking cache entries for job %s.', job_id)
    job = Job.query.get(job_id)
    #rows = Cache.query.filter(Cache.file_id == job.file_id).one()
    #logger.debug('Number of cache entries for file %s: %s', job.file_id, rows)

    if not job.cache:
        logger.debug('Cache entry not found - job %s', job_id)
        #queue file download
        ivle_download_file.delay(job.job_id)
        #trigger a wait to free the dropbox worker
        raise NoLocalCopy(job.job_id)

    else:
        try:
            validate_cache_entry(job.cache)
        except InvalidFile, e:
            logger.debug('Invalid file: file - %s, Deleting cache entry', e)
            #delete cache entry
            db_session.delete(job.cache)
            db_session.commit()
            #queue file download
            ivle_download_file.delay(job.job_id)
            #trigger a wait to free the dropbox worker
            raise NoLocalCopy(job.job_id)
    return

@celery.task(base=SqlAlchemyTask)
def ivle_download_file(job_id, wait_interval = 20):
    logger.info('Checking and downloading file for job %s.', job_id)
    job = Job.query.get(job_id)
    try:
        if job.cache:
            logger.debug(job.cache)
            logger.debug('Validating job cache %s.', job_id)
            #check cache entry for errors
            validate_cache_entry(job.cache)
            return
        else:
            logger.debug('Downloading for job cache %s.', job_id)
            #check mutex and wait
            try_lock(job.file_id, "file not cached, some other job is downloading, wait.")
            #mutex is yours
            try:
                #check again that there is no entry
                if job.cache == None:
                    #go ahead and download
                    if job.method == 'http':
                        path = 'cache/' + str(job.file_id)
                        download_to_file_http(job.http_url, path)
                        logger.debug("downloaded file to %s.", path)
                    #create cache entry
                    create_cache_entry(job)
                    validate_cache_entry(job.cache)
                    release_lock(job.file_id)
                else:
                    logger.debug('file %s has cache entry already. Continue.', job.file_id)
                    release_lock(job.file_id)
            except:
                release_lock(job.file_id)
                raise

    except CacheMutex, e:
        logger.debug('Lock conflict: lock - %s, message - %s', e.lock, e.value)
        logger.debug('Delay by %d seconds', wait_interval)
        #wait, might have to retry?
        #countdown of 20 seconds
        ivle_download_file.apply_async(args=(job_id, wait_interval*2), countdown=wait_interval)
    except InvalidFile, e:
        logger.debug('Invalid file: file - %s', e)
        #delete cache entry
        db_session.delete(job.cache)
        db_session.commit()
    return

def create_cache_entry(job):
    new_cache = Cache({'file_id':job.file_id,
                       'http_url':job.http_url,
                       'method':job.method,
                       'download_user_id':job.user_id,
                       'file_size': get_file_size('cache/' + str(job.file_id)),
                       'path': 'cache/' + str(job.file_id)})
    db_session.add(new_cache)
    db_session.commit()

def validate_cache_entry(cache):
    path = cache.path
    if not check_file_exists_and_sized(path):
        raise InvalidFile(cache.file_id)
    return

def delete_file_if_exists(path):
    if os.path.exists(path):
        logger.debug('File exists at %s', path)
        logger.debug("Cache - have to delete existing file at %s.", path)
        os.remove(path)
    return

def check_file_exists_and_sized(path):
    if os.path.exists(path) and os.stat(path).st_size > 0:
        logger.debug('File exists at %s', path)
        return True
    return False

def download_to_file_http(url, path):
    ensure_directory(path)
    delete_file_if_exists(path)
    download = requests.get(url)
    download.raise_for_status()
    with open(path, 'wb') as f:
        logger.debug(download.headers)

        f.write(download.content)
        f.close()
    return


def ensure_directory(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)
    return

def get_file_size(path):
    if os.path.exists(path):
        file_size = os.stat(path).st_size
    else:
        file_size = 0
    return file_size
