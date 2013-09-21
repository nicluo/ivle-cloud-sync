from __future__ import absolute_import
from datetime import datetime, timedelta, date, time
from time import sleep
import logging
import numpy as np
logger = logging.getLogger(__name__)
mail_logger = logging.getLogger('mail.monitor')

from ivlemods.celery import celery
from ivlemods.tasks import one_task_callback

def gen_six_hourly():
    #generate 6 hourly dates
    dates = [datetime.combine(date.today(), time(0)),
             datetime.combine(date.today(), time(6)),
             datetime.combine(date.today(), time(12)),
             datetime.combine(date.today(), time(18))]
    return dates

def cycle(dates):
    #cycles the dates so that dates[0] will be closest forward to current time
    #dates that are passed will be removed, added a day, and appended to the queue
    while(dates[0] < datetime.now()):
        dt = dates[0] 
        dates.pop(0)
        dates.append(dt + timedelta(days=1))
    return

def check_dates(dates):
    #checks if the time coincides with the listed
    #automatically cycles the dates
    if(dates[0] < datetime.now()):
        cycle(dates)
        return True
    else:
        return False

def create_alarm(minutes, reboot, alarm_list):
    #appends alarm to alarm_list
    alarm_list.append((minutes, reboot))
    alarm_list.sort(key=lambda tup: tup[0], reverse=True)

def check_alarms(inactive_minutes, alarm_list):
    #triggers mail logging
    for times, reboot in alarm_list:
        if(inactive_minutes > times):
            return (times, reboot) 
    return False

def email_statistics(times):
    #consolidates and emails statistics
    run_times = np.array(times)
    average_time = timedelta(seconds = np.average(run_times))
    max_time = timedelta(seconds = int(np.amax(run_times)))
    min_time = timedelta(seconds = int(np.amin(run_times)))
    total = len(times)
    mail_logger.info('one_task has been run a total of %s times. Average: %s, Max: %s, Min: %s.', total, average_time, max_time, min_time)

def watch():
    #main loop to be called
    #dev
    inspect_worker_name = 'celery1.localhost'
    #inspect_worker_name = 'celery.cloudsync'

    #generate the times when statistics are mailed
    mail_times = gen_six_hourly()
    cycle(mail_times)

    #generate the alarm times for problems to be raised
    alarm_list = []
    create_alarm(15, 0, alarm_list)
    create_alarm(45, 0, alarm_list)
    create_alarm(90, 1, alarm_list)

    #initial states
    times = []
    #state = 1 to ignore first data point
    state = 1
    now = datetime.now()
    #alarm state to propagate
    task_alarm_state = 0
    worker_alarm_state = 0

    while True:
        #collect statistics
        i = celery.control.inspect([inspect_worker_name])
        scheduled = 0

        #checks for worker running status, i.scheduled() should be callable if the celery worker is inspectable.
        if i.scheduled():
            #worker is alive and running
            #update scheduled as the number of tasks that are scheduled
            #this detetts the 30 seconds delay in one_task_callback
            scheduled = len(i.scheduled()[inspect_worker_name])
            if worker_alarm_state:
                #reset worker alarm state
                worker_alarm_state = 0
                logger.warning('Worker %s is now inspectable. Woohoo...', inspect_worker_name) 
        elif worker_alarm_state == 0:
            #worker isn't alive
            #set worker alarm state and ignore repeat alarms
            worker_alarm_state = 1
            logger.warning('Worker %s not inspectable. Is the worker running and alive.', inspect_worker_name) 

        if not state == scheduled:
            #state is the number of things in the scheduled queue
            logger.debug(state)
            state = scheduled
            diff = datetime.now() - now
            now = datetime.now()

            #logging
            if state == 0 :
                logger.info('No scheduled tasks - one_task should be running')
            elif state == 1 :
                times.append(int(diff.total_seconds()))
                logger.info('Scheduled task detected - one_task is queued')
                logger.info('Current Run %s', diff)


        #check for scheduled reports
        if check_dates(mail_times):
            #mail results here
            if(len(times)):
                email_statistics(times)
            else:
                logger.info('Not enough run statistics. Not reporting statistics')
            times = []

        #check for task alarms (if one_task hasn't been running for a while)
        if(state == 0):
            diff = datetime.now() - now
            res = check_alarms(diff.total_seconds() / 60, alarm_list)
            if res:
                res_state, res_reboot = res
                if res_state > task_alarm_state:
                    #ignore repeat alarms from the same limit
                    task_alarm_state = res_state
                    #alarmed
                    logger.warning('Alarm triggered. CloudSync one_task hasn\'t been scheduled for %s minutes. Reboot Flag: %s', task_alarm_state, res_reboot) 
                    if res_reboot:
                        one_task_callback.delay()
                        logger.warning('Attempting to run one_task_callback.') 
        else:
            if task_alarm_state:
                logger.warning('Alarm reset. CloudSync one_task is found to be scheduled. Last alarm: %s minutes.', task_alarm_state) 
                #reset alarm
                task_alarm_state = 0

        sleep(10)
