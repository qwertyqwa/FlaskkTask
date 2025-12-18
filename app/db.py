from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import click
from flask import Flask
from flask import current_app
from flask import g

from app.seed_data import seed_app_db
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

@click.command("reset-db")
def reset_db_command() -> None:
    db_path = _reset_db_file()
    init_db()
    ensure_initial_users()
    click.echo(f"Database reset: {db_path}")

@click.command("seed-db")
@click.option("--tickets", type=int, default=500, show_default=True)
@click.option("--operators", type=int, default=5, show_default=True)
@click.option("--specialists", type=int, default=10, show_default=True)
@click.option("--days-back", type=int, default=30, show_default=True)
@click.option("--comments-max", type=int, default=3, show_default=True)
@click.option("--parts-max", type=int, default=2, show_default=True)
@click.option("--seed", type=int, default=42, show_default=True)
@click.option("--reset", is_flag=True, help="Reset application DB before seeding")
def seed_db_command(
    tickets: int,
    operators: int,
    specialists: int,
    days_back: int,
    comments_max: int,
    parts_max: int,
    seed: int,
    reset: bool,
) -> None:
    click.echo("Генерация тестовых данных для app (Flask)...")
    click.echo("--------------------------------------------------")

    if tickets <= 0:
        raise click.BadParameter("--tickets must be > 0")
    if operators < 0:
        raise click.BadParameter("--operators must be >= 0")
    if specialists < 0:
        raise click.BadParameter("--specialists must be >= 0")
    if days_back <= 0:
        raise click.BadParameter("--days-back must be > 0")
    if comments_max < 0:
        raise click.BadParameter("--comments-max must be >= 0")
    if parts_max < 0:
        raise click.BadParameter("--parts-max must be >= 0")

    if reset:
        db_path = _reset_db_file()
        init_db()
        ensure_initial_users()
        click.echo(f"[OK] БД сброшена: {db_path}")

    db = get_db()
    try:
        result = seed_app_db(
            db,
            seed=seed,
            tickets_count=tickets,
            operators_count=operators,
            specialists_count=specialists,
            days_back=days_back,
            comments_max=comments_max,
            parts_max=parts_max,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    click.echo(f"[OK] Пользователи: +{result.users_created}")
    click.echo(f"[OK] Заявки: {result.tickets_created}")
    click.echo(f"[OK] История статусов: {result.status_history_created}")
    click.echo(f"[OK] История сроков: {result.due_history_created}")
    click.echo(f"[OK] Привлеченные специалисты: {result.assistants_created}")
    click.echo(f"[OK] Запросы помощи: {result.help_requests_created}")
    click.echo(f"[OK] Отзывы: {result.reviews_created}")
    click.echo(f"[OK] Комментарии: {result.comments_created}")
    click.echo(f"[OK] Комплектующие: {result.parts_created}")
    click.echo("--------------------------------------------------")
    click.echo("[OK] Генерация завершена!")


def init_app(app: Flask) -> None:
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(seed_db_command)


def _reset_db_file() -> Path:
    db_path = Path(current_app.config["DATABASE"])
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()
    if db_path.exists():
        db_path.unlink()
    return db_path


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
