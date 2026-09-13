import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL,
)


class ConnectionManager:
    """Менеджер WebSocket-подключений."""
    def __init__(self):
        self.active: list = []

    async def connect(self, ws):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: str):
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def send_email_alert(alert: dict):
    if not SMTP_HOST or not SMTP_USER:
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_USER
        msg["To"]      = ADMIN_EMAIL
        msg["Subject"] = (
            f"[{alert.get('severity','?').upper()}] "
            f"{alert.get('view','?')}: "
            f"{alert.get('src_ip','')} → {alert.get('dst_ip','')}"
        )
        body = (
            f"Anomaly detected at {alert.get('timestamp')}\n"
            f"Detector: {alert.get('detector')} / {alert.get('view')}\n"
            f"Source:      {alert.get('src_ip')}:{alert.get('src_port')}\n"
            f"Destination: {alert.get('dst_ip')}:{alert.get('dst_port')}\n"
            f"Protocol:    {alert.get('protocol')}\n"
            f"Packets:     {alert.get('packet_count')}\n"
            f"Bytes:       {alert.get('byte_sum')}\n"
            f"Z-score:     {alert.get('z_score')}\n"
            f"Type:        {alert.get('anomaly_type')}\n"
            f"Severity:    {alert.get('severity')}\n"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.send_message(msg)
    except Exception as e:
        print(f"[email] ошибка: {e}")