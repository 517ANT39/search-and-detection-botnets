import psutil
import os
from dotenv import load_dotenv
load_dotenv()


if __name__ == "__main__":
    # Добавляем необходимые поля для дополнительной информации
    fields = ['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'cmdline', 'environ', 'open_files']
    # Итерация по всем запущенным процессам
    for proc in psutil.process_iter(fields):
        try:
            if proc.pid != os.getpid():  # Пропускаем собственный процесс
                info = proc.info
                print(info)
                connections = proc.net_connections()
                print(connections)

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue