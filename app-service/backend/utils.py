import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ADMIN_EMAIL

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for conn in self.active_connections:
            try:
                await conn.send_text(message)
            except:
                pass

manager = ConnectionManager()

async def send_email_alert(alert: dict):
    if not SMTP_USER or not SMTP_PASSWORD:
        return
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = f"Traffic Anomaly Alert: {alert['src_ip']} -> {alert['dst_ip']}"
    body = f"""
    Detected anomaly at {alert['timestamp']}
    Source: {alert['src_ip']}:{alert['src_port']}
    Destination: {alert['dst_ip']}:{alert['dst_port']}
    Protocol: {alert['protocol']}
    Packets: {alert['packet_count']} (threshold: {alert['threshold_count']})
    Bytes: {alert['byte_sum']} (threshold: {alert['threshold_bytes']})
    Type: {alert['anomaly_type']}
    """
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Email error: {e}")