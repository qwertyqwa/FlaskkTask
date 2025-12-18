from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "task2" / "task2.sqlite3"
SCHEMA_PATH = PROJECT_ROOT / "task2" / "schema.sql"
IMPORT_DIR = PROJECT_ROOT / "task2" / "import"
QUERIES_DIR = PROJECT_ROOT / "task2" / "queries"
REPORTS_DIR = PROJECT_ROOT / "task2" / "reports"
BACKUPS_DIR = PROJECT_ROOT / "task2" / "backups"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: Path) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with connect(db_path) as db:
        db.executescript(schema_sql)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def build_map(db: sqlite3.Connection, table: str, key_col: str, value_col: str = "id") -> dict[str, int]:
    rows = db.execute(f"SELECT {value_col} AS id, {key_col} AS key FROM {table}").fetchall()
    return {str(row["key"]): int(row["id"]) for row in rows}


def import_data(db_path: Path, import_dir: Path) -> None:
    with connect(db_path) as db:
        try:
            _import_roles(db, import_dir)
            _import_users(db, import_dir)
            _import_ticket_statuses(db, import_dir)
            _import_equipment_types(db, import_dir)
            _import_equipment_models(db, import_dir)
            _import_fault_types(db, import_dir)
            _import_customers(db, import_dir)
            _import_parts(db, import_dir)
            _import_tickets(db, import_dir)
            _import_ticket_comments(db, import_dir)
            _import_ticket_parts(db, import_dir)
            db.commit()
        except Exception:
            db.rollback()
            raise


def _import_roles(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "roles.csv"):
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        if not code or not name:
            continue
        db.execute("INSERT OR IGNORE INTO roles (code, name) VALUES (?, ?)", (code, name))


def _import_users(db: sqlite3.Connection, import_dir: Path) -> None:
    roles = build_map(db, "roles", "code")
    for row in read_csv_rows(import_dir / "users.csv"):
        username = (row.get("username") or "").strip()
        password = row.get("password") or ""
        full_name = (row.get("full_name") or "").strip()
        role_code = (row.get("role_code") or "").strip()
        is_active = 1 if (row.get("is_active") or "1").strip() in {"1", "true", "True", "yes", "Да"} else 0

        if not username or not password or not full_name or role_code not in roles:
            continue

        db.execute(
            """
            INSERT OR IGNORE INTO users (username, password_hash, full_name, role_id, is_active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, generate_password_hash(password), full_name, roles[role_code], is_active),
        )


def _import_ticket_statuses(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "ticket_statuses.csv"):
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        is_final = 1 if (row.get("is_final") or "0").strip() in {"1", "true", "True", "yes", "Да"} else 0
        if not code or not name:
            continue
        db.execute(
            "INSERT OR IGNORE INTO ticket_statuses (code, name, is_final) VALUES (?, ?, ?)",
            (code, name, is_final),
        )


def _import_equipment_types(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "equipment_types.csv"):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        db.execute("INSERT OR IGNORE INTO equipment_types (name) VALUES (?)", (name,))


def _import_equipment_models(db: sqlite3.Connection, import_dir: Path) -> None:
    type_map = build_map(db, "equipment_types", "name")
    for row in read_csv_rows(import_dir / "equipment_models.csv"):
        type_name = (row.get("equipment_type_name") or "").strip()
        name = (row.get("name") or "").strip()
        manufacturer = (row.get("manufacturer") or "").strip() or None
        if not type_name or not name:
            continue
        if type_name not in type_map:
            db.execute("INSERT INTO equipment_types (name) VALUES (?)", (type_name,))
            type_map = build_map(db, "equipment_types", "name")
        db.execute(
            """
            INSERT OR IGNORE INTO equipment_models (equipment_type_id, name, manufacturer)
            VALUES (?, ?, ?)
            """,
            (type_map[type_name], name, manufacturer),
        )


def _import_fault_types(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "fault_types.csv"):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        db.execute("INSERT OR IGNORE INTO fault_types (name) VALUES (?)", (name,))


def _import_customers(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "customers.csv"):
        full_name = (row.get("full_name") or "").strip()
        phone = (row.get("phone") or "").strip()
        if not full_name or not phone:
            continue
        db.execute(
            "INSERT OR IGNORE INTO customers (full_name, phone) VALUES (?, ?)",
            (full_name, phone),
        )


def _import_parts(db: sqlite3.Connection, import_dir: Path) -> None:
    for row in read_csv_rows(import_dir / "parts.csv"):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        db.execute("INSERT OR IGNORE INTO parts (name) VALUES (?)", (name,))


def _import_tickets(db: sqlite3.Connection, import_dir: Path) -> None:
    status_map = build_map(db, "ticket_statuses", "code")
    user_map = build_map(db, "users", "username")
    fault_map = build_map(db, "fault_types", "name")
    customer_rows = db.execute("SELECT id, phone, full_name FROM customers").fetchall()
    customer_map = {(row["phone"], row["full_name"]): int(row["id"]) for row in customer_rows}

    model_rows = db.execute(
        """
        SELECT em.id, et.name AS type_name, em.name AS model_name
        FROM equipment_models em
        JOIN equipment_types et ON et.id = em.equipment_type_id
        """
    ).fetchall()
    model_map = {(row["type_name"], row["model_name"]): int(row["id"]) for row in model_rows}

    for row in read_csv_rows(import_dir / "tickets.csv"):
        request_number = (row.get("request_number") or "").strip()
        created_at = (row.get("created_at") or "").strip()
        customer_full_name = (row.get("customer_full_name") or "").strip()
        customer_phone = (row.get("customer_phone") or "").strip()
        equipment_type_name = (row.get("equipment_type_name") or "").strip()
        equipment_model_name = (row.get("equipment_model_name") or "").strip()
        problem_description = (row.get("problem_description") or "").strip()
        fault_type_name = (row.get("fault_type_name") or "").strip()
        status_code = (row.get("status_code") or "").strip()
        opened_by_username = (row.get("opened_by_username") or "").strip()
        assigned_specialist_username = (row.get("assigned_specialist_username") or "").strip()
        completed_at = (row.get("completed_at") or "").strip() or None

        if not request_number or not created_at:
            continue
        if not customer_full_name or not customer_phone:
            continue
        if not equipment_type_name or not equipment_model_name:
            continue
        if not problem_description or status_code not in status_map:
            continue
        if opened_by_username not in user_map:
            continue

        customer_key = (customer_phone, customer_full_name)
        if customer_key not in customer_map:
            db.execute(
                "INSERT INTO customers (full_name, phone, created_at) VALUES (?, ?, ?)",
                (customer_full_name, customer_phone, created_at),
            )
            new_id = db.execute("SELECT id FROM customers WHERE phone = ? AND full_name = ?", customer_key).fetchone()
            customer_map[customer_key] = int(new_id["id"])

        model_key = (equipment_type_name, equipment_model_name)
        if model_key not in model_map:
            db.execute("INSERT OR IGNORE INTO equipment_types (name) VALUES (?)", (equipment_type_name,))
            type_id = db.execute("SELECT id FROM equipment_types WHERE name = ?", (equipment_type_name,)).fetchone()
            if type_id is None:
                continue
            db.execute(
                "INSERT OR IGNORE INTO equipment_models (equipment_type_id, name) VALUES (?, ?)",
                (int(type_id["id"]), equipment_model_name),
            )
            model_id = db.execute(
                """
                SELECT em.id
                FROM equipment_models em
                JOIN equipment_types et ON et.id = em.equipment_type_id
                WHERE et.name = ? AND em.name = ?
                """,
                model_key,
            ).fetchone()
            if model_id is None:
                continue
            model_map[model_key] = int(model_id["id"])

        fault_type_id = fault_map.get(fault_type_name) if fault_type_name else None
        status_id = status_map[status_code]
        opened_by_id = user_map[opened_by_username]
        assigned_id = user_map.get(assigned_specialist_username) if assigned_specialist_username else None

        db.execute(
            """
            INSERT OR IGNORE INTO tickets (
              request_number,
              created_at,
              customer_id,
              equipment_model_id,
              problem_description,
              fault_type_id,
              status_id,
              opened_by_user_id,
              assigned_specialist_user_id,
              completed_at,
              updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_number,
                created_at,
                customer_map[customer_key],
                model_map[model_key],
                problem_description,
                fault_type_id,
                status_id,
                opened_by_id,
                assigned_id,
                completed_at,
                completed_at or created_at,
            ),
        )

        ticket_row = db.execute("SELECT id FROM tickets WHERE request_number = ?", (request_number,)).fetchone()
        if ticket_row is None:
            continue
        ticket_id = int(ticket_row["id"])

        db.execute(
            """
            INSERT INTO ticket_status_history (
              ticket_id,
              old_status_id,
              new_status_id,
              changed_by_user_id,
              changed_at,
              comment
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, None, status_id, opened_by_id, created_at, "Создание заявки"),
        )

        if completed_at and status_code == "completed":
            db.execute(
                """
                INSERT INTO ticket_status_history (
                  ticket_id,
                  old_status_id,
                  new_status_id,
                  changed_by_user_id,
                  changed_at,
                  comment
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ticket_id, None, status_id, opened_by_id, completed_at, "Завершение заявки"),
            )


def _import_ticket_comments(db: sqlite3.Connection, import_dir: Path) -> None:
    user_map = build_map(db, "users", "username")
    ticket_rows = db.execute("SELECT id, request_number FROM tickets").fetchall()
    ticket_map = {row["request_number"]: int(row["id"]) for row in ticket_rows}

    for row in read_csv_rows(import_dir / "ticket_comments.csv"):
        request_number = (row.get("request_number") or "").strip()
        username = (row.get("username") or "").strip()
        created_at = (row.get("created_at") or "").strip()
        body = (row.get("body") or "").strip()

        if request_number not in ticket_map or username not in user_map:
            continue
        if not created_at or not body:
            continue

        db.execute(
            """
            INSERT INTO ticket_comments (ticket_id, user_id, body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_map[request_number], user_map[username], body, created_at),
        )


def _import_ticket_parts(db: sqlite3.Connection, import_dir: Path) -> None:
    user_map = build_map(db, "users", "username")
    part_map = build_map(db, "parts", "name")
    ticket_rows = db.execute("SELECT id, request_number FROM tickets").fetchall()
    ticket_map = {row["request_number"]: int(row["id"]) for row in ticket_rows}

    for row in read_csv_rows(import_dir / "ticket_parts.csv"):
        request_number = (row.get("request_number") or "").strip()
        part_name = (row.get("part_name") or "").strip()
        quantity_raw = (row.get("quantity") or "").strip()
        created_by_username = (row.get("created_by_username") or "").strip()
        created_at = (row.get("created_at") or "").strip()

        if request_number not in ticket_map:
            continue
        if not part_name or created_by_username not in user_map:
            continue
        if not created_at:
            continue
        try:
            quantity = int(quantity_raw)
        except ValueError:
            continue
        if quantity <= 0:
            continue

        if part_name not in part_map:
            db.execute("INSERT OR IGNORE INTO parts (name) VALUES (?)", (part_name,))
            part_map = build_map(db, "parts", "name")

        db.execute(
            """
            INSERT OR IGNORE INTO ticket_parts (
              ticket_id,
              part_id,
              quantity,
              created_by_user_id,
              created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_map[request_number], part_map[part_name], quantity, user_map[created_by_username], created_at),
        )


def write_reports(db_path: Path, date_from: str, date_to: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    params = {"date_from": date_from, "date_to": date_to}

    query_files = sorted(QUERIES_DIR.glob("*.sql"))
    with connect(db_path) as db:
        for query_file in query_files:
            sql = query_file.read_text(encoding="utf-8")
            rows = db.execute(sql, params).fetchall()
            report_path = output_dir / f"{query_file.stem}.md"
            report_path.write_text(_rows_to_markdown(rows), encoding="utf-8")


def _rows_to_markdown(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "Нет данных.\n"
    headers = list(rows[0].keys())
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = [str(row[h]) if row[h] is not None else "" for h in headers]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def backup_db(db_path: Path, backups_dir: Path, format_: str) -> Path:
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format_ == "sqlite":
        backup_path = backups_dir / f"task2_backup_{stamp}.sqlite3"
        with connect(db_path) as source, sqlite3.connect(backup_path) as dest:
            source.backup(dest)
        return backup_path

    if format_ == "sql":
        backup_path = backups_dir / f"task2_backup_{stamp}.sql"
        with connect(db_path) as db, backup_path.open("w", encoding="utf-8") as handle:
            for line in db.iterdump():
                handle.write(line)
                handle.write("\n")
        return backup_path

    raise ValueError("format must be 'sqlite' or 'sql'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Task2: ERD/DB/import/reports/backup")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to task2 sqlite database")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Create empty DB using task2/schema.sql")
    sub.add_parser("reset", help="Delete DB file and create empty DB using task2/schema.sql")

    p_import = sub.add_parser("import", help="Import CSV data from task2/import/")
    p_import.add_argument("--path", default=str(IMPORT_DIR), help="Path to import directory")

    p_recreate = sub.add_parser("recreate", help="Reset DB and import CSV data")
    p_recreate.add_argument("--path", default=str(IMPORT_DIR), help="Path to import directory")

    p_reports = sub.add_parser("reports", help="Run SQL queries and write Markdown reports")
    p_reports.add_argument("--date-from", default="1900-01-01 00:00:00", help="Period start (ISO)")
    p_reports.add_argument("--date-to", default="2999-12-31 23:59:59", help="Period end (ISO)")
    p_reports.add_argument("--out", default=str(REPORTS_DIR), help="Output directory for reports")

    p_backup = sub.add_parser("backup", help="Create DB backup")
    p_backup.add_argument("--format", choices=("sqlite", "sql"), default="sql", help="Backup format")
    p_backup.add_argument("--out", default=str(BACKUPS_DIR), help="Output directory for backups")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)

    if args.cmd == "init":
        init_db(db_path)
        print(f"OK: DB initialized: {db_path}")
        return

    if args.cmd == "reset":
        if db_path.exists():
            db_path.unlink()
        init_db(db_path)
        print(f"OK: DB reset: {db_path}")
        return

    if args.cmd == "import":
        import_path = Path(args.path)
        import_data(db_path, import_path)
        print(f"OK: Data imported from: {import_path}")
        return

    if args.cmd == "recreate":
        if db_path.exists():
            db_path.unlink()
        init_db(db_path)
        import_path = Path(args.path)
        import_data(db_path, import_path)
        print(f"OK: DB recreated and imported from: {import_path}")
        return

    if args.cmd == "reports":
        write_reports(db_path, args.date_from, args.date_to, Path(args.out))
        print(f"OK: Reports written to: {args.out}")
        return

    if args.cmd == "backup":
        backup_path = backup_db(db_path, Path(args.out), args.format)
        print(f"OK: Backup created: {backup_path}")
        return

    raise RuntimeError("Unknown command")


if __name__ == "__main__":
    main()

