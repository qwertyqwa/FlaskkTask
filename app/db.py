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
    _migrate_schema(db)
    db.commit()


def ensure_initial_users() -> None:
    db = get_db()
    admin_password = current_app.config.get("INITIAL_ADMIN_PASSWORD", "admin")
    operator_password = current_app.config.get("INITIAL_OPERATOR_PASSWORD", "operator")
    specialist_password = current_app.config.get("INITIAL_SPECIALIST_PASSWORD", "specialist")
    manager_password = current_app.config.get("INITIAL_MANAGER_PASSWORD", "manager")

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
        {
            "username": "manager",
            "full_name": "Менеджер по качеству",
            "role": "manager",
            "password": manager_password,
        },
    ]

    for user in users:
        exists = db.execute("SELECT 1 FROM users WHERE username = ?", (user["username"],)).fetchone()
        if exists is not None:
            continue
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (user["username"], hash_password(user["password"]), user["full_name"], user["role"]),
        )

    db.commit()


@click.command("init-db")
def init_db_command() -> None:
    init_db()
    ensure_initial_users()
    click.echo("Database initialized. Users ensured: admin/operator/specialist/manager.")


def init_app(app: Flask) -> None:
    app.cli.add_command(init_db_command)


def _column_exists(db: sqlite3.Connection, table: str, column: str) -> bool:
    rows = db.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _table_create_sql(db: sqlite3.Connection, table: str) -> str | None:
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    ).fetchone()
    if row is None:
        return None
    return str(row["sql"] or "")


def _rebuild_users_table_with_manager(db: sqlite3.Connection) -> None:
    db.execute("PRAGMA foreign_keys = OFF")
    db.execute(
        """
        CREATE TABLE users_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          full_name TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('admin', 'operator', 'specialist', 'manager')),
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    db.execute(
        """
        INSERT INTO users_new (id, username, password_hash, full_name, role, is_active, created_at)
        SELECT id, username, password_hash, full_name, role, is_active, created_at
        FROM users
        """
    )
    db.execute("DROP TABLE users")
    db.execute("ALTER TABLE users_new RENAME TO users")
    db.execute("PRAGMA foreign_keys = ON")


def _migrate_schema(db: sqlite3.Connection) -> None:
    users_sql = _table_create_sql(db, "users")
    if users_sql and "manager" not in users_sql:
        _rebuild_users_table_with_manager(db)

    if _table_create_sql(db, "tickets") and not _column_exists(db, "tickets", "due_at"):
        db.execute("ALTER TABLE tickets ADD COLUMN due_at TEXT")
