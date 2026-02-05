from constants import TIME_SEND_DATA
from send_info_about_system import *
from apscheduler.schedulers.blocking import BlockingScheduler

from producer import producer

if __name__ == "__main__":

    for _ in range(100):
        producer.send('foobar', b'some_message_bytes')