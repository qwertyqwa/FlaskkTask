from __future__ import annotations

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import url_for

from app.auth import login_required
from app.db import get_db
from app.utils import format_datetime

bp = Blueprint("notifications", __name__)


@bp.route("/notifications", methods=("GET",))
@login_required
def list_notifications():
    db = get_db()
    rows = db.execute(
        """
        SELECT n.*, t.request_number
        FROM notifications n
        LEFT JOIN tickets t ON t.id = n.ticket_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 200
        """,
        (int(g.user["id"]),),
    ).fetchall()
    return render_template("notifications/list.html", notifications=rows, format_datetime=format_datetime)


@bp.route("/notifications/mark-all-read", methods=("POST",))
@login_required
def mark_all_read():
    db = get_db()
    db.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
        (int(g.user["id"]),),
    )
    db.commit()
    flash("Уведомления отмечены как прочитанные.", "success")
    return redirect(url_for("notifications.list_notifications"))
