from ivlemods import app
from ivlemods.error import CacheMutex
import logging
import redis

logger = logging.getLogger(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)

def try_lock(lock, fail_message):
    logger.debug('trying for lock %s', lock)
    mutex_is_locked = r.getset(lock, '1') == '1'
    if mutex_is_locked:
        raise CacheMutex(lock, fail_message) 

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

def release_lock(lock):
    logger.debug('release lock %s', lock)
    r.set(lock, 'None')
