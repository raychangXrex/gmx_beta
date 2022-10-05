from insert_into_sql import *
from apscheduler.schedulers.blocking import BlockingScheduler

if __name__ == '__main__':
    # change
    sched = BlockingScheduler()
    sched.add_job(update_database, 'cron', minute='*/5', second=0)
    sched.start()