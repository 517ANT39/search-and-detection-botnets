import time
from constants import TIME_SEND_DATA
from utils import *

if __name__ == "__main__":
    while True:
        with pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL_CONNECT)) as connection:
            send_info_host(connection)
            send_info_processes(connection)
        time.sleep(TIME_SEND_DATA)