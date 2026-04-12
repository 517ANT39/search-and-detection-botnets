from flask import Blueprint, render_template
from flask_login import login_required

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/stats")
@login_required
def index():
    return render_template("stats.html")
