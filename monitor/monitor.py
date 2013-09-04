from __future__ import absolute_import
import datetime
import time
import logging
import numpy as np
logger = logging.getLogger(__name__)

from ivlemods.celery import celery

def watch():
    state = 0
    now = datetime.datetime.now()
    while True:
        i = celery.control.inspect(['celery1.localhost'])
        #print len(i.active()['celery1.localhost'])
        scheduled = len(i.scheduled()['celery1.localhost'])
        times = []
        if not state == scheduled:
            state = scheduled
            print('-----')
            logger.info(state)
            diff = datetime.datetime.now() - now
            if state == 0 :
                logger.debug('Scheduled task detected')
            elif state == 1 :
                times.append(int(diff.total_seconds()))
                logger.debug('No scheduled tasks')
                logger.info('Average')
                logger.info(datetime.timedelta(seconds = np.average(np.array(times))))
            logger.info(now)
            now = datetime.datetime.now()
        time.sleep(10)
