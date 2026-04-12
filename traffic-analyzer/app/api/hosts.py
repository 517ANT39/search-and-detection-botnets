from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from app.clickhouse.queries import get_hosts

hosts_bp = Blueprint("hosts", __name__)


@hosts_bp.route("/hosts")
@login_required
def index():
    return render_template("hosts.html")


@hosts_bp.route("/api/hosts")
@login_required
def api_list():
    hosts = get_hosts()
    for h in hosts:
        for k, v in h.items():
            if hasattr(v, "isoformat"):
                h[k] = v.isoformat()
    return jsonify(hosts)
