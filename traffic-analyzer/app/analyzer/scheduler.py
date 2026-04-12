import logging

from app.extensions.extensions import scheduler

logger = logging.getLogger("analyzer.scheduler")


def init_scheduler(app):
    default_interval = app.config.get("ANALYZER_SCHEDULE_MINUTES", 5)

    interval = default_interval
    try:
        with app.app_context():
            from app.models import AnalyzerSettings
            s = AnalyzerSettings.get_safe()
            if s:
                interval = s.schedule_minutes
    except Exception:
        pass

    @scheduler.task("interval", id="traffic_analysis", minutes=interval, misfire_grace_time=120)
    def scheduled_analysis():
        from app.analyzer.engine import run_analysis
        run_analysis(scheduler.app)

    def manual_run():
        from app.analyzer.engine import run_analysis
        run_analysis(app)

    app.run_analysis = manual_run
    logger.info("Scheduler: analysis every %d min", interval)
