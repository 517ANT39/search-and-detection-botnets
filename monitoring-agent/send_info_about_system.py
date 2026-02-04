import psutil
from constants import PROCESS_INFO_FIELDS, CURR_PID, PROCESSES_INFO_TOPIC, SYSTEM_INFO_TOPIC, CURR_INFO_SYSTEM
from producer import send_data


def send_info_host():
    send_data(SYSTEM_INFO_TOPIC,data=CURR_INFO_SYSTEM)

def send_info_processes():
    for proc in psutil.process_iter(PROCESS_INFO_FIELDS):
        if proc.pid != CURR_PID:
            info = proc.info
            connections = proc.net_connections()
            info["connections"] = connections
            send_data(PROCESSES_INFO_TOPIC,key=CURR_INFO_SYSTEM["host_id"],data=info)
