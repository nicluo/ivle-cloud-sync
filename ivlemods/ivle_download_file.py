import os
import logging
import requests

from datetime import datetime

from ivlemods import app
from ivlemods.celery import celery
from ivlemods.database import db_session
from ivlemods.models import User, Job, OnlineStore, IVLEFile, Cache

from ivlemods.task import SqlAlchemyTask
from ivlemods.error import CacheMutex

logger = logging.getLogger(__name__)

class InvalidFile(Exception):
    def __init__(self, file_id):
        self.file_id = file_id 
    def __str__(self):
        return repr(self.file_id)

@celery.task(base=SqlAlchemyTask)
def ivle_download_file(job):
    try:
        if job.cache:
            #check cache entry for errors
            self.validate_cache_entry(job.cache)
            return
        else:
            #check mutex and wait
            try_lock(job.file_id, "Cache - File not cached, some other job is downloading, wait.")
            #mutex is yours
            try:
                #check again that there is no entry
                if job.cache == None:
                    #go ahead and download
                    if job.method == 'http':
                        path = 'cache/' + job.file_id
                        cache_file = get_cache_file(path)
                        download_to_file_http(job.http_url, cache_file)
                    #create cache entry
                    create_cache_entry(job)
                    validate_cache_entry(job.cache)
            except:
                release_lock(job.file_id)
                raise
            else:
                logger.debug('Cache - File %s has cache entry already. Continue.', job.file_id)
                release_lock(job.file_id)
                return
    except InvalidFile, e:
        #delete cache entry
        db_session.remove(job.cache)
        db_session.commit()


def create_cache_entry(job):
    pass

def validate_cache_entry(cache):
    path = cache.path
    if check_file_exists_and_sized(path):
        return 
    else:
        raise InvalidFile(cache.file_id)

def delete_file_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
        logger.debug("Cache - have to delete existing file at %s.", path)
    return

def check_file_exists_and_sized(path):
    if not os.path.exists(path) and os.stat(path).st_size > 0:
        return True
    return False

def get_cache_file(path):
    ensure_directory(path) 
    delete_file_if_exists(path)
    out = open(path, 'wb')
    return out


def download_to_file_http(url, f):
    download = requests.get(url)
    download.raise_for_status()
    logger.debug(download.headers)

    #ensure proper, empty temp file for the cache to use
    f.write(download.content)
    f.close()
    logger.debug("Cache - downloaded file to %s.", path)
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
                           'download_user_id':self.job.user_id,
                           'file_size': get_file_size('cache/' + self.job.file_id)})
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

    def check_if_complete(self, path):
        if os.path.exists(path) and os.stat(path).st_size > 0:
            return True
        return False


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

