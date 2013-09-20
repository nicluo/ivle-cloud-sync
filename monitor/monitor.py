from __future__ import absolute_import
from datetime import datetime, timedelta, date, time
from time import sleep
import logging
import numpy as np
logger = logging.getLogger(__name__)
mail_logger = logging.getLogger('mail.monitor')

from ivlemods.celery import celery

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

def create_alarm(minutes, alarm_list):
    #appends alarm to alarm_list
    alarm_list.append(minutes)
    alarm_list.sort(reverse=True)

def check_alarms(inactive_minutes, alarm_list):
    #triggers mail logging
    for times in alarm_list:
        if(inactive_minutes > times):
            return times
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
    #inspect_worker_name = 'celery1.localhost'
    inspect_worker_name = 'celery.cloudsync'

    #generate the times when statistics are mailed
    mail_times = gen_six_hourly()
    cycle(mail_times)

    #generate the alarm times for problems to be raised
    alarm_list = []
    create_alarm(15, alarm_list)
    create_alarm(45, alarm_list)
    create_alarm(90, alarm_list)

    #initial states
    times = []
    #state = 1 to ignore first data point
    state = 1
    now = datetime.now()
    #alarm state to propagate
    task_alarm_state = 0
    worker_alarm_state = 0

    while True:
        #check for alarms
        if(state == 0):
            diff = datetime.now() - now
            res = check_alarms(diff.total_seconds() / 60, alarm_list)
            if res and res > task_alarm_state:
                #ignore repeat alarms from the same limit
                task_alarm_state = res
                #alarmed
                logger.warning('Alarm triggered. CloudSync one_task hasn\'t been scheduled for %s minutes.', task_alarm_state) 
        else:
            logger.warning('Alarm reset. CloudSync one_task is found to be scheduled. Last alarm: %s minutes.', task_alarm_state) 
            #reset alarm
            task_alarm_state = 0

        #collect statistics
        i = celery.control.inspect([inspect_worker_name])
        scheduled = 0
        if i.scheduled():
            scheduled = len(i.scheduled()[inspect_worker_name])
            if worker_alarm_state:
                logger.warning('Worker %s is now inspectable. Woohoo...', inspect_worker_name) 
                worker_alarm_state = 0
        elif worker_alarm_state == 0:
            #worker isn't alive
            logger.warning('Worker %s not inspectable. Is the worker running and alive.', inspect_worker_name) 
            #ignore repeat alarms
            worker_alarm_state = 1


        #check for scheduled reports
        if check_dates(mail_times):
            #mail results here
            if(len(times)):
                email_statistics(times)
            else:
                logger.info('Not enough run statistics. Not reporting statistics')
            times = []

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

        sleep(10)
