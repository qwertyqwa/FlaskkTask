from __future__ import annotations

from flask import Blueprint
from flask import abort
from flask import flash
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for

from app.db import get_db
from app.roles import roles_required
from app.security import hash_password
from app.utils import ROLE_LABELS

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=("GET",))
@roles_required("admin")
def users_list():
    db = get_db()
    users = db.execute(
        "SELECT id, username, full_name, role, is_active, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin/users_list.html", users=users, role_labels=ROLE_LABELS)


@bp.route("/users/new", methods=("GET", "POST"))
@roles_required("admin")
def users_new():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Логин обязателен.", "error")
            return render_template("admin/users_new.html", form=request.form, role_labels=ROLE_LABELS)
        if not full_name:
            flash("ФИО обязательно.", "error")
            return render_template("admin/users_new.html", form=request.form, role_labels=ROLE_LABELS)
        if role not in ROLE_LABELS:
            flash("Выберите корректную роль.", "error")
            return render_template("admin/users_new.html", form=request.form, role_labels=ROLE_LABELS)
        if not password or len(password) < 4:
            flash("Пароль должен быть не короче 4 символов.", "error")
            return render_template("admin/users_new.html", form=request.form, role_labels=ROLE_LABELS)

        db = get_db()
        try:
            db.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (?, ?, ?, ?)
                """,
                (username, hash_password(password), full_name, role),
            )
            db.commit()
        except Exception:
            db.rollback()
            flash("Не удалось создать пользователя. Возможно, логин уже занят.", "error")
            return render_template("admin/users_new.html", form=request.form, role_labels=ROLE_LABELS)

        flash("Пользователь создан.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/users_new.html", form={}, role_labels=ROLE_LABELS)


@bp.route("/users/<int:user_id>/edit", methods=("GET", "POST"))
@roles_required("admin")
def users_edit(user_id: int):
    db = get_db()
    user = db.execute(
        "SELECT id, username, full_name, role, is_active, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if user is None:
        abort(404)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "").strip()
        is_active = 1 if request.form.get("is_active") == "on" else 0
        password = request.form.get("password", "")

        if not full_name:
            flash("ФИО обязательно.", "error")
            return render_template("admin/users_edit.html", user=user, role_labels=ROLE_LABELS)
        if role not in ROLE_LABELS:
            flash("Выберите корректную роль.", "error")
            return render_template("admin/users_edit.html", user=user, role_labels=ROLE_LABELS)

        try:
            db.execute(
                "UPDATE users SET full_name = ?, role = ?, is_active = ? WHERE id = ?",
                (full_name, role, is_active, user_id),
            )
            if password:
                if len(password) < 4:
                    flash("Пароль должен быть не короче 4 символов.", "error")
                    return render_template("admin/users_edit.html", user=user, role_labels=ROLE_LABELS)
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id))
            db.commit()
        except Exception:
            db.rollback()
            flash("Не удалось сохранить пользователя.", "error")
            return render_template("admin/users_edit.html", user=user, role_labels=ROLE_LABELS)

        flash("Пользователь обновлен.", "success")
        return redirect(url_for("admin.users_list"))

    return render_template("admin/users_edit.html", user=user, role_labels=ROLE_LABELS)


@bp.route("/users/<int:user_id>/delete", methods=("POST",))
@roles_required("admin")
def users_delete(user_id: int):
    if user_id == 1:
        flash("Нельзя удалить первого администратора.", "warning")
        return redirect(url_for("admin.users_list"))

    db = get_db()
    user = db.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    if user is None:
        abort(404)

    try:
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))
        db.commit()
    except Exception:
        db.rollback()
        flash("Не удалось удалить пользователя. Возможно, он используется в заявках.", "error")
        return redirect(url_for("admin.users_list"))

    flash(f"Пользователь {user['username']} удален.", "info")
    return redirect(url_for("admin.users_list"))

