from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from app.security import hash_password
from app.utils import generate_request_number


FIRST_NAMES = [
    "Иван",
    "Петр",
    "Сергей",
    "Александр",
    "Дмитрий",
    "Андрей",
    "Михаил",
    "Николай",
    "Владимир",
    "Алексей",
    "Анна",
    "Мария",
    "Елена",
    "Ольга",
    "Татьяна",
    "Наталья",
    "Ирина",
    "Светлана",
    "Екатерина",
    "Юлия",
]

LAST_NAMES = [
    "Иванов",
    "Петров",
    "Сидоров",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Соколов",
    "Лебедев",
    "Козлов",
    "Новиков",
    "Морозов",
]

MIDDLE_NAMES = [
    "Иванович",
    "Петрович",
    "Сергеевич",
    "Александрович",
    "Дмитриевич",
    "Андреевич",
    "Михайлович",
    "Николаевич",
    "Владимирович",
    "Алексеевич",
    "Ивановна",
    "Петровна",
    "Сергеевна",
    "Александровна",
    "Дмитриевна",
    "Андреевна",
    "Михайловна",
    "Николаевна",
    "Владимировна",
    "Алексеевна",
]

EQUIPMENT_TYPES = [
    "Кондиционер",
    "Вентиляция",
    "Обогреватель",
    "Увлажнитель",
    "Осушитель",
    "Тепловой насос",
]

DEVICE_MODELS = [
    "LG S12EQ",
    "Daikin FTXB",
    "Mitsubishi MSZ‑HR",
    "Panasonic CS‑TZ",
    "Samsung AR12",
    "Toshiba RAS‑10",
    "Gree GWH09",
    "Haier HSU‑09",
]

PROBLEM_DESCRIPTIONS = [
    "Не включается после включения в сеть",
    "Плохо охлаждает",
    "Плохо греет",
    "Шумит при работе",
    "Вибрация при включении",
    "Течет вода",
    "Не работает пульт управления",
    "Выбивает автомат при включении",
    "Запах гари",
    "Не переключается режим",
]

COMMENTS = [
    "Провел диагностику. Требуется замена детали.",
    "Очистка фильтров выполнена.",
    "Требуется заказ комплектующих.",
    "Ожидаем поставку запчастей.",
    "Ремонт завершен, требуется проверка клиентом.",
    "Выполнена профилактическая чистка.",
]

PARTS = [
    "Датчик температуры",
    "Плата управления",
    "Компрессор",
    "Вентилятор",
    "Фильтр",
    "Датчик давления",
    "Термостат",
    "Конденсатор",
    "Пульт управления",
]

HELP_MESSAGES = [
    "Нужна консультация по диагностике неисправности.",
    "Не получается выполнить ремонт: требуется помощь коллег.",
    "Требуется согласование продления срока из‑за отсутствия комплектующих.",
    "Нужна помощь при координации работ с другим специалистом.",
]

REVIEW_COMMENTS = [
    "Все быстро и качественно.",
    "Работа выполнена хорошо.",
    "Нужно было дольше ждать, но объяснили причину.",
    "Качеством доволен.",
]


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def _random_full_name(rng: random.Random) -> str:
    return f"{rng.choice(LAST_NAMES)} {rng.choice(FIRST_NAMES)} {rng.choice(MIDDLE_NAMES)}"


def _random_phone(rng: random.Random) -> str:
    area = rng.choice(["999", "916", "903", "905", "925", "926", "929"])
    part1 = rng.randint(100, 999)
    part2 = rng.randint(10, 99)
    part3 = rng.randint(10, 99)
    return f"+7 ({area}) {part1}-{part2}-{part3}"


def _get_user_id(db: sqlite3.Connection, username: str) -> int | None:
    row = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        return None
    return int(row["id"])


def _create_users(
    db: sqlite3.Connection,
    *,
    rng: random.Random,
    role: str,
    prefix: str,
    count: int,
    password: str,
    name_prefix: str,
) -> int:
    created = 0
    for idx in range(1, count + 1):
        username = f"{prefix}{idx}"
        full_name = f"{name_prefix} {idx}"
        try:
            db.execute(
                """
                INSERT OR IGNORE INTO users (username, password_hash, full_name, role, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (username, hash_password(password), full_name, role),
            )
            created += 1
        except Exception:
            continue
    return created


def _fetch_user_ids_by_role(db: sqlite3.Connection, role: str) -> list[int]:
    rows = db.execute("SELECT id FROM users WHERE role = ? AND is_active = 1", (role,)).fetchall()
    return [int(r["id"]) for r in rows]


@dataclass(frozen=True)
class SeedResult:
    users_created: int
    tickets_created: int
    comments_created: int
    parts_created: int
    assistants_created: int
    help_requests_created: int
    reviews_created: int
    due_history_created: int
    status_history_created: int


def seed_app_db(
    db: sqlite3.Connection,
    *,
    seed: int,
    tickets_count: int,
    operators_count: int,
    specialists_count: int,
    days_back: int,
    comments_max: int,
    parts_max: int,
) -> SeedResult:
    rng = random.Random(seed)

    users_created = 0
    users_created += _create_users(
        db,
        rng=rng,
        role="operator",
        prefix="operator",
        count=operators_count,
        password="operator",
        name_prefix="Оператор",
    )
    users_created += _create_users(
        db,
        rng=rng,
        role="specialist",
        prefix="specialist",
        count=specialists_count,
        password="specialist",
        name_prefix="Специалист",
    )

    operator_id = _get_user_id(db, "operator")
    manager_id = _get_user_id(db, "manager")

    if operator_id is None:
        operator_id = _fetch_user_ids_by_role(db, "operator")[0]
    if manager_id is None:
        manager_id = _fetch_user_ids_by_role(db, "manager")[0]

    specialist_ids = _fetch_user_ids_by_role(db, "specialist")

    start_dt = datetime.now() - timedelta(days=days_back)
    end_dt = datetime.now()

    tickets_created = 0
    comments_created = 0
    parts_created = 0
    assistants_created = 0
    help_requests_created = 0
    reviews_created = 0
    due_history_created = 0
    status_history_created = 0

    statuses = ["open", "in_repair", "waiting_parts", "completed"]
    weights = [0.25, 0.35, 0.25, 0.15]

    for _ in range(tickets_count):
        created_at_dt = start_dt + (end_dt - start_dt) * rng.random()
        created_at = _iso(created_at_dt)
        updated_at = created_at

        equipment_type = rng.choice(EQUIPMENT_TYPES)
        device_model = rng.choice(DEVICE_MODELS)
        problem_description = rng.choice(PROBLEM_DESCRIPTIONS)
        customer_full_name = _random_full_name(rng)
        customer_phone = _random_phone(rng)

        assigned_specialist_id: int | None = None
        if rng.random() < 0.8 and specialist_ids:
            assigned_specialist_id = rng.choice(specialist_ids)

        status = rng.choices(statuses, weights=weights, k=1)[0]

        due_at: str | None = None
        if rng.random() < 0.75:
            due_dt = created_at_dt + timedelta(days=rng.randint(1, 10))
            due_at = _iso(due_dt.replace(hour=23, minute=59, second=59))

        completed_at: str | None = None
        if status == "completed":
            completed_dt = created_at_dt + timedelta(hours=rng.randint(2, 72))
            completed_at = _iso(completed_dt)
            updated_at = completed_at

        request_number = generate_request_number(db, created_at)

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
                completed_at,
                updated_at,
            ),
        )
        ticket_id = int(cur.lastrowid)
        tickets_created += 1

        db.execute(
            """
            INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (ticket_id, None, "open", operator_id, created_at, "Создание заявки"),
        )
        status_history_created += 1

        if status != "open":
            change_dt = created_at_dt + timedelta(hours=rng.randint(1, 24))
            changed_at = _iso(change_dt)
            db.execute(
                """
                INSERT INTO status_history (ticket_id, old_status, new_status, changed_by_user_id, changed_at, comment)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ticket_id, "open", status, operator_id, changed_at, "Смена статуса"),
            )
            status_history_created += 1

        if due_at is not None:
            db.execute(
                """
                INSERT INTO ticket_due_history (ticket_id, old_due_at, new_due_at, changed_by_user_id, changed_at, customer_agreed, comment)
                VALUES (?, ?, ?, ?, ?, 0, ?)
                """,
                (ticket_id, None, due_at, operator_id, created_at, "Установка срока выполнения"),
            )
            due_history_created += 1

            if rng.random() < 0.2:
                old_due_at = due_at
                due_dt = datetime.fromisoformat(due_at) + timedelta(days=rng.randint(1, 5))
                due_at = _iso(due_dt.replace(hour=23, minute=59, second=59))
                change_dt = created_at_dt + timedelta(days=rng.randint(1, 3))
                changed_at = _iso(change_dt)
                db.execute("UPDATE tickets SET due_at = ?, updated_at = ? WHERE id = ?", (due_at, changed_at, ticket_id))
                db.execute(
                    """
                    INSERT INTO ticket_due_history (ticket_id, old_due_at, new_due_at, changed_by_user_id, changed_at, customer_agreed, comment)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """,
                    (ticket_id, old_due_at, due_at, manager_id, changed_at, "Продление срока выполнения"),
                )
                due_history_created += 1

        assistants_for_ticket: list[int] = []
        if rng.random() < 0.25 and len(specialist_ids) >= 2:
            pool = [sid for sid in specialist_ids if sid != assigned_specialist_id]
            rng.shuffle(pool)
            assistants_for_ticket = pool[: rng.randint(1, min(2, len(pool)))]
            for assistant_id in assistants_for_ticket:
                db.execute(
                    """
                    INSERT OR IGNORE INTO ticket_specialists (ticket_id, specialist_user_id, added_by_user_id, added_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (ticket_id, assistant_id, manager_id, created_at),
                )
                assistants_created += 1

        comment_count = rng.randint(0, comments_max)
        for _ in range(comment_count):
            author_id = operator_id
            if assigned_specialist_id is not None and rng.random() < 0.6:
                author_id = assigned_specialist_id
            if assistants_for_ticket and rng.random() < 0.15:
                author_id = rng.choice(assistants_for_ticket)

            comment_dt = created_at_dt + timedelta(hours=rng.randint(0, 72))
            db.execute(
                """
                INSERT INTO ticket_comments (ticket_id, user_id, body, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (ticket_id, author_id, rng.choice(COMMENTS), _iso(comment_dt)),
            )
            comments_created += 1

        part_count = rng.randint(0, parts_max)
        for _ in range(part_count):
            created_by = operator_id
            if assigned_specialist_id is not None:
                created_by = assigned_specialist_id
            part_dt = created_at_dt + timedelta(hours=rng.randint(1, 96))
            db.execute(
                """
                INSERT INTO ticket_parts (ticket_id, part_name, quantity, created_by_user_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticket_id, rng.choice(PARTS), rng.randint(1, 3), created_by, _iso(part_dt)),
            )
            parts_created += 1

        if assigned_specialist_id is not None and status in {"in_repair", "waiting_parts"} and rng.random() < 0.18:
            requested_dt = created_at_dt + timedelta(hours=rng.randint(2, 48))
            status_value = "open"
            resolved_by: int | None = None
            resolved_at: str | None = None
            resolution_comment: str | None = None

            if rng.random() < 0.55:
                status_value = "resolved"
                resolved_by = manager_id
                resolved_dt = requested_dt + timedelta(hours=rng.randint(1, 24))
                resolved_at = _iso(resolved_dt)
                resolution_comment = "Рекомендации переданы специалисту."

            db.execute(
                """
                INSERT INTO ticket_help_requests (
                  ticket_id,
                  requested_by_user_id,
                  requested_at,
                  message,
                  status,
                  resolved_by_user_id,
                  resolved_at,
                  resolution_comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    assigned_specialist_id,
                    _iso(requested_dt),
                    rng.choice(HELP_MESSAGES),
                    status_value,
                    resolved_by,
                    resolved_at,
                    resolution_comment,
                ),
            )
            help_requests_created += 1

        if status == "completed" and rng.random() < 0.55:
            rating = rng.randint(3, 5)
            comment = None
            if rng.random() < 0.5:
                comment = rng.choice(REVIEW_COMMENTS)
            review_dt = created_at_dt + timedelta(hours=rng.randint(10, 120))
            db.execute(
                """
                INSERT OR IGNORE INTO ticket_reviews (ticket_id, rating, comment, source, recorded_by_user_id, created_at)
                VALUES (?, ?, ?, 'manual', ?, ?)
                """,
                (ticket_id, rating, comment, manager_id, _iso(review_dt)),
            )
            reviews_created += 1

    return SeedResult(
        users_created=users_created,
        tickets_created=tickets_created,
        comments_created=comments_created,
        parts_created=parts_created,
        assistants_created=assistants_created,
        help_requests_created=help_requests_created,
        reviews_created=reviews_created,
        due_history_created=due_history_created,
        status_history_created=status_history_created,
    )

