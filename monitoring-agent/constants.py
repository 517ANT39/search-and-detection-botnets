import os
from dotenv import load_dotenv
load_dotenv()

CURR_PID = os.getpid()
RABBITMQ_URL_CONNECT = os.getenv('RABBITMQ_URL_CONNECT')
PROCESS_INFO_FIELDS = ['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'cmdline', 'environ', 'open_files']
TIME_SEND_DATA = os.getenv('TIME_SEND_DATA')