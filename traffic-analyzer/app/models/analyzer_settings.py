from app.extensions.extensions import db


class AnalyzerSettings(db.Model):
    __tablename__ = "analyzer_settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, default="default")

    contamination = db.Column(db.Float, default=0.05)
    n_estimators = db.Column(db.Integer, default=200)
    window_minutes = db.Column(db.Integer, default=10)
    min_samples = db.Column(db.Integer, default=100)
    schedule_minutes = db.Column(db.Integer, default=5)

    port_scan_threshold = db.Column(db.Integer, default=50)
    ddos_pps_threshold = db.Column(db.Integer, default=10000)
    ddos_bps_threshold = db.Column(db.BigInteger, default=100_000_000)

    enable_isolation_forest = db.Column(db.Boolean, default=True)
    enable_port_scan_detect = db.Column(db.Boolean, default=True)
    enable_ddos_detect = db.Column(db.Boolean, default=True)

    @classmethod
    def get_safe(cls):
        """Возвращает настройки или None если таблица не существует."""
        try:
            s = cls.query.filter_by(key="default").first()
            if not s:
                s = cls(key="default")
                db.session.add(s)
                db.session.commit()
            return s
        except Exception:
            db.session.rollback()
            return None

    def __str__(self):
        return f"AnalyzerSettings(contamination={self.contamination})"
