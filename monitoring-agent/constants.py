import os
from dotenv import load_dotenv

from utils import generate_host_id

load_dotenv()

CURR_PID = os.getpid()

_UNAME = os.uname()
CURR_INFO_SYSTEM = {
    **_UNAME,
    "host_id": generate_host_id(_UNAME[1])
}
CONFIG_PRODUCER = {
    'bootstrap.servers': os.getenv('KAFKA_SERVERS'),
    'group.id': os.getenv('GROUP_ID'),
    'auto.offset.reset': 'earliest'
}
PROCESS_INFO_FIELDS = ['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'cmdline', 'environ', 'open_files']
TIME_SEND_DATA = os.getenv('TIME_SEND_DATA')
PROCESSES_INFO_TOPIC = os.getenv('PROCESSES_INFO_TOPIC')
SYSTEM_INFO_TOPIC = os.getenv('SYSTEM_INFO_TOPIC')