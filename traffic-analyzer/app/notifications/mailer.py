import logging
from flask_mail import Message
from app.extensions.extensions import mail
from app.models import NotificationGroup

logger = logging.getLogger("notifications")

SEV_RU = {
    "critical": "КРИТИЧЕСКИЙ",
    "high": "ВЫСОКИЙ",
    "medium": "СРЕДНИЙ",
    "low": "НИЗКИЙ",
}

TYPE_RU = {
    "anomaly": "Аномалия",
    "port_scan": "Сканирование портов",
    "ddos": "DDoS-атака",
}

TEMPLATE = """
🚨 ОПОВЕЩЕНИЕ: {title}

Критичность : {severity}
Тип          : {alert_type}
Узел         : {host_id}
IP источника : {src_ip}
IP назначения: {dst_ip}
Время        : {created_at}

{description}

--
Анализатор сетевого трафика
"""


def send_alert_notifications(alert):
    groups = NotificationGroup.query.filter_by(is_active=True).all()

    for group in groups:
        if alert.severity not in group.severity_list:
            continue

        emails = group.all_emails
        if not emails:
            continue

        sev_text = SEV_RU.get(alert.severity, alert.severity.upper())
        type_text = TYPE_RU.get(alert.alert_type, alert.alert_type)

        subject = f"[{sev_text}] {alert.title}"
        body = TEMPLATE.format(
            title=alert.title,
            severity=sev_text,
            alert_type=type_text,
            host_id=alert.host_id,
            src_ip=alert.src_ip or "Н/Д",
            dst_ip=alert.dst_ip or "Н/Д",
            created_at=alert.created_at,
            description=alert.description,
        )

        try:
            msg = Message(subject=subject, recipients=emails, body=body)
            mail.send(msg)
            logger.info("Письмо отправлено группе '%s' (%d адр.)", group.name, len(emails))
        except Exception as e:
            logger.error("Ошибка отправки '%s': %s", group.name, e)
