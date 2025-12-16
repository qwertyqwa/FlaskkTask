from __future__ import annotations

from flask import Blueprint
from flask import render_template

from app.db import get_db
from app.roles import roles_required
from app.utils import STATUS_LABELS
from app.utils import format_datetime

bp = Blueprint("manager", __name__, url_prefix="/manager")


@bp.route("/", methods=("GET",))
@roles_required("admin", "manager")
def dashboard():
    db = get_db()

    overdue = db.execute(
        """
        SELECT
          t.id,
          t.request_number,
          t.due_at,
          t.status,
          u.full_name AS specialist_name
        FROM tickets t
        LEFT JOIN users u ON u.id = t.assigned_specialist_id
        WHERE t.due_at IS NOT NULL
          AND t.status != 'completed'
          AND t.due_at < datetime('now')
        ORDER BY t.due_at ASC
        LIMIT 200
        """
    ).fetchall()

    help_requests = db.execute(
        """
        SELECT
          r.id,
          r.ticket_id,
          r.requested_at,
          r.message,
          t.request_number,
          req.full_name AS requested_by_name
        FROM ticket_help_requests r
        JOIN tickets t ON t.id = r.ticket_id
        JOIN users req ON req.id = r.requested_by_user_id
        WHERE r.status = 'open'
        ORDER BY r.requested_at DESC
        LIMIT 200
        """
    ).fetchall()

    return render_template(
        "manager/dashboard.html",
        overdue=overdue,
        help_requests=help_requests,
        status_labels=STATUS_LABELS,
        format_datetime=format_datetime,
    )

