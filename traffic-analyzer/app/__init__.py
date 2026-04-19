import logging
from flask import Flask
from flask_admin import Admin

from app.extensions.config import Config
from app.extensions.extensions import db, login_manager, mail, migrate, scheduler, csrf, babel


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    babel.init_app(app)

    from app.admin.views import DashboardView, init_admin

    flask_admin = Admin(
        app,
        name="Анализатор трафика",
        template_mode="bootstrap4",
        index_view=DashboardView(name="Дашборд", url="/"),
    )

    with app.app_context():
        init_admin(flask_admin, db.session)

    from app.auth.routes import auth_bp
    from app.api.dashboard import dashboard_bp
    from app.api.hosts import hosts_bp
    from app.api.alerts import alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hosts_bp)
    app.register_blueprint(alerts_bp)

    csrf.exempt(dashboard_bp)
    csrf.exempt(hosts_bp)
    csrf.exempt(alerts_bp)

    with app.app_context():
        _ensure_tables()

    with app.app_context():
        _seed()

    scheduler.init_app(app)
    from app.analyzer.scheduler import init_scheduler
    init_scheduler(app)
    scheduler.start()

    return app


def _ensure_tables():
    try:
        from app.models import AnalyzerSettings
        AnalyzerSettings.query.first()
    except Exception:
        db.session.rollback()
        logging.getLogger("app").warning("Таблицы не найдены — создаю через db.create_all()")
        db.create_all()


def _seed():
    from app.models import User, Role, AnalyzerSettings

    for rn, desc in [("admin", "Администратор"), ("viewer", "Наблюдатель")]:
        if not Role.query.filter_by(name=rn).first():
            db.session.add(Role(name=rn, description=desc))
    db.session.commit()

    if not User.query.filter_by(username="admin").first():
        role = Role.query.filter_by(name="admin").first()
        u = User(username="admin", email="admin@localhost", is_active=True)
        u.set_password("admin")
        u.roles.append(role)
        db.session.add(u)
        db.session.commit()
        logging.getLogger("app").warning("Создан администратор по умолчанию — admin / admin")

    AnalyzerSettings.get_safe()
