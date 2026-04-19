import logging
from flask import redirect, url_for, request, flash
from flask_admin.contrib.sqla import ModelView
from flask_admin import AdminIndexView, expose, BaseView
from flask_login import current_user

logger = logging.getLogger("admin")


class AuthMixin:
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))


class AdminOnlyMixin:
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))
        flash("Требуются права администратора.", "danger")
        return redirect(url_for("admin.index"))


# ═══════════════════════════════════════════════════════════
#  Главная — Дашборд
# ═══════════════════════════════════════════════════════════

class DashboardView(AuthMixin, AdminIndexView):
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
        return self.render("dashboard.html", stats=stats)


# ═══════════════════════════════════════════════════════════
#  Страницы мониторинга
# ═══════════════════════════════════════════════════════════

class HostsView(AuthMixin, BaseView):
    @expose("/")
    def index(self):
        return self.render("hosts.html")


class AlertsPageView(AuthMixin, BaseView):
    @expose("/")
    def index(self):
        return self.render("alerts.html")


class StatsView(AuthMixin, BaseView):
    @expose("/")
    def index(self):
        return self.render("stats.html")


# ═══════════════════════════════════════════════════════════
#  Модели (только для админов)
# ═══════════════════════════════════════════════════════════

class UserAdmin(AdminOnlyMixin, ModelView):
    column_list = ["id", "username", "email", "is_active", "roles", "created_at", "last_login"]
    column_labels = {
        "id": "ID",
        "username": "Имя пользователя",
        "email": "Эл. почта",
        "is_active": "Активен",
        "roles": "Роли",
        "created_at": "Создан",
        "last_login": "Последний вход",
    }
    column_searchable_list = ["username", "email"]
    column_filters = ["is_active"]
    form_excluded_columns = ["password_hash", "last_login"]
    column_editable_list = ["is_active"]


class RoleAdmin(AdminOnlyMixin, ModelView):
    column_list = ["id", "name", "description"]
    column_labels = {
        "id": "ID",
        "name": "Название",
        "description": "Описание",
    }


class AlertAdmin(AdminOnlyMixin, ModelView):
    column_list = ["id", "host_id", "alert_type", "severity", "title", "is_resolved", "created_at"]
    column_labels = {
        "id": "ID",
        "host_id": "Узел",
        "alert_type": "Тип",
        "severity": "Критичность",
        "title": "Заголовок",
        "is_resolved": "Решено",
        "created_at": "Создано",
    }
    column_searchable_list = ["host_id", "src_ip", "dst_ip", "title"]
    column_filters = ["severity", "alert_type", "is_resolved"]
    column_default_sort = ("created_at", True)
    can_create = False


class NotificationGroupAdmin(AdminOnlyMixin, ModelView):
    column_list = ["id", "name", "is_active", "severity_filter", "members"]
    column_labels = {
        "id": "ID",
        "name": "Название группы",
        "is_active": "Активна",
        "severity_filter": "Фильтр критичности",
        "members": "Участники",
        "description": "Описание",
        "extra_emails": "Доп. адреса",
    }
    form_columns = ["name", "description", "is_active", "severity_filter", "extra_emails", "members"]


class AnalyzerSettingsAdmin(AdminOnlyMixin, ModelView):
    column_list = [
        "contamination", "n_estimators", "window_minutes", "schedule_minutes",
        "port_scan_threshold", "ddos_pps_threshold", "ddos_bps_threshold",
        "enable_isolation_forest", "enable_port_scan_detect", "enable_ddos_detect",
    ]
    column_labels = {
        "contamination": "Контаминация",
        "n_estimators": "Кол-во деревьев",
        "window_minutes": "Окно анализа (мин)",
        "schedule_minutes": "Интервал запуска (мин)",
        "min_samples": "Мин. кол-во образцов",
        "port_scan_threshold": "Порог сканирования портов",
        "ddos_pps_threshold": "Порог DDoS (пакетов/сек)",
        "ddos_bps_threshold": "Порог DDoS (байт/сек)",
        "enable_isolation_forest": "IsolationForest вкл.",
        "enable_port_scan_detect": "Обнаружение сканирования вкл.",
        "enable_ddos_detect": "Обнаружение DDoS вкл.",
    }
    can_create = False
    can_delete = False

    def on_model_change(self, form, model, is_created):
        from app.extensions.extensions import scheduler
        job = scheduler.get_job("traffic_analysis")
        if job:
            from apscheduler.triggers.interval import IntervalTrigger
            job.reschedule(trigger=IntervalTrigger(minutes=model.schedule_minutes))


class RunAnalysisView(AdminOnlyMixin, BaseView):
    @expose("/", methods=["GET", "POST"])
    def run(self):
        if request.method == "POST":
            from flask import current_app
            current_app.run_analysis()
            flash("Анализ запущен.", "success")
        return redirect(url_for("admin.index"))


# ═══════════════════════════════════════════════════════════
#  Регистрация
# ═══════════════════════════════════════════════════════════

def init_admin(admin_instance, db_session):
    from app.models import User, Role, Alert, NotificationGroup, AnalyzerSettings

    admin_instance.add_view(HostsView(
        name="Узлы", endpoint="hosts_page", url="/hosts/",
        category="Мониторинг",
    ))
    admin_instance.add_view(AlertsPageView(
        name="Оповещения", endpoint="alerts_page", url="/alerts/",
        category="Мониторинг",
    ))
    admin_instance.add_view(StatsView(
        name="Статистика", endpoint="stats_page", url="/stats/",
        category="Мониторинг",
    ))

    admin_instance.add_view(AlertAdmin(
        Alert, db_session, name="Журнал оповещений", category="Управление данными",
    ))

    admin_instance.add_view(UserAdmin(
        User, db_session, name="Пользователи", category="Администрирование",
    ))
    admin_instance.add_view(RoleAdmin(
        Role, db_session, name="Роли", category="Администрирование",
    ))
    admin_instance.add_view(NotificationGroupAdmin(
        NotificationGroup, db_session, name="Группы рассылки", category="Администрирование",
    ))
    admin_instance.add_view(AnalyzerSettingsAdmin(
        AnalyzerSettings, db_session, name="Настройки анализатора", category="Администрирование",
    ))
    admin_instance.add_view(RunAnalysisView(
        name="Запустить анализ", endpoint="run_analysis", category="Администрирование",
    ))
