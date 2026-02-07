import hashlib
from uuid import getnode as get_mac_address

def generate_host_id(hostname):
    mac = hex(get_mac_address())[2:] # Удаляем префикс '0x'
    data = f"{hostname}-{mac}"
    hashed_data = hashlib.sha256(data.encode()).hexdigest()
    return hashed_data
