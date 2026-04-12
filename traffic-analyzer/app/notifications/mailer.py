import logging
from flask_mail import Message
from app.extensions.extensions import mail
from app.models import NotificationGroup

logger = logging.getLogger("notifications")

TEMPLATE = """
🚨 TRAFFIC ALERT: {title}

Severity : {severity}
Type     : {alert_type}
Host     : {host_id}
Source IP : {src_ip}
Dest IP  : {dst_ip}
Time     : {created_at}

{description}

--
Traffic Analyzer
"""


def send_alert_notifications(alert):
    groups = NotificationGroup.query.filter_by(is_active=True).all()

    for group in groups:
        if alert.severity not in group.severity_list:
            continue

        emails = group.all_emails
        if not emails:
            continue

        subject = f"[{alert.severity.upper()}] {alert.title}"
        body = TEMPLATE.format(
            title=alert.title,
            severity=alert.severity.upper(),
            alert_type=alert.alert_type,
            host_id=alert.host_id,
            src_ip=alert.src_ip or "N/A",
            dst_ip=alert.dst_ip or "N/A",
            created_at=alert.created_at,
            description=alert.description,
        )

        try:
            msg = Message(subject=subject, recipients=emails, body=body)
            mail.send(msg)
            logger.info("Email sent to group '%s' (%d recip)", group.name, len(emails))
        except Exception as e:
            logger.error("Email to '%s' failed: %s", group.name, e)
