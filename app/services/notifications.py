from __future__ import annotations

import sqlite3

from app.utils import now_iso


def create_notification(
    *,
    db: sqlite3.Connection,
    user_id: int,
    ticket_id: int | None,
    type_: str,
    message: str,
) -> None:
    db.execute(
        """
        INSERT INTO notifications (user_id, ticket_id, type, message, is_read, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
        """,
        (user_id, ticket_id, type_, message, now_iso()),
    )
    db.commit()

