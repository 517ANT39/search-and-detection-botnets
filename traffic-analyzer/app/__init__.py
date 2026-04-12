import logging
from flask import Flask
from flask_admin import Admin

from app.extensions.config import Config
from app.extensions.extensions import db, login_manager, mail, migrate, scheduler, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # ── Extensions (без Admin) ──────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # ── Blueprints ──────────────────────────────────────────
    from app.auth.routes import auth_bp
    from app.api.dashboard import dashboard_bp
    from app.api.hosts import hosts_bp
    from app.api.alerts import alerts_bp
    from app.api.stats import stats_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(hosts_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(stats_bp)

    csrf.exempt(dashboard_bp)
    csrf.exempt(hosts_bp)
    csrf.exempt(alerts_bp)

    # ── Flask-Admin (создаём здесь, не в extensions) ────────
    from app.admin.views import SecureAdminIndex, init_admin

    flask_admin = Admin(
        app,
        name="Traffic Analyzer",
        template_mode="bootstrap4",
        index_view=SecureAdminIndex(),
    )

    with app.app_context():
        init_admin(flask_admin, db.session)

    # ── Ensure tables ───────────────────────────────────────
    with app.app_context():
        _ensure_tables()

    # ── Seed data ───────────────────────────────────────────
    with app.app_context():
        _seed()

    # ── Scheduler ───────────────────────────────────────────
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
        logging.getLogger("app").warning("Creating tables via db.create_all()")
        db.create_all()


def _seed():
    from app.models import User, Role, AnalyzerSettings

    for rn in ("admin", "viewer"):
        if not Role.query.filter_by(name=rn).first():
            db.session.add(Role(name=rn, description=f"{rn} role"))
    db.session.commit()

    if not User.query.filter_by(username="admin").first():
        role = Role.query.filter_by(name="admin").first()
        u = User(username="admin", email="admin@localhost", is_active=True)
        u.set_password("admin")
        u.roles.append(role)
        db.session.add(u)
        db.session.commit()
        logging.getLogger("app").warning("Default admin created — admin / admin")

    AnalyzerSettings.get_safe()
