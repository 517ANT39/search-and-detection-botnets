import json
import pika
import psutil

from constants import RABBITMQ_URL_CONNECT, PROCESS_INFO_FIELDS, CURR_PID


def send_info_host(connection):
    with connection.channel() as channel:
        channel.basic_publish(exchange='', routing_key='info', body='info')

def send_info_processes(connection):
    with connection.channel() as channel:
        for proc in psutil.process_iter(PROCESS_INFO_FIELDS):
            if proc.pid != CURR_PID:
                info = proc.info
                connections = proc.net_connections()
