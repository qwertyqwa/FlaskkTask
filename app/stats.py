from __future__ import annotations

from flask import Blueprint
from flask import flash
from flask import render_template
from flask import request

from app.db import get_db
from app.roles import roles_required
from app.services.statistics import calculate_statistics
from app.utils import format_duration_seconds
from app.utils import parse_iso

bp = Blueprint("stats", __name__)


@bp.route("/stats", methods=("GET",))
@roles_required("admin", "operator")
def stats_view():
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    rows = []
    result = None

    if date_from or date_to:
        date_from_iso, date_to_iso = _validate_period(date_from, date_to)
        if date_from_iso and date_to_iso:
            rows = _fetch_completed(date_from_iso, date_to_iso)
            result = calculate_statistics(rows)
            if result.completed_count == 0:
                flash("За выбранный период выполненных заявок нет.", "info")

    return render_template(
        "stats/view.html",
        date_from=date_from,
        date_to=date_to,
        result=result,
        format_duration_seconds=format_duration_seconds,
    )


def _validate_period(date_from: str, date_to: str) -> tuple[str | None, str | None]:
    if not date_from or not date_to:
        flash("Укажите обе даты периода.", "warning")
        return None, None

    from_dt = parse_iso(date_from)
    to_dt = parse_iso(date_to)
    if from_dt is None or to_dt is None:
        flash("Некорректный формат дат. Используйте YYYY-MM-DD.", "warning")
        return None, None

    if from_dt > to_dt:
        flash("Дата 'с' не может быть больше даты 'по'.", "warning")
        return None, None

    start = from_dt.strftime("%Y-%m-%d 00:00:00")
    end = to_dt.strftime("%Y-%m-%d 23:59:59")
    return start, end


def _fetch_completed(date_from_iso: str, date_to_iso: str) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT created_at, completed_at, problem_description
        FROM tickets
        WHERE status = 'completed'
          AND completed_at IS NOT NULL
          AND completed_at BETWEEN ? AND ?
        """,
        (date_from_iso, date_to_iso),
    ).fetchall()
    return [dict(row) for row in rows]

