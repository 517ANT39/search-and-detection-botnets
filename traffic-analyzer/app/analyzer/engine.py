import logging

from app.extensions.extensions import db
from app.models import AnalyzerSettings
from app.analyzer.registry import detector_registry
from app.notifications.mailer import send_alert_notifications

logger = logging.getLogger("analyzer.engine")


def run_analysis(app):
    """Главная точка входа — вызывается планировщиком."""
    with app.app_context():
        settings = AnalyzerSettings.get_safe()
        if settings is None:
            logger.warning("Cannot load settings, skipping analysis")
            return

        logger.info("Analysis started (window=%d min)", settings.window_minutes)

        all_alerts = []

        for detector in detector_registry.get_all():
            if not detector.is_enabled(settings):
                logger.debug("Detector '%s' disabled, skipping", detector.name)
                continue

            try:
                alerts = detector.detect(settings)
                all_alerts.extend(alerts)
                logger.info("Detector '%s': %d alerts", detector.name, len(alerts))
            except Exception as e:
                logger.error("Detector '%s' failed: %s", detector.name, e, exc_info=True)

        if all_alerts:
            db.session.add_all(all_alerts)
            db.session.commit()
            logger.warning("Total %d alerts created", len(all_alerts))

            for alert in all_alerts:
                try:
                    send_alert_notifications(alert)
                except Exception as e:
                    logger.error("Notification failed: %s", e)
        else:
            logger.info("No anomalies detected")
