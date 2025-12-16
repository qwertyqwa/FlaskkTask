from app.db import get_db


def _login(client, username: str, password: str) -> None:
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302


def _create_ticket_as_operator(client) -> str:
    _login(client, "operator", "operator")
    response = client.post(
        "/tickets/new",
        data={
            "equipment_type": "Кондиционер",
            "device_model": "LG S12EQ",
            "problem_description": "Не включается",
            "customer_full_name": "Иванов Иван",
            "customer_phone": "+7 (999) 123-45-67",
            "assigned_specialist_id": "3",
        },
    )
    assert response.status_code == 302
    return response.headers["Location"]


def test_help_request_visible_for_manager(client, app):
    ticket_url = _create_ticket_as_operator(client)

    specialist_client = app.test_client()
    _login(specialist_client, "specialist", "specialist")
    response = specialist_client.post(ticket_url + "/help", data={"message": "Нужна консультация по диагностике."})
    assert response.status_code == 302

    manager_client = app.test_client()
    _login(manager_client, "manager", "manager")
    response = manager_client.get("/manager/")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Открытые запросы помощи" in html
    assert "Нужна консультация" in html


def test_extend_due_date_requires_customer_agreement(client, app):
    ticket_url = _create_ticket_as_operator(client)
    ticket_id = int(ticket_url.rsplit("/", 1)[-1])

    manager_client = app.test_client()
    _login(manager_client, "manager", "manager")

    response = manager_client.post(f"/tickets/{ticket_id}/due", data={"due_date": "2025-12-20"}, follow_redirects=True)
    assert response.status_code == 200
    assert "Продление срока возможно только с согласованием заказчика" in response.data.decode("utf-8")

    response = manager_client.post(
        f"/tickets/{ticket_id}/due",
        data={"due_date": "2025-12-20", "customer_agreed": "on"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Срок выполнения обновлен" in response.data.decode("utf-8")

    with app.app_context():
        db = get_db()
        row = db.execute("SELECT due_at FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        assert row is not None
        assert row["due_at"] == "2025-12-20 23:59:59"


def test_qr_endpoint_returns_svg(client, app):
    ticket_url = _create_ticket_as_operator(client)
    ticket_id = int(ticket_url.rsplit("/", 1)[-1])

    operator_client = app.test_client()
    _login(operator_client, "operator", "operator")

    response = operator_client.get(f"/tickets/{ticket_id}/qr")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert response.data.lstrip().startswith(b"<svg")

