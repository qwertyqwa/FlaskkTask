# FlaskkTask — учет заявок на ремонт климатического оборудования

Проект для учебной практики: веб‑модуль учета заявок на ремонт климатического оборудования.

## Запуск

1) Установить зависимости: `python3 -m pip install -r requirements.txt`
   (для тестов: `python3 -m pip install -r requirements-dev.txt`)
2) Инициализация БД и пользователей: `flask --app main init-db`
3) Запуск: `python3 main.py`

Откройте `http://127.0.0.1:5000`.

Пользователи по умолчанию:
- `admin / admin`
- `operator / operator`
- `specialist / specialist`

## Документы

- Задание 1 (спецификация + алгоритмы): `docs/task1.md`
- Задание 1 (отчет + протокол тестирования): `docs/report_task1.md`, `docs/test_protocol_task1.md`
