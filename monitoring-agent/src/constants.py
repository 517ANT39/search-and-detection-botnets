import os
from dotenv import load_dotenv
from utils import generate_host_id
load_dotenv()

CURR_PID = os.getpid()
_UNAME = os.uname()
CURR_INFO_SYSTEM = {
    "sysname": _UNAME[0],
    "nodename": _UNAME[1],
    "release": _UNAME[2],
    "machine": _UNAME[4],
    "host_id": generate_host_id(_UNAME[1])
}

CONFIG_PRODUCER = {
    'bootstrap.servers': os.getenv('KAFKA_SERVERS'),
    'log_level': 3,
    'compression.type': 'lz4'
}
PROCESS_INFO_FIELDS = ['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']
TIME_SEND_DATA = int(os.getenv('TIME_SEND_DATA',"0"))
PROCESSES_INFO_TOPIC = os.getenv('PROCESSES_INFO_TOPIC')
SYSTEM_INFO_TOPIC = os.getenv('SYSTEM_INFO_TOPIC')