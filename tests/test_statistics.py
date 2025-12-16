from app.services.statistics import calculate_statistics


def test_calculate_statistics_counts_average_and_fault_types():
    rows = [
        {
            "created_at": "2025-12-16 10:00:00",
            "completed_at": "2025-12-16 11:00:00",
            "problem_description": "Не включается после включения в розетку",
        },
        {
            "created_at": "2025-12-16 12:00:00",
            "completed_at": "2025-12-16 12:30:00",
            "problem_description": "Сильный шум и вибрация",
        },
        {
            "created_at": "2025-12-16 13:00:00",
            "completed_at": None,
            "problem_description": "Не охлаждает",
        },
    ]

    result = calculate_statistics(rows)

    assert result.completed_count == 2
    assert result.average_seconds == 2700.0
    assert result.fault_type_counts["Не включается"] == 1
    assert result.fault_type_counts["Шум/вибрация"] == 1

