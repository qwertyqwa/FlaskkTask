def _login(client, username: str, password: str) -> None:
    response = client.post("/login", data={"username": username, "password": password})
    assert response.status_code == 302


def test_full_ticket_workflow_creates_notifications(client, app):
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
    ticket_url = response.headers["Location"]
    assert ticket_url.startswith("/tickets/")

    specialist_client = app.test_client()
    _login(specialist_client, "specialist", "specialist")

    response = specialist_client.get(ticket_url)
    assert response.status_code == 200

    response = specialist_client.post(ticket_url + "/comment", data={"body": "Принял в работу"})
    assert response.status_code == 302

    response = specialist_client.post(ticket_url + "/part", data={"part_name": "Датчик температуры", "quantity": "1"})
    assert response.status_code == 302

    response = specialist_client.post(ticket_url + "/status", data={"status": "completed"})
    assert response.status_code == 302

    operator_client = app.test_client()
    _login(operator_client, "operator", "operator")
    response = operator_client.get("/notifications")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Статус заявки" in html
    assert "Завершена" in html

