from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import sqlite3

STATUS_LABELS: dict[str, str] = {
    "open": "Открыта",
    "in_repair": "В процессе ремонта",
    "waiting_parts": "Ожидание комплектующих",
    "completed": "Завершена",
}

ROLE_LABELS: dict[str, str] = {
    "admin": "Администратор",
    "operator": "Оператор",
    "specialist": "Специалист",
    "manager": "Менеджер по качеству",
}

FEEDBACK_FORM_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLSdhZcExx6LSIXxk0ub55mSu-WIh23WYdGG9HY5EZhLDo7P8eA/viewform?usp=sf_link"
)

PHONE_ALLOWED = re.compile(r"^[0-9+()\-\s]{6,20}$")


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def format_datetime(value: str | None) -> str:
    parsed = parse_iso(value)
    if parsed is None:
        return ""
    return parsed.strftime("%d.%m.%Y %H:%M")


def format_duration_seconds(seconds: int | float | None) -> str:
    if seconds is None:
        return "0"
    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts: list[str] = []
    if days:
        parts.append(f"{days} дн.")
    if hours:
        parts.append(f"{hours} ч.")
    if minutes:
        parts.append(f"{minutes} мин.")
    if not parts:
        parts.append(f"{sec} сек.")
    return " ".join(parts)


def validate_phone(phone: str) -> tuple[bool, str]:
    cleaned = phone.strip()
    if not cleaned:
        return False, "Номер телефона обязателен."
    if not PHONE_ALLOWED.match(cleaned):
        return False, "Номер телефона содержит недопустимые символы."
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if len(digits) < 10:
        return False, "Номер телефона слишком короткий (нужно минимум 10 цифр)."
    return True, cleaned


@dataclass(frozen=True)
class SelectOption:
    value: str
    label: str


def status_options() -> list[SelectOption]:
    return [SelectOption(value=key, label=label) for key, label in STATUS_LABELS.items()]


def generate_request_number(db: sqlite3.Connection, created_at_iso: str) -> str:
    created = parse_iso(created_at_iso)
    if created is None:
        created = datetime.now()
    day_prefix = created.strftime("%Y%m%d")

    row = db.execute(
        "SELECT COUNT(*) AS cnt FROM tickets WHERE request_number LIKE ?",
        (f"R-{day_prefix}-%",),
    ).fetchone()
    seq = int(row["cnt"]) + 1 if row is not None else 1
    return f"R-{day_prefix}-{seq:04d}"


def normalize_search_tokens(value: str) -> Iterable[str]:
    return [token for token in re.split(r"\s+", value.strip()) if token]
