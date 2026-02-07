from constants import TIME_SEND_DATA
from send_info_about_system import *
from apscheduler.schedulers.blocking import BlockingScheduler
if __name__ == "__main__":
    scheduler = BlockingScheduler()
    try:
        send_info_host()
        scheduler.add_job(send_info_processes, "interval", seconds=TIME_SEND_DATA)
        scheduler.start()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()