from flask import Blueprint, jsonify, request
from flask_login import login_required

from app.clickhouse.queries import (
    get_traffic_summary, get_top_talkers,
    get_protocol_distribution, get_traffic_timeline,
)
from app.models import Alert

dashboard_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/summary")
@login_required
def api_summary():
    minutes = request.args.get("minutes", 60, type=int)
    return jsonify(get_traffic_summary(minutes))


@dashboard_bp.route("/top-talkers")
@login_required
def api_top_talkers():
    minutes = request.args.get("minutes", 60, type=int)
    limit = request.args.get("limit", 20, type=int)
    return jsonify(get_top_talkers(minutes, limit))


@dashboard_bp.route("/protocols")
@login_required
def api_protocols():
    minutes = request.args.get("minutes", 60, type=int)
    return jsonify(get_protocol_distribution(minutes))


@dashboard_bp.route("/timeline")
@login_required
def api_timeline():
    minutes = request.args.get("minutes", 60, type=int)
    interval = request.args.get("interval", 60, type=int)
    data = get_traffic_timeline(minutes, interval)
    for row in data:
        if "ts" in row:
            row["ts"] = str(row["ts"])
    return jsonify(data)


@dashboard_bp.route("/alerts-summary")
@login_required
def api_alerts_summary():
    return jsonify({
        "total": Alert.query.count(),
        "unresolved": Alert.query.filter_by(is_resolved=False).count(),
        "critical": Alert.query.filter_by(severity="critical", is_resolved=False).count(),
        "high": Alert.query.filter_by(severity="high", is_resolved=False).count(),
    })
