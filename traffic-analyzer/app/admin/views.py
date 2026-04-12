import logging
from flask import redirect, url_for, request, flash
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose, BaseView
from flask_login import current_user

logger = logging.getLogger("admin")


class AuthMixin:
    """Проверка: залогинен + роль admin."""

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        flash("Admin access required.", "danger")
        return redirect(url_for("dashboard.index"))


class SecureAdminIndex(AuthMixin, AdminIndexView):
    @expose("/")
    def index(self):
        from app.models import Alert, User

        hosts_count = 0
        try:
            from app.clickhouse.queries import get_hosts
            hosts_count = len(get_hosts())
        except Exception as e:
            logger.warning("ClickHouse: %s", e)

        stats = {
            "total_users": User.query.count(),
            "total_alerts": Alert.query.count(),
            "unresolved_alerts": Alert.query.filter_by(is_resolved=False).count(),
            "total_hosts": hosts_count,
        }
        return self.render("admin/index.html", stats=stats)


class UserAdmin(AuthMixin, ModelView):
    column_list = ["id", "username", "email", "is_active", "roles", "created_at", "last_login"]
    column_searchable_list = ["username", "email"]
    column_filters = ["is_active"]
    form_excluded_columns = ["password_hash", "last_login"]
    column_editable_list = ["is_active"]


class RoleAdmin(AuthMixin, ModelView):
    column_list = ["id", "name", "description"]


class AlertAdmin(AuthMixin, ModelView):
    column_list = ["id", "host_id", "alert_type", "severity", "title", "is_resolved", "created_at"]
    column_searchable_list = ["host_id", "src_ip", "dst_ip", "title"]
    column_filters = ["severity", "alert_type", "is_resolved"]
    column_default_sort = ("created_at", True)
    can_create = False


class NotificationGroupAdmin(AuthMixin, ModelView):
    column_list = ["id", "name", "is_active", "severity_filter", "members"]
    form_columns = ["name", "description", "is_active", "severity_filter", "extra_emails", "members"]


class AnalyzerSettingsAdmin(AuthMixin, ModelView):
    column_list = [
        "contamination", "n_estimators", "window_minutes", "schedule_minutes",
        "port_scan_threshold", "ddos_pps_threshold", "ddos_bps_threshold",
        "enable_isolation_forest", "enable_port_scan_detect", "enable_ddos_detect",
    ]
    can_create = False
    can_delete = False

    def on_model_change(self, form, model, is_created):
        from app.extensions.extensions import scheduler
        job = scheduler.get_job("traffic_analysis")
        if job:
            from apscheduler.triggers.interval import IntervalTrigger
            job.reschedule(trigger=IntervalTrigger(minutes=model.schedule_minutes))


class RunAnalysisView(AuthMixin, BaseView):
    @expose("/", methods=["GET", "POST"])
    def run(self):
        if request.method == "POST":
            from flask import current_app
            current_app.run_analysis()
            flash("Analysis triggered.", "success")
        return redirect(url_for("admin.index"))


def init_admin(admin_instance, db_session):
    from app.models import User, Role, Alert, NotificationGroup, AnalyzerSettings

    admin_instance.add_view(UserAdmin(User, db_session, name="Users", category="Access"))
    admin_instance.add_view(RoleAdmin(Role, db_session, name="Roles", category="Access"))
    admin_instance.add_view(AlertAdmin(Alert, db_session, name="Alerts"))
    admin_instance.add_view(NotificationGroupAdmin(NotificationGroup, db_session,
                                                    name="Notification Groups", category="Notifications"))
    admin_instance.add_view(AnalyzerSettingsAdmin(AnalyzerSettings, db_session,
                                                   name="Analyzer Settings", category="Settings"))
    admin_instance.add_view(RunAnalysisView(name="Run Analysis", endpoint="run_analysis", category="Settings"))
