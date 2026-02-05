import psutil
from constants import PROCESS_INFO_FIELDS, CURR_PID, PROCESSES_INFO_TOPIC, SYSTEM_INFO_TOPIC, CURR_INFO_SYSTEM
from src.producer import send_data


def send_info_host():
    send_data(topic=SYSTEM_INFO_TOPIC,data=CURR_INFO_SYSTEM)

def send_info_processes():
    for proc in psutil.process_iter(PROCESS_INFO_FIELDS):
        try:
            if proc.pid != CURR_PID:
                info = proc.info
                connections = proc.net_connections()
                info["connections"] = connections
                send_data(topic=PROCESSES_INFO_TOPIC,key=CURR_INFO_SYSTEM["host_id"],data=info)
        except:
            pass