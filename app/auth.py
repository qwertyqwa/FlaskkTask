from __future__ import annotations

from functools import wraps
from typing import Any
from typing import Callable
from typing import TypeVar

from flask import Blueprint
from flask import Flask
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for

from app.db import get_db
from app.security import verify_password

bp = Blueprint("auth", __name__)

F = TypeVar("F", bound=Callable[..., Any])


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        g.unread_notifications = 0
        return

    db = get_db()
    user = db.execute(
        "SELECT id, username, full_name, role, is_active FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        session.clear()
        g.user = None
        g.unread_notifications = 0
        return

    if not bool(user["is_active"]):
        session.clear()
        g.user = None
        g.unread_notifications = 0
        flash("Пользователь заблокирован. Обратитесь к администратору.", "error")
        return

    g.user = user
    unread = db.execute(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = ? AND is_read = 0",
        (user["id"],),
    ).fetchone()
    g.unread_notifications = int(unread["cnt"]) if unread is not None else 0


def login_required(view: F) -> F:
    @wraps(view)
    def wrapped_view(**kwargs: Any):  # type: ignore[no-untyped-def]
        if g.user is None:
            flash("Для продолжения выполните вход.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view  # type: ignore[return-value]


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Введите логин и пароль.", "error")
            return render_template("login.html", username=username)

        db = get_db()
        user = db.execute(
            "SELECT id, username, password_hash, full_name, role, is_active FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None:
            flash("Неверный логин или пароль.", "error")
            return render_template("login.html", username=username)

        if not bool(user["is_active"]):
            flash("Пользователь заблокирован. Обратитесь к администратору.", "error")
            return render_template("login.html", username=username)

        if not verify_password(user["password_hash"], password):
            flash("Неверный логин или пароль.", "error")
            return render_template("login.html", username=username)

        session.clear()
        session["user_id"] = int(user["id"])
        flash(f"Здравствуйте, {user['full_name']}!", "success")
        return redirect(url_for("tickets.list_tickets"))

    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("auth.login"))


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_: Exception):  # type: ignore[no-untyped-def]
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_: Exception):  # type: ignore[no-untyped-def]
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(_: Exception):  # type: ignore[no-untyped-def]
        return render_template("errors/500.html"), 500

