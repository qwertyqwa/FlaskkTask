from __future__ import annotations

from dataclasses import dataclass

from app.utils import parse_iso


@dataclass(frozen=True)
class StatisticsResult:
    completed_count: int
    average_seconds: float
    fault_type_counts: dict[str, int]


def categorize_fault_type(problem_description: str) -> str:
    text = (problem_description or "").lower()

    keywords: dict[str, tuple[str, ...]] = {
        "Не включается": ("не включ", "не запуска", "нет питания", "не горит"),
        "Шум/вибрация": ("шум", "гуд", "вибрац", "стук"),
        "Не охлаждает": ("не охлажд", "плохо охлажд", "теплый воздух"),
        "Не греет": ("не греет", "плохо греет"),
        "Протечка": ("теч", "капает", "конденсат", "вода"),
        "Запах": ("запах", "воняет"),
        "Ошибка/код": ("ошибк", "код", "error", "err"),
    }

    for label, parts in keywords.items():
        for part in parts:
            if part in text:
                return label

    return "Другое"


def calculate_statistics(rows: list[dict]) -> StatisticsResult:
    completed = 0
    sum_seconds = 0.0
    fault_counts: dict[str, int] = {}

    for row in rows:
        created_at = parse_iso(row.get("created_at"))
        completed_at = parse_iso(row.get("completed_at"))
        if created_at is None or completed_at is None:
            continue

        duration = (completed_at - created_at).total_seconds()
        if duration < 0:
            continue

        completed += 1
        sum_seconds += duration

        fault_type = categorize_fault_type(str(row.get("problem_description", "")))
        fault_counts[fault_type] = fault_counts.get(fault_type, 0) + 1

    average = (sum_seconds / completed) if completed else 0.0
    return StatisticsResult(completed_count=completed, average_seconds=average, fault_type_counts=fault_counts)
