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
- Задание 2 (ERD + 3НФ + импорт/отчеты/backup): `docs/task2.md`, `docs/report_task2.md`

## Задание 2 (БД + отчеты)

- Инициализация БД: `python3 tools/task2_manage.py init`
- Импорт данных (CSV из `task2/import/`): `python3 tools/task2_manage.py import`
- Отчеты (Markdown в `task2/reports/`): `python3 tools/task2_manage.py reports --date-from "2025-12-01 00:00:00" --date-to "2025-12-31 23:59:59"`
- Backup: `python3 tools/task2_manage.py backup --format sql`

## Генерация отчета в DOCX (опционально, для задания 1)

Если нужен DOCX в формате, как в примере:
1) `cd tools`
2) `npm install`
3) `node generate_report_task1_docx.js`

## Генерация отчета в DOCX (задание 2)

1) `cd tools`
2) `npm install`
3) `node generate_report_task2_docx.js`

Файл появится в `docs/Отчет_Учебная_практика_Задание_2.docx`.
