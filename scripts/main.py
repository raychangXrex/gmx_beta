from apscheduler.schedulers.blocking import BlockingScheduler
from dataBaseInserter import DatabaseInserter
import time
import datetime


def update_database():
    start_time = time.time()
    print(f'Start updating databases at {datetime.datetime.now()}')
    try:
        updater = DatabaseInserter()
        updater.insert_summary_total_balance()
        updater.insert_gmx_account()
        updater.insert_binance_hedge_account()
        updater.insert_metamask_account()

    except BaseException:
        print(f'Update fails at {datetime.datetime.now()}')

    print(f'Update succeeds, It takes {time.time() - start_time}')


if __name__ == '__main__':
    sched = BlockingScheduler()
    sched.add_job(update_database, 'cron', minute='*/10', second=0)
    sched.start()
