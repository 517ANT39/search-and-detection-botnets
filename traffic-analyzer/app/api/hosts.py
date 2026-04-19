from flask import Blueprint, jsonify
from flask_login import login_required
from app.clickhouse.queries import get_hosts

hosts_bp = Blueprint("hosts_api", __name__, url_prefix="/api/hosts")


@hosts_bp.route("/")
@login_required
def api_list():
    hosts = get_hosts()
    for h in hosts:
        for k, v in h.items():
            if hasattr(v, "isoformat"):
                h[k] = v.isoformat()
    return jsonify(hosts)
