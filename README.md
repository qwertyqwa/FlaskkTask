# FlaskkTask — учет заявок на ремонт климатического оборудования

Проект для учебной практики (3 задания). В репозитории **две независимые базы данных**:

⚠️ Схемы **разные** и намеренно не смешиваются: **Task2‑БД не подключена к Flask‑приложению** (это отдельное задание про проектирование и SQL‑отчеты).

Если у вас в `instance/` лежит файл вроде `task2.sqlite3` — это лишний артефакт. Для задания 2 используйте только `task2/task2.sqlite3`.

## 1) Запуск Web‑приложения (Задание 1 + 3)

### 1.1. Подготовка окружения

Рекомендуется виртуальное окружение.

**Windows (PowerShell):**
1) `py -3 -m venv .venv`
2) `.venv\\Scripts\\Activate.ps1`
3) `python -m pip install -r requirements.txt`
4) (опционально тесты) `python -m pip install -r requirements-dev.txt`

**macOS/Linux (bash):**
1) `python3 -m venv .venv`
2) `source .venv/bin/activate`
3) `python -m pip install -r requirements.txt`
4) (опционально тесты) `python -m pip install -r requirements-dev.txt`

Если `python3 -m venv` падает с ошибкой про `ensurepip`, на Debian/Ubuntu обычно нужно установить пакет `python3-venv`.

### 1.2. Инициализация БД приложения

Создать таблицы и пользователей по умолчанию:

`python -m flask --app main init-db`

Файл БД создается в `instance/app.sqlite3` (папка `instance/` в git не хранится).

### 1.3. Запуск

`python main.py`

Откройте `http://127.0.0.1:5000`.

### 1.4. Пользователи по умолчанию

- `admin / admin`
- `operator / operator`
- `specialist / specialist`
- `manager / manager`

### 1.5. Сброс БД приложения

Рекомендуемый способ (кроссплатформенно):

`python -m flask --app main reset-db`

### 1.6. Генерация тестовых данных (в БД приложения)

Команда генерирует тестовые данные напрямую в `instance/app.sqlite3` (пользователи/заявки/история/комментарии/комплектующие/запросы помощи/отзывы).

Сбросить БД и сгенерировать 500 заявок:

`python -m flask --app main seed-db --reset --tickets 500`

Пример (как в task2, но сразу в app‑БД):

```
Генерация тестовых данных для app (Flask)...
--------------------------------------------------
[OK] БД сброшена: .../instance/app.sqlite3
[OK] Пользователи: +15
[OK] Заявки: 500
...
[OK] Генерация завершена!
```

Альтернатива вручную:
1) удалить файл `instance/app.sqlite3`
2) выполнить `python -m flask --app main init-db`

## 2) Задание 2 (ER‑диаграмма, БД 3НФ, импорт, отчеты, backup)

Все команды работают с Task2‑БД `task2/task2.sqlite3` и **не влияют** на `instance/app.sqlite3`.

### 2.1. Создать пустую БД по схеме

`python tools/task2_manage.py init`

### 2.2. Импорт данных из CSV

Файлы импорта лежат в `task2/import/` (пример структуры — `task2/import/README.md`).

Импорт:

`python tools/task2_manage.py import`

Опционально можно сгенерировать примерные CSV:

`python tools/generate_test_data.py`

### 2.3. Сформировать отчеты (SQL → Markdown)

`python tools/task2_manage.py reports --date-from "2025-12-01 00:00:00" --date-to "2025-12-31 23:59:59"`

Результаты: `task2/reports/*.md`

### 2.4. Резервное копирование Task2‑БД

SQL‑дамп:

`python tools/task2_manage.py backup --format sql`

Копия файла SQLite:

`python tools/task2_manage.py backup --format sqlite`

### 2.5. Сброс Task2‑БД

Рекомендуемый способ (кроссплатформенно):

`python tools/task2_manage.py reset`

Полный пересоздать+импорт за один шаг:

`python tools/task2_manage.py recreate`

Альтернатива вручную:
1) удалить файл `task2/task2.sqlite3`
2) выполнить `python tools/task2_manage.py init` и `python tools/task2_manage.py import`

## 3) Тесты

`pytest -q`
