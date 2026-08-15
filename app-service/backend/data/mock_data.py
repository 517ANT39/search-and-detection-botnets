import random
from datetime import datetime, timedelta


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def now_time():
    return datetime.utcnow().strftime("%H:%M:%S")


# ------------------------------------------------------------------
# Пользователи (демо). Пароли только для примера — замените на свою
# систему аутентификации при подключении реального backend.
# ------------------------------------------------------------------
USERS_DB = {
    "admin": {
        "password": "admin123",
        "name": "Александр Иванов",
        "role": "Администратор",
        "email": "a.ivanov@netsentry.local",
    }
}

# ------------------------------------------------------------------
# Метрики верхней панели «Обзор»
# Формат согласован с src/mock/mockProvider.js на фронтенде.
# ------------------------------------------------------------------
def build_summary():
    return {
        "totalTraffic": {"value": 2.47, "unit": "ТБ", "delta": 18.6},
        "outboundTraffic": {"value": 1.35, "unit": "ТБ", "percent": 54.7},
        "inboundTraffic": {"value": 1.12, "unit": "ТБ", "percent": 45.3},
        "activeNodes": {"active": 128, "total": 172, "percent": 74},
        "suspiciousActivity": {"value": 23, "delta24h": 5},
        "criticalIncidents": {"value": 7, "delta24h": 2},
    }

SUMMARY = build_summary()

CHANNEL_USAGE = [
    {"label": "Основной канал", "percent": 78},
    {"label": "Резервный канал", "percent": 34},
    {"label": "Канал в ЦОД", "percent": 61},
]

PROTOCOLS = [
    {"label": "HTTP/HTTPS", "percent": 38.6, "color": "#2f6fed"},
    {"label": "SMB", "percent": 22.1, "color": "#3aa0ff"},
    {"label": "DNS", "percent": 11.3, "color": "#2ecc71"},
    {"label": "RDP", "percent": 7.8, "color": "#f5a623"},
    {"label": "Прочее", "percent": 20.2, "color": "#c7ccd6"},
]

# ------------------------------------------------------------------
# Узлы сети. Поле "label" — отображаемое имя, "group" — площадка,
# "status" — один из ok | warning | critical (см. StatusBadge.jsx)
# ------------------------------------------------------------------
NODES = [
    {"id": "WS-MSK-21", "label": "WS-MSK-21", "group": "Офис Москва", "status": "ok", "ip": "10.10.1.21"},
    {"id": "WS-MSK-22", "label": "WS-MSK-22", "group": "Офис Москва", "status": "ok", "ip": "10.10.1.22"},
    {"id": "SRV-MSK-01", "label": "SRV-MSK-01", "group": "Офис Москва", "status": "ok", "ip": "10.10.1.10"},
    {"id": "FW-DC", "label": "FW-DC", "group": "ЦОД", "status": "critical", "ip": "10.10.2.1"},
    {"id": "SRV-CORE-01", "label": "SRV-CORE-01", "group": "ЦОД", "status": "ok", "ip": "10.10.2.5"},
    {"id": "SRV-APP-01", "label": "SRV-APP-01", "group": "ЦОД", "status": "ok", "ip": "10.10.2.10"},
    {"id": "SRV-DB-01", "label": "SRV-DB-01", "group": "ЦОД", "status": "warning", "ip": "10.10.2.11"},
    {"id": "SRV-FILE-01", "label": "SRV-FILE-01", "group": "ЦОД", "status": "ok", "ip": "10.10.2.12"},
    {"id": "WS-SPB-12", "label": "WS-SPB-12", "group": "Офис СПб", "status": "ok", "ip": "10.10.3.12"},
    {"id": "WS-SPB-11", "label": "WS-SPB-11", "group": "Офис СПб", "status": "ok", "ip": "10.10.3.11"},
    {"id": "SRV-SPB-01", "label": "SRV-SPB-01", "group": "Офис СПб", "status": "ok", "ip": "10.10.3.10"},
    {"id": "VPC-NETSENTRY", "label": "VPC-NETSENTRY", "group": "Облако", "status": "ok", "ip": "192.168.10.1"},
    {"id": "SRV-CLOUD-01", "label": "SRV-CLOUD-01", "group": "Облако", "status": "ok", "ip": "192.168.10.2"},
    {"id": "SRV-CLOUD-02", "label": "SRV-CLOUD-02", "group": "Облако", "status": "ok", "ip": "192.168.10.3"},
]

# ------------------------------------------------------------------
# Инциденты. level: critical|high|medium|low, status: new|in_progress|closed
# ------------------------------------------------------------------
INCIDENTS = [
    {
        "id": "INC-2024-05-24-102431", "time": "24.05.2024 10:24:31", "level": "critical",
        "title": "Несанкционированный доступ", "source": "WS-CLI-23",
        "target": "SRV-DB-01 (10.10.1.15)", "status": "new",
        "category": "Нарушение доступа", "subcategory": "Внешняя угроза",
        "responsible": "Не назначен", "policy": "Политика доступа к БД",
        "description": "Обнаружен несанкционированный доступ к базе данных с последующим изменением данных.",
        "timeline": [
            {"time": "10:24:01", "text": "Входной узел в сети", "node": "WS-CLI-23 (10.10.5.23)"},
            {"time": "10:24:15", "text": "Попытка доступа к ресурсу", "node": "SRV-DB-01 (10.10.1.15)"},
            {"time": "10:24:21", "text": "Повышение привилегий", "node": "Учётная запись: admin_db"},
            {"time": "10:24:31", "text": "Изменение данных", "node": "Таблица: customers, объём 12.4 МБ"},
            {"time": "10:24:48", "text": "Аномальный трафик", "node": "185.220.101.12"},
        ],
    },
    {"id": "INC-2024-05-24-095812", "time": "24.05.2024 09:58:12", "level": "high",
     "title": "Подозрительное сканирование портов", "source": "WS-CLI-17", "target": "10.10.1.0/24", "status": "in_progress"},
    {"id": "INC-2024-05-24-094107", "time": "24.05.2024 09:41:07", "level": "high",
     "title": "Массовое обращение к серверу", "source": "SRV-APP-01", "target": "SRV-APP-01 (10.10.2.30)", "status": "new"},
    {"id": "INC-2024-05-24-092218", "time": "24.05.2024 09:22:18", "level": "medium",
     "title": "Аномальный исходящий трафик", "source": "SRV-FILE-01", "target": "185.220.101.12", "status": "new"},
    {"id": "INC-2024-05-24-085533", "time": "24.05.2024 08:55:33", "level": "medium",
     "title": "DNS-туннелирование", "source": "WS-CLI-21", "target": "8.8.8.8", "status": "in_progress"},
    {"id": "INC-2024-05-24-081209", "time": "24.05.2024 08:12:09", "level": "low",
     "title": "Изменение конфигурации системы", "source": "SW-MSK-01", "target": "—", "status": "closed"},
    {"id": "INC-2024-05-24-075844", "time": "24.05.2024 07:58:44", "level": "low",
     "title": "Событие политики безопасности", "source": "FW-DC", "target": "—", "status": "closed"},
]

# ------------------------------------------------------------------
# Журнал событий
# ------------------------------------------------------------------
EVENTS = [
    {"time": "10:24:45", "level": "warning", "text": "Попытка доступа к ресурсу", "source": "SRV-DB-01"},
    {"time": "10:24:31", "level": "critical", "text": "Повышение привилегий", "source": "admin_db"},
    {"time": "10:24:15", "level": "warning", "text": "Изменение данных", "source": "Таблица customers"},
    {"time": "10:24:08", "level": "info", "text": "Сетевое соединение", "source": "185.220.112.443"},
    {"time": "10:23:57", "level": "warning", "text": "Аномальный трафик", "source": "SRV-FILE-01"},
]

# ------------------------------------------------------------------
# Уведомления (колокольчик в топбаре)
# ------------------------------------------------------------------
NOTIFICATIONS = [
    {"id": 1, "level": "critical", "text": "Обнаружен несанкционированный доступ к SRV-DB-01", "time": "10:24:31", "read": False},
    {"id": 2, "level": "warning", "text": "Подозрительное сканирование портов с WS-CLI-17", "time": "09:58:12", "read": False},
    {"id": 3, "level": "info", "text": "Еженедельный отчёт готов к загрузке", "time": "08:00:00", "read": True},
]

RULES = [
    {"id": 1, "name": "Политика доступа к БД", "type": "Доступ", "status": "active", "severity": "critical"},
    {"id": 2, "name": "Блокировка сканирования портов", "type": "Сеть", "status": "active", "severity": "high"},
    {"id": 3, "name": "Контроль исходящего трафика", "type": "Трафик", "status": "disabled", "severity": "medium"},
]

REPORTS = [
    {"id": 1, "name": "Еженедельный отчёт по инцидентам", "date": "19.05.2024", "format": "PDF"},
    {"id": 2, "name": "Отчёт по трафику узлов", "date": "12.05.2024", "format": "XLSX"},
]

SETTINGS = {
    "clusters": ["Все кластеры", "Москва", "Санкт-Петербург", "Облако"],
    "siemIntegration": True,
    "version": "2.4.1",
    "mode": "realtime",
}


def traffic_history():
    points = []
    now = datetime.utcnow()
    for i in range(24, -1, -1):
        t = now - timedelta(minutes=30 * i)
        points.append({
            "time": t.strftime("%H:%M"),
            "in": round(60 + random.random() * 140, 1),
            "out": round(40 + random.random() * 100, 1),
        })
    return points


def node_load_heatmap():
    return [round(random.random(), 2) for _ in range(36)]


# ------------------------------------------------------------------
# Структурированная нагрузка по узлам для столбчатой диаграммы:
# по каждому временному интервалу -- количество узлов в состоянии
# low / medium / high нагрузки.
# ------------------------------------------------------------------
def node_load_buckets():
    labels = ["-24ч", "-21ч", "-18ч", "-15ч", "-12ч", "-9ч", "-6ч", "-3ч", "Сейчас"]
    result = []
    for label in labels:
        low = random.randint(1, 4)
        medium = random.randint(0, 3)
        high = random.randint(0, 2)
        result.append({"time": label, "low": low, "medium": medium, "high": high})
    return result


# ------------------------------------------------------------------
# История трафика в разрезе по серверам (для сетки графиков на «Обзоре»
# и для страницы «Трафик»). Каждый узел получает свой профиль нагрузки,
# чтобы графики визуально отличались друг от друга.
# ------------------------------------------------------------------
def traffic_history_for_node(node_id: str, points: int = 25):
    seed = sum(ord(c) for c in node_id)
    rnd = random.Random(seed + int(datetime.utcnow().minute / 5))
    base_in = 40 + (seed % 60)
    base_out = 30 + (seed % 40)
    history = []
    now = datetime.utcnow()
    for i in range(points - 1, -1, -1):
        t = now - timedelta(minutes=30 * i)
        history.append({
            "time": t.strftime("%H:%M"),
            "in": round(max(5, base_in + rnd.uniform(-30, 40)), 1),
            "out": round(max(5, base_out + rnd.uniform(-20, 30)), 1),
        })
    return history


def traffic_by_node():
    """Список {id, label, group, history} для всех узлов -- используется
    сеткой мини-графиков на «Обзоре» и страницей «Трафик»."""
    return [
        {
            "id": n["id"],
            "label": n["label"],
            "group": n["group"],
            "history": traffic_history_for_node(n["id"]),
        }
        for n in NODES
    ]
