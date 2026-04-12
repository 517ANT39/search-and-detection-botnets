from datetime import datetime
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.extensions.extensions import db
from app.models import Alert

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
@login_required
def index():
    return render_template("alerts.html")


@alerts_bp.route("/api/alerts")
@login_required
def api_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    severity = request.args.get("severity")
    alert_type = request.args.get("type")
    unresolved = request.args.get("unresolved", "false") == "true"

    q = Alert.query
    if severity:
        q = q.filter(Alert.severity == severity)
    if alert_type:
        q = q.filter(Alert.alert_type == alert_type)
    if unresolved:
        q = q.filter(Alert.is_resolved == False)

    pag = q.order_by(Alert.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    items = [{
        "id": a.id,
        "host_id": a.host_id,
        "alert_type": a.alert_type,
        "severity": a.severity,
        "title": a.title,
        "description": a.description,
        "src_ip": a.src_ip,
        "dst_ip": a.dst_ip,
        "is_resolved": a.is_resolved,
        "created_at": a.created_at.isoformat(),
        "details": a.details_json,
    } for a in pag.items]

    return jsonify({"items": items, "total": pag.total, "pages": pag.pages, "page": pag.page})


@alerts_bp.route("/api/alerts/&lt;int:alert_id&gt;/resolve", methods=["POST"])
@login_required
def resolve(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_resolved = True
    alert.resolved_by = current_user.id
    alert.resolved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})
