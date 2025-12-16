from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import click
from flask import Flask
from flask import current_app
from flask import g

from app.security import hash_password


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection

    return g.db


def close_db(_: Exception | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    db = get_db()
    schema_path = Path(current_app.root_path) / "schema.sql"
    db.executescript(schema_path.read_text(encoding="utf-8"))
    db.commit()


def ensure_initial_users() -> None:
    db = get_db()
    row = db.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
    if row is None:
        return

    if row["cnt"] > 0:
        return

    admin_password = current_app.config.get("INITIAL_ADMIN_PASSWORD", "admin")
    operator_password = current_app.config.get("INITIAL_OPERATOR_PASSWORD", "operator")
    specialist_password = current_app.config.get("INITIAL_SPECIALIST_PASSWORD", "specialist")

    users: list[dict[str, Any]] = [
        {
            "username": "admin",
            "full_name": "Администратор",
            "role": "admin",
            "password": admin_password,
        },
        {
            "username": "operator",
            "full_name": "Оператор",
            "role": "operator",
            "password": operator_password,
        },
        {
            "username": "specialist",
            "full_name": "Специалист",
            "role": "specialist",
            "password": specialist_password,
        },
    ]

    for user in users:
        db.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role)
            VALUES (?, ?, ?, ?)
            """,
            (user["username"], hash_password(user["password"]), user["full_name"], user["role"]),
        )

    db.commit()


@click.command("init-db")
def init_db_command() -> None:
    init_db()
    ensure_initial_users()
    click.echo("Database initialized. Users created: admin/operator/specialist.")


def init_app(app: Flask) -> None:
    app.cli.add_command(init_db_command)
