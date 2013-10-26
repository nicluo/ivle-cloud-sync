from ivlemods import app
from ivlemods.error import CacheMutex
import logging
import redis

logger = logging.getLogger(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)

#default set name as locks use sadd and srem (set) operations
DEFAULT_LOCK_SET = 'lock_general'

def try_lock(lock, fail_message, set=DEFAULT_LOCK_SET):
    logger.debug('trying for lock %s', lock)
    #sadd returns an integer.
    #1 means the set has grown
    #0 means the key exists in the set already (locked)
    mutex_is_locked = r.sadd(set, lock) != 1
    if mutex_is_locked:
        raise CacheMutex(lock, fail_message) 

def release_lock(lock, set=DEFAULT_LOCK_SET):
    logger.debug('release lock %s', lock)
    r.srem(set, lock)

def compare_and_swap_int(lock, expected_value, set_value):
    with r.pipeline() as pipe:
        while 1:
            try:
                pipe.watch(lock)
                #special case for 0 values
                #have to check redis for None
                value = pipe.get(lock)
                swap = False
                if value == None:
                    if expected_value == 0:
                        swap = True
                elif int(value) == expected_value:
                    swap = True

                if swap:
                    pipe.multi()
                    pipe.set(lock, set_value) 
                    pipe.execute()
                break
            except redis.WatchError, e:
                logger.debug('Watch error triggered, try again')
                continue
    if swap:
        return True
    return False
