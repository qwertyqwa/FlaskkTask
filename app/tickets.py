from __future__ import annotations

import base64
import io
from datetime import datetime

from flask import Blueprint
from flask import Response
from flask import abort
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from app.auth import login_required
from app.db import get_db
from app.roles import roles_required
from app.services.notifications import create_notification
from app.utils import STATUS_LABELS
from app.utils import FEEDBACK_FORM_URL
from app.utils import format_datetime
from app.utils import generate_request_number
from app.utils import now_iso
from app.utils import normalize_search_tokens
from app.utils import parse_iso
from app.utils import status_options
from app.utils import validate_phone

bp = Blueprint("tickets", __name__, url_prefix="/tickets")


def _get_specialists():
    db = get_db()
    return db.execute(
        """
        SELECT id, full_name
        FROM users
        WHERE role = 'specialist' AND is_active = 1
        ORDER BY full_name
        """
    ).fetchall()


def _ticket_access_allowed(ticket_row) -> bool:
    if g.user is None:
        return False
    if g.user["role"] in {"admin", "operator", "manager"}:
        return True
    if g.user["role"] != "specialist":
        return False
    if ticket_row["assigned_specialist_id"] == g.user["id"]:
        return True
    return _is_assistant_specialist(ticket_id=int(ticket_row["id"]), user_id=int(g.user["id"]))


def _is_assistant_specialist(*, ticket_id: int, user_id: int) -> bool:
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM ticket_specialists WHERE ticket_id = ? AND specialist_user_id = ?",
        (ticket_id, user_id),
    ).fetchone()
    return row is not None


def _get_ticket_row(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)
    return ticket


@bp.route("/", methods=("GET",))
@login_required
def list_tickets():
    db = get_db()

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    specialist_id = request.args.get("specialist_id", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    clauses: list[str] = []
    params: list[object] = []

    if g.user["role"] == "specialist":
        clauses.append(
            "(t.assigned_specialist_id = ? OR EXISTS (SELECT 1 FROM ticket_specialists ts WHERE ts.ticket_id = t.id AND ts.specialist_user_id = ?))"
        )
        params.append(int(g.user["id"]))
        params.append(int(g.user["id"]))

    if status in STATUS_LABELS:
        clauses.append("t.status = ?")
        params.append(status)

    if specialist_id and g.user["role"] in {"admin", "operator", "manager"}:
        try:
            specialist_int = int(specialist_id)
        except ValueError:
            flash("Некорректный фильтр специалиста.", "warning")
        else:
            clauses.append("t.assigned_specialist_id = ?")
            params.append(specialist_int)

    if date_from:
        parsed = parse_iso(date_from)
        if parsed is None:
            flash("Некорректная дата 'с'. Используйте формат YYYY-MM-DD.", "warning")
        else:
            clauses.append("t.created_at >= ?")
            params.append(parsed.strftime("%Y-%m-%d 00:00:00"))

    if date_to:
        parsed = parse_iso(date_to)
        if parsed is None:
            flash("Некорректная дата 'по'. Используйте формат YYYY-MM-DD.", "warning")
        else:
            clauses.append("t.created_at <= ?")
            params.append(parsed.strftime("%Y-%m-%d 23:59:59"))

    if q:
        token_clauses: list[str] = []
        for token in normalize_search_tokens(q):
            token_clauses.append(
                "(t.request_number LIKE ? OR t.customer_full_name LIKE ? OR t.customer_phone LIKE ? OR "
                "t.equipment_type LIKE ? OR t.device_model LIKE ?)"
            )
            like = f"%{token}%"
            params.extend([like, like, like, like, like])
        clauses.append("(" + " AND ".join(token_clauses) + ")")

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    tickets = db.execute(
        f"""
        SELECT
          t.*,
          u.full_name AS specialist_name,
          CASE
            WHEN t.due_at IS NOT NULL AND t.status != 'completed' AND t.due_at < datetime('now')
              THEN 1
            ELSE 0
          END AS is_overdue
        FROM tickets t
        LEFT JOIN users u ON u.id = t.assigned_specialist_id
        {where_sql}
        ORDER BY t.created_at DESC
        """,
        params,
    ).fetchall()

    if q and not tickets:
        flash("По вашему запросу заявок не найдено.", "info")

    return render_template(
        "tickets/list.html",
        tickets=tickets,
        status_options=status_options(),
        status_labels=STATUS_LABELS,
        q=q,
        selected_status=status,
        specialists=_get_specialists(),
        selected_specialist_id=specialist_id,
        date_from=date_from,
        date_to=date_to,
        format_datetime=format_datetime,
    )


@bp.route("/new", methods=("GET", "POST"))
@roles_required("admin", "operator")
def create_ticket():
    db = get_db()
    specialists = _get_specialists()

    if request.method == "POST":
        equipment_type = request.form.get("equipment_type", "").strip()
        device_model = request.form.get("device_model", "").strip()
        problem_description = request.form.get("problem_description", "").strip()
        customer_full_name = request.form.get("customer_full_name", "").strip()
        customer_phone = request.form.get("customer_phone", "").strip()
        due_date = request.form.get("due_date", "").strip()
        specialist_id_raw = request.form.get("assigned_specialist_id", "").strip()

        if not equipment_type:
            flash("Укажите тип оборудования.", "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)
        if not device_model:
            flash("Укажите модель устройства.", "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)
        if not problem_description:
            flash("Опишите проблему.", "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)
        if not customer_full_name:
            flash("Укажите ФИО заказчика.", "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)

        ok, normalized_phone_or_error = validate_phone(customer_phone)
        if not ok:
            flash(normalized_phone_or_error, "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)
        customer_phone = normalized_phone_or_error

        created_at = now_iso()
        updated_at = created_at
        request_number = generate_request_number(db, created_at)
        status = "open"
        due_at: str | None = None
        if due_date:
            parsed_due = parse_iso(due_date)
            if parsed_due is None:
                flash("Некорректная дата срока. Используйте формат YYYY-MM-DD.", "error")
                return render_template("tickets/new.html", specialists=specialists, form=request.form)
            due_at = parsed_due.strftime("%Y-%m-%d 23:59:59")

        assigned_specialist_id: int | None = None
        if specialist_id_raw:
            try:
                assigned_specialist_id = int(specialist_id_raw)
            except ValueError:
                flash("Некорректный специалист.", "error")
                return render_template("tickets/new.html", specialists=specialists, form=request.form)

        try:
            cur = db.execute(
                """
                INSERT INTO tickets (
                  request_number,
                  created_at,
                  equipment_type,
                  device_model,
                  problem_description,
                  customer_full_name,
                  customer_phone,
                  status,
                  assigned_specialist_id,
                  due_at,
                  completed_at,
                  updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_number,
                    created_at,
                    equipment_type,
                    device_model,
                    problem_description,
                    customer_full_name,
                    customer_phone,
                    status,
                    assigned_specialist_id,
                    due_at,
                    None,
                    updated_at,
                ),
            )
            ticket_id = int(cur.lastrowid)
            db.execute(
                """
                INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ticket_id, None, status, int(g.user["id"]), created_at, "Создание заявки"),
            )
            if due_at:
                db.execute(
                    """
                    INSERT INTO ticket_due_history (ticket_id, old_due_at, new_due_at, changed_by_user_id, changed_at, customer_agreed, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ticket_id, None, due_at, int(g.user["id"]), created_at, 0, "Установка срока выполнения"),
                )
            db.commit()
        except Exception:
            db.rollback()
            flash("Не удалось создать заявку. Повторите попытку.", "error")
            return render_template("tickets/new.html", specialists=specialists, form=request.form)

        if assigned_specialist_id is not None:
            create_notification(
                db=db,
                user_id=assigned_specialist_id,
                ticket_id=ticket_id,
                type_="assigned",
                message=f"Вам назначена заявка {request_number}.",
            )

        flash(f"Заявка {request_number} создана.", "success")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    return render_template("tickets/new.html", specialists=specialists, form={})


@bp.route("/<int:ticket_id>", methods=("GET",))
@login_required
def view_ticket(ticket_id: int):
    db = get_db()
    ticket = db.execute(
        """
        SELECT
          t.*,
          u.full_name AS specialist_name
        FROM tickets t
        LEFT JOIN users u ON u.id = t.assigned_specialist_id
        WHERE t.id = ?
        """,
        (ticket_id,),
    ).fetchone()
    if ticket is None:
        abort(404)

    if not _ticket_access_allowed(ticket):
        abort(403)

    assistants = db.execute(
        """
        SELECT u.id, u.full_name
        FROM ticket_specialists ts
        JOIN users u ON u.id = ts.specialist_user_id
        WHERE ts.ticket_id = ?
        ORDER BY u.full_name
        """,
        (ticket_id,),
    ).fetchall()
    assistant_ids = {int(row["id"]) for row in assistants}

    due_history = db.execute(
        """
        SELECT h.*, u.full_name
        FROM ticket_due_history h
        JOIN users u ON u.id = h.changed_by_user_id
        WHERE h.ticket_id = ?
        ORDER BY h.changed_at DESC
        """,
        (ticket_id,),
    ).fetchall()

    help_requests = db.execute(
        """
        SELECT
          r.*,
          req.full_name AS requested_by_name,
          res.full_name AS resolved_by_name
        FROM ticket_help_requests r
        JOIN users req ON req.id = r.requested_by_user_id
        LEFT JOIN users res ON res.id = r.resolved_by_user_id
        WHERE r.ticket_id = ?
        ORDER BY r.requested_at DESC
        """,
        (ticket_id,),
    ).fetchall()

    review = db.execute(
        """
        SELECT rv.*, u.full_name AS recorded_by_name
        FROM ticket_reviews rv
        JOIN users u ON u.id = rv.recorded_by_user_id
        WHERE rv.ticket_id = ?
        """,
        (ticket_id,),
    ).fetchone()

    comments = db.execute(
        """
        SELECT c.*, u.full_name
        FROM ticket_comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.ticket_id = ?
        ORDER BY c.created_at DESC
        """,
        (ticket_id,),
    ).fetchall()

    parts = db.execute(
        """
        SELECT p.*, u.full_name
        FROM ticket_parts p
        JOIN users u ON u.id = p.created_by_user_id
        WHERE p.ticket_id = ?
        ORDER BY p.created_at DESC
        """,
        (ticket_id,),
    ).fetchall()

    history = db.execute(
        """
        SELECT h.*, u.full_name
        FROM status_history h
        JOIN users u ON u.id = h.changed_by_user_id
        WHERE h.ticket_id = ?
        ORDER BY h.changed_at DESC
        """,
        (ticket_id,),
    ).fetchall()

    specialists = _get_specialists() if g.user["role"] in {"admin", "operator", "manager"} else []

    is_overdue = False
    due_at = parse_iso(ticket["due_at"])
    if due_at is not None and ticket["status"] != "completed":
        if due_at < datetime.now():
            is_overdue = True

    is_specialist_worker = False
    if g.user["role"] == "specialist":
        is_specialist_worker = ticket["assigned_specialist_id"] == g.user["id"] or _is_assistant_specialist(
            ticket_id=ticket_id,
            user_id=int(g.user["id"]),
        )

    can_change_status = g.user["role"] in {"admin", "operator"} or is_specialist_worker
    can_add_parts = g.user["role"] in {"admin", "operator"} or is_specialist_worker
    can_request_help = is_specialist_worker and ticket["status"] != "completed"
    can_manager_actions = g.user["role"] in {"admin", "manager"}

    feedback_url = f"{FEEDBACK_FORM_URL}&ticket={ticket['request_number']}"
    
    # Генерируем QR код как data URI
    qr_data_uri = None
    try:
        import segno
        qr_url = f"{FEEDBACK_FORM_URL}&ticket={ticket['request_number']}"
        qr = segno.make(qr_url)
        buffer = io.BytesIO()
        qr.save(buffer, kind="svg", scale=5, border=2, xmldecl=False)
        svg_bytes = buffer.getvalue()
        svg_base64 = base64.b64encode(svg_bytes).decode("utf-8")
        qr_data_uri = f"data:image/svg+xml;base64,{svg_base64}"
    except Exception:
        pass  # Если не удалось сгенерировать QR, оставляем None

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        assistants=assistants,
        assistant_ids=assistant_ids,
        due_history=due_history,
        help_requests=help_requests,
        review=review,
        feedback_url=feedback_url,
        comments=comments,
        parts=parts,
        history=history,
        is_overdue=is_overdue,
        status_labels=STATUS_LABELS,
        status_options=status_options(),
        specialists=specialists,
        can_change_status=can_change_status,
        can_add_parts=can_add_parts,
        can_request_help=can_request_help,
        can_manager_actions=can_manager_actions,
        format_datetime=format_datetime,
        qr_data_uri=qr_data_uri,
    )


@bp.route("/<int:ticket_id>/qr", methods=("GET",))
@login_required
def ticket_qr(ticket_id: int):
    ticket = _get_ticket_row(ticket_id)
    if not _ticket_access_allowed(ticket):
        abort(403)

    try:
        import segno
    except Exception:
        abort(503)

    url = f"{FEEDBACK_FORM_URL}&ticket={ticket['request_number']}"
    qr = segno.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=5, border=2, xmldecl=False)
    svg_bytes = buffer.getvalue()
    return Response(svg_bytes, mimetype="image/svg+xml")


@bp.route("/<int:ticket_id>/assistants/add", methods=("POST",))
@roles_required("admin", "manager")
def add_assistant(ticket_id: int):
    db = get_db()
    ticket = _get_ticket_row(ticket_id)

    specialist_id_raw = request.form.get("specialist_user_id", "").strip()
    if not specialist_id_raw:
        flash("Выберите специалиста для привлечения.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    try:
        specialist_user_id = int(specialist_id_raw)
    except ValueError:
        flash("Некорректный специалист.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    specialist = db.execute(
        "SELECT id, full_name FROM users WHERE id = ? AND role = 'specialist' AND is_active = 1",
        (specialist_user_id,),
    ).fetchone()
    if specialist is None:
        flash("Специалист не найден или заблокирован.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    try:
        db.execute(
            """
            INSERT INTO ticket_specialists (ticket_id, specialist_user_id, added_by_user_id, added_at)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, specialist_user_id, int(g.user["id"]), now_iso()),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось привлечь специалиста. Возможно, он уже добавлен.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    create_notification(
        db=db,
        user_id=specialist_user_id,
        ticket_id=ticket_id,
        type_="assistant_added",
        message=f"Вас привлекли к заявке {ticket['request_number']} как помощника.",
    )
    flash("Специалист добавлен к заявке.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/assistants/<int:specialist_user_id>/remove", methods=("POST",))
@roles_required("admin", "manager")
def remove_assistant(ticket_id: int, specialist_user_id: int):
    db = get_db()
    _get_ticket_row(ticket_id)

    try:
        cur = db.execute(
            "DELETE FROM ticket_specialists WHERE ticket_id = ? AND specialist_user_id = ?",
            (ticket_id, specialist_user_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось удалить привлеченного специалиста.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if cur.rowcount == 0:
        flash("Привлеченный специалист не найден.", "info")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    create_notification(
        db=db,
        user_id=specialist_user_id,
        ticket_id=ticket_id,
        type_="assistant_removed",
        message="Вас исключили из привлеченных специалистов по заявке.",
    )
    flash("Привлеченный специалист удален.", "info")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/due", methods=("POST",))
@roles_required("admin", "manager")
def extend_due_date(ticket_id: int):
    db = get_db()
    ticket = _get_ticket_row(ticket_id)

    due_date = request.form.get("due_date", "").strip()
    customer_agreed = request.form.get("customer_agreed") == "on"
    comment = request.form.get("comment", "").strip()

    if not due_date:
        flash("Укажите новую дату срока выполнения.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    parsed_due = parse_iso(due_date)
    if parsed_due is None:
        flash("Некорректная дата срока. Используйте формат YYYY-MM-DD.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if not customer_agreed:
        flash("Продление срока возможно только с согласованием заказчика.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    new_due_at = parsed_due.strftime("%Y-%m-%d 23:59:59")
    old_due_at = ticket["due_at"]

    if old_due_at == new_due_at:
        flash("Срок не изменился.", "info")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    old_due_dt = parse_iso(old_due_at)
    new_due_dt = parse_iso(new_due_at)
    if old_due_dt is not None and new_due_dt is not None and new_due_dt < old_due_dt:
        flash("Новый срок не может быть меньше текущего. Можно только продлить.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    changed_at = now_iso()
    history_comment = comment or "Продление срока выполнения"

    try:
        db.execute(
            "UPDATE tickets SET due_at = ?, updated_at = ? WHERE id = ?",
            (new_due_at, changed_at, ticket_id),
        )
        db.execute(
            """
            INSERT INTO ticket_due_history (ticket_id, old_due_at, new_due_at, changed_by_user_id, changed_at, customer_agreed, comment)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (ticket_id, old_due_at, new_due_at, int(g.user["id"]), changed_at, history_comment),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось продлить срок. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    recipients = set()
    if ticket["assigned_specialist_id"] is not None:
        recipients.add(int(ticket["assigned_specialist_id"]))

    assistant_rows = db.execute(
        "SELECT specialist_user_id FROM ticket_specialists WHERE ticket_id = ?",
        (ticket_id,),
    ).fetchall()
    for row in assistant_rows:
        recipients.add(int(row["specialist_user_id"]))

    for user_id in recipients:
        create_notification(
            db=db,
            user_id=user_id,
            ticket_id=ticket_id,
            type_="due_changed",
            message=f"Срок выполнения заявки {ticket['request_number']} изменен на {new_due_at}.",
        )

    flash("Срок выполнения обновлен.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/help", methods=("POST",))
@login_required
def request_help(ticket_id: int):
    db = get_db()
    ticket = _get_ticket_row(ticket_id)
    if not _ticket_access_allowed(ticket):
        abort(403)

    is_specialist_worker = g.user["role"] == "specialist"
    if is_specialist_worker:
        is_specialist_worker = ticket["assigned_specialist_id"] == g.user["id"] or _is_assistant_specialist(
            ticket_id=ticket_id,
            user_id=int(g.user["id"]),
        )
    if not is_specialist_worker:
        flash("Запрос помощи доступен только специалисту, выполняющему заявку.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if ticket["status"] == "completed":
        flash("Нельзя запрашивать помощь для завершенной заявки.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    message = request.form.get("message", "").strip()
    if not message:
        flash("Опишите проблему и причину запроса помощи.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    requested_at = now_iso()
    try:
        db.execute(
            """
            INSERT INTO ticket_help_requests (ticket_id, requested_by_user_id, requested_at, message, status)
            VALUES (?, ?, ?, ?, 'open')
            """,
            (ticket_id, int(g.user["id"]), requested_at, message),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось отправить запрос помощи. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    managers = db.execute("SELECT id FROM users WHERE role = 'manager' AND is_active = 1").fetchall()
    for manager in managers:
        create_notification(
            db=db,
            user_id=int(manager["id"]),
            ticket_id=ticket_id,
            type_="help_requested",
            message=f"Запрос помощи по заявке {ticket['request_number']}: {message}",
        )

    flash("Запрос помощи отправлен менеджеру по качеству.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/help/<int:help_id>/resolve", methods=("POST",))
@roles_required("admin", "manager")
def resolve_help(ticket_id: int, help_id: int):
    db = get_db()
    ticket = _get_ticket_row(ticket_id)
    resolution_comment = request.form.get("resolution_comment", "").strip()

    help_row = db.execute(
        "SELECT * FROM ticket_help_requests WHERE id = ? AND ticket_id = ?",
        (help_id, ticket_id),
    ).fetchone()
    if help_row is None:
        flash("Запрос помощи не найден.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if help_row["status"] != "open":
        flash("Запрос помощи уже закрыт.", "info")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    resolved_at = now_iso()
    try:
        db.execute(
            """
            UPDATE ticket_help_requests
            SET status = 'resolved',
                resolved_by_user_id = ?,
                resolved_at = ?,
                resolution_comment = ?
            WHERE id = ?
            """,
            (int(g.user["id"]), resolved_at, resolution_comment or None, help_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось закрыть запрос помощи. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    create_notification(
        db=db,
        user_id=int(help_row["requested_by_user_id"]),
        ticket_id=ticket_id,
        type_="help_resolved",
        message=f"Запрос помощи по заявке {ticket['request_number']} закрыт. {resolution_comment}".strip(),
    )

    flash("Запрос помощи закрыт.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/review", methods=("POST",))
@roles_required("admin", "manager")
def record_review(ticket_id: int):
    db = get_db()
    _get_ticket_row(ticket_id)

    rating_raw = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    try:
        rating = int(rating_raw)
    except ValueError:
        flash("Оценка должна быть числом от 1 до 5.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if rating < 1 or rating > 5:
        flash("Оценка должна быть в диапазоне 1–5.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    created_at = now_iso()
    try:
        db.execute(
            """
            INSERT INTO ticket_reviews (ticket_id, rating, comment, source, recorded_by_user_id, created_at)
            VALUES (?, ?, ?, 'manual', ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
              rating = excluded.rating,
              comment = excluded.comment,
              recorded_by_user_id = excluded.recorded_by_user_id,
              created_at = excluded.created_at
            """,
            (ticket_id, rating, comment or None, int(g.user["id"]), created_at),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось сохранить отзыв. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    flash("Отзыв сохранен.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/edit", methods=("GET", "POST"))
@roles_required("admin", "operator")
def edit_ticket(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)

    specialists = _get_specialists()

    if request.method == "POST":
        new_status = request.form.get("status", "").strip()
        new_description = request.form.get("problem_description", "").strip()
        specialist_id_raw = request.form.get("assigned_specialist_id", "").strip()
        due_date = request.form.get("due_date", "").strip()

        if new_status not in STATUS_LABELS:
            flash("Выберите корректный статус.", "error")
            return render_template(
                "tickets/edit.html",
                ticket=ticket,
                specialists=specialists,
                status_options=status_options(),
                status_labels=STATUS_LABELS,
            )

        if not new_description:
            flash("Описание проблемы не может быть пустым.", "error")
            return render_template(
                "tickets/edit.html",
                ticket=ticket,
                specialists=specialists,
                status_options=status_options(),
                status_labels=STATUS_LABELS,
            )

        assigned_specialist_id: int | None = None
        if specialist_id_raw:
            try:
                assigned_specialist_id = int(specialist_id_raw)
            except ValueError:
                flash("Некорректный специалист.", "error")
                return render_template(
                    "tickets/edit.html",
                    ticket=ticket,
                    specialists=specialists,
                    status_options=status_options(),
                    status_labels=STATUS_LABELS,
                )

        changed_at = now_iso()
        new_due_at: str | None = ticket["due_at"]
        if due_date:
            parsed_due = parse_iso(due_date)
            if parsed_due is None:
                flash("Некорректная дата срока. Используйте формат YYYY-MM-DD.", "error")
                return render_template(
                    "tickets/edit.html",
                    ticket=ticket,
                    specialists=specialists,
                    status_options=status_options(),
                    status_labels=STATUS_LABELS,
                )
            new_due_at = parsed_due.strftime("%Y-%m-%d 23:59:59")

        completed_at: str | None = ticket["completed_at"]
        if new_status == "completed" and not completed_at:
            completed_at = changed_at
        if new_status != "completed":
            completed_at = None

        old_status = ticket["status"]
        old_specialist = ticket["assigned_specialist_id"]
        old_due_at = ticket["due_at"]

        try:
            db.execute(
                """
                UPDATE tickets
                SET status = ?,
                    problem_description = ?,
                    assigned_specialist_id = ?,
                    due_at = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (new_status, new_description, assigned_specialist_id, new_due_at, completed_at, changed_at, ticket_id),
            )

            if old_status != new_status:
                db.execute(
                    """
                    INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (ticket_id, old_status, new_status, int(g.user["id"]), changed_at, "Смена статуса"),
                )

            if old_specialist != assigned_specialist_id:
                db.execute(
                    """
                    INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ticket_id,
                        old_status,
                        new_status,
                        int(g.user["id"]),
                        changed_at,
                        "Изменение ответственного специалиста",
                    ),
                )

            if old_due_at != new_due_at and new_due_at:
                db.execute(
                    """
                    INSERT INTO ticket_due_history (ticket_id, old_due_at, new_due_at, changed_by_user_id, changed_at, customer_agreed, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ticket_id, old_due_at, new_due_at, int(g.user["id"]), changed_at, 0, "Изменение срока выполнения"),
                )

            db.commit()
        except Exception:
            db.rollback()
            flash("Не удалось сохранить изменения. Повторите попытку.", "error")
            return render_template(
                "tickets/edit.html",
                ticket=ticket,
                specialists=specialists,
                status_options=status_options(),
                status_labels=STATUS_LABELS,
            )

        request_number = ticket["request_number"]
        if old_status != new_status:
            _notify_status_change(db=db, ticket_id=ticket_id, request_number=request_number, new_status=new_status)

        if old_specialist != assigned_specialist_id and assigned_specialist_id is not None:
            create_notification(
                db=db,
                user_id=assigned_specialist_id,
                ticket_id=ticket_id,
                type_="assigned",
                message=f"Вам назначена заявка {request_number}.",
            )

        flash("Изменения сохранены.", "success")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    return render_template(
        "tickets/edit.html",
        ticket=ticket,
        specialists=specialists,
        status_options=status_options(),
        status_labels=STATUS_LABELS,
    )


def _notify_status_change(*, db, ticket_id: int, request_number: str, new_status: str) -> None:
    recipients = db.execute(
        "SELECT id FROM users WHERE role IN ('admin', 'operator') AND is_active = 1"
    ).fetchall()

    for recipient in recipients:
        create_notification(
            db=db,
            user_id=int(recipient["id"]),
            ticket_id=ticket_id,
            type_="status_changed",
            message=f"Статус заявки {request_number} изменен: {STATUS_LABELS[new_status]}.",
        )

    ticket = db.execute("SELECT assigned_specialist_id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is not None and ticket["assigned_specialist_id"] is not None:
        create_notification(
            db=db,
            user_id=int(ticket["assigned_specialist_id"]),
            ticket_id=ticket_id,
            type_="status_changed",
            message=f"Статус заявки {request_number} изменен: {STATUS_LABELS[new_status]}.",
        )


@bp.route("/<int:ticket_id>/status", methods=("POST",))
@login_required
def update_status(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)

    if not _ticket_access_allowed(ticket):
        abort(403)

    new_status = request.form.get("status", "").strip()
    if new_status not in STATUS_LABELS:
        flash("Выберите корректный статус.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if g.user["role"] == "specialist" and new_status == "open":
        flash("Специалист не может переводить заявку в статус 'Открыта'.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    old_status = ticket["status"]
    if old_status == new_status:
        flash("Статус не изменился.", "info")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    changed_at = now_iso()
    completed_at: str | None = ticket["completed_at"]
    if new_status == "completed" and not completed_at:
        completed_at = changed_at
    if new_status != "completed":
        completed_at = None

    try:
        db.execute(
            "UPDATE tickets SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
            (new_status, completed_at, changed_at, ticket_id),
        )
        db.execute(
            """
            INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, old_status, new_status, int(g.user["id"]), changed_at, "Смена статуса"),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось обновить статус. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    _notify_status_change(db=db, ticket_id=ticket_id, request_number=ticket["request_number"], new_status=new_status)
    flash("Статус обновлен.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/comment", methods=("POST",))
@login_required
def add_comment(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)
    if not _ticket_access_allowed(ticket):
        abort(403)

    body = request.form.get("body", "").strip()
    if not body:
        flash("Комментарий не может быть пустым.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    created_at = now_iso()
    try:
        db.execute(
            """
            INSERT INTO ticket_comments (ticket_id, user_id, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, int(g.user["id"]), body, created_at),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось добавить комментарий. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    flash("Комментарий добавлен.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/part", methods=("POST",))
@login_required
def add_part(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)
    if not _ticket_access_allowed(ticket):
        abort(403)

    part_name = request.form.get("part_name", "").strip()
    quantity_raw = request.form.get("quantity", "").strip()

    if not part_name:
        flash("Укажите наименование комплектующей.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    try:
        quantity = int(quantity_raw)
    except ValueError:
        flash("Количество должно быть числом.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    if quantity <= 0:
        flash("Количество должно быть больше нуля.", "warning")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    created_at = now_iso()
    try:
        db.execute(
            """
            INSERT INTO ticket_parts (ticket_id, part_name, quantity, created_by_user_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_id, part_name, quantity, int(g.user["id"]), created_at),
        )
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось добавить комплектующую. Повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    flash("Комплектующая добавлена.", "success")
    return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))


@bp.route("/<int:ticket_id>/delete", methods=("POST",))
@roles_required("admin")
def delete_ticket(ticket_id: int):
    db = get_db()
    ticket = db.execute("SELECT request_number FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        abort(404)

    try:
        db.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось удалить заявку. Проверьте связи и повторите попытку.", "error")
        return redirect(url_for("tickets.view_ticket", ticket_id=ticket_id))

    flash(f"Заявка {ticket['request_number']} удалена.", "info")
    return redirect(url_for("tickets.list_tickets"))
