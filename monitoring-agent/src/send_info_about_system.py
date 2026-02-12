import psutil
from constants import PROCESS_INFO_FIELDS, CURR_PID, PROCESSES_INFO_TOPIC, SYSTEM_INFO_TOPIC, CURR_INFO_SYSTEM
from producer import producer



def send_info_host():
    producer.produce(topic=SYSTEM_INFO_TOPIC,value=CURR_INFO_SYSTEM)
    producer.flush()

def send_info_processes():
    try:
        for proc in psutil.process_iter(PROCESS_INFO_FIELDS):
            try:
                if proc.pid != CURR_PID:
                    info = proc.info
                    connections = proc.net_connections()
                    io_counters = proc.io_counters()
                    info["memory_info"] = info["memory_info"]._asdict()
                    info["connections"] = list(map(lambda c: c._asdict(), connections))
                    info["io_counters"] = io_counters._asdict()
                    info["host_id"] = CURR_INFO_SYSTEM["host_id"]
                    producer.produce(topic=PROCESSES_INFO_TOPIC,key=CURR_INFO_SYSTEM["host_id"],value=info)
            except:
                pass
        producer.flush()
    except:
        pass

if __name__ == '__main__':
    import json
    for proc in psutil.process_iter(PROCESS_INFO_FIELDS):
        try:
            if proc.pid != CURR_PID:
                info = proc.info
                connections = proc.net_connections()
                io_counters = proc.io_counters()
                info["memory_info"] = info["memory_info"]._asdict()
                info["connections"] = list(map(lambda c: c._asdict(), connections))
                info["io_counters"] = io_counters._asdict()
                info["host_id"] = CURR_INFO_SYSTEM["host_id"]
                print(json.dumps(info))
        except:
            pass