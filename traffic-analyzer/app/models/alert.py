from datetime import datetime
from app.extensions.extensions import db


class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.String(255), nullable=False, index=True)
    alert_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="medium")
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    details_json = db.Column(db.JSON)
    src_ip = db.Column(db.String(45))
    dst_ip = db.Column(db.String(45))
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __str__(self):
        return f"[{self.severity}] {self.title}"
