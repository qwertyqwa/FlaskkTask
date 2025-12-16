from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORT_DIR = PROJECT_ROOT / "task2" / "import"

# Русские имена и фамилии для генерации
FIRST_NAMES = [
    "Иван", "Петр", "Сергей", "Александр", "Дмитрий", "Андрей", "Михаил",
    "Николай", "Владимир", "Алексей", "Анна", "Мария", "Елена", "Ольга",
    "Татьяна", "Наталья", "Ирина", "Светлана", "Екатерина", "Юлия"
]

LAST_NAMES = [
    "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Соколов",
    "Лебедев", "Козлов", "Новиков", "Морозов", "Петрова", "Смирнова", "Кузнецова",
    "Попова", "Соколова", "Лебедева", "Козлова", "Новикова", "Морозова"
]

MIDDLE_NAMES = [
    "Иванович", "Петрович", "Сергеевич", "Александрович", "Дмитриевич",
    "Андреевич", "Михайлович", "Николаевич", "Владимирович", "Алексеевич",
    "Ивановна", "Петровна", "Сергеевна", "Александровна", "Дмитриевна",
    "Андреевна", "Михайловна", "Николаевна", "Владимировна", "Алексеевна"
]

PROBLEM_DESCRIPTIONS = [
    "Не включается после включения в сеть",
    "Плохо охлаждает",
    "Плохо греет",
    "Издает странные звуки",
    "Течет вода",
    "Не работает пульт управления",
    "Не включается вообще",
    "Шумит при работе",
    "Вибрация при включении",
    "Не отображается температура",
    "Запах гари",
    "Искрит при включении",
    "Не переключается режим",
    "Не работает таймер",
    "Замерзает внутренний блок",
    "Не работает вентиляция",
    "Выбивает автомат при включении",
    "Не работает дистанционное управление",
    "Течет фреон",
    "Не работает обогрев"
]

COMMENTS = [
    "Провел диагностику. Требуется замена детали.",
    "Заправка фреоном выполнена. Проверка работы.",
    "Очистка фильтров выполнена.",
    "Заменен датчик температуры.",
    "Проверка электрики - все в норме.",
    "Требуется заказ комплектующих.",
    "Ожидаем поставку запчастей.",
    "Ремонт завершен, требуется проверка клиентом.",
    "Установлена новая плата управления.",
    "Выполнена профилактическая чистка.",
    "Заменен компрессор.",
    "Проверка герметичности системы.",
    "Настройка параметров работы.",
    "Калибровка датчиков выполнена.",
    "Тестирование всех режимов работы."
]


def generate_phone() -> str:
    """Генерирует случайный номер телефона"""
    area = random.choice(["999", "916", "903", "905", "925", "926", "929"])
    part1 = random.randint(100, 999)
    part2 = random.randint(10, 99)
    part3 = random.randint(10, 99)
    return f"+7 ({area}) {part1}-{part2}-{part3}"


def generate_full_name() -> str:
    """Генерирует случайное ФИО"""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    middle = random.choice(MIDDLE_NAMES)
    return f"{last} {first} {middle}"


def generate_date(start_date: datetime, end_date: datetime) -> str:
    """Генерирует случайную дату в формате строки"""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    random_hours = random.randint(0, 23)
    random_minutes = random.randint(0, 59)
    date = start_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
    return date.strftime("%Y-%m-%d %H:%M:%S")


def generate_request_number(date: datetime) -> str:
    """Генерирует номер заявки"""
    date_str = date.strftime("%Y%m%d")
    num = random.randint(1, 9999)
    return f"R-{date_str}-{num:04d}"


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    """Записывает CSV файл"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def generate_customers(count: int = 100) -> None:
    """Генерирует клиентов"""
    rows = []
    seen_phones = set()
    
    for _ in range(count):
        full_name = generate_full_name()
        phone = generate_phone()
        # Убеждаемся, что телефон уникален
        while phone in seen_phones:
            phone = generate_phone()
        seen_phones.add(phone)
        rows.append([full_name, phone])
    
    write_csv(IMPORT_DIR / "customers.csv", ["full_name", "phone"], rows)
    print(f"[OK] Сгенерировано {count} клиентов")


def generate_users() -> None:
    """Генерирует пользователей (операторов и специалистов)"""
    rows = [
        ["admin", "admin", "Администратор", "admin", "1"],
        ["operator", "operator", "Оператор", "operator", "1"],
        ["specialist", "specialist", "Специалист", "specialist", "1"],
    ]
    
    # Добавляем операторов
    for i in range(1, 6):
        rows.append([
            f"operator{i}",
            "operator",
            f"Оператор {i}",
            "operator",
            "1"
        ])
    
    # Добавляем специалистов
    for i in range(1, 11):
        rows.append([
            f"specialist{i}",
            "specialist",
            f"Специалист {i}",
            "specialist",
            "1"
        ])
    
    write_csv(IMPORT_DIR / "users.csv", ["username", "password", "full_name", "role_code", "is_active"], rows)
    print(f"[OK] Сгенерировано {len(rows)} пользователей")


def generate_equipment_types() -> None:
    """Расширяет типы оборудования"""
    rows = [
        ["Кондиционер"],
        ["Вентиляция"],
        ["Обогреватель"],
        ["Увлажнитель"],
        ["Осушитель"],
        ["Тепловой насос"],
        ["Чиллер"],
        ["Фанкойл"],
    ]
    write_csv(IMPORT_DIR / "equipment_types.csv", ["name"], rows)
    print(f"[OK] Сгенерировано {len(rows)} типов оборудования")


def generate_equipment_models() -> None:
    """Расширяет модели оборудования"""
    equipment_types = [
        ("Кондиционер", ["LG", "Daikin", "Mitsubishi", "Panasonic", "Samsung", "Toshiba", "Gree", "Haier"]),
        ("Вентиляция", ["VentPro", "Systemair", "Vents", "Maico", "Dantherm"]),
        ("Обогреватель", ["Ballu", "Timberk", "Electrolux", "Polaris", "Scarlett"]),
        ("Увлажнитель", ["Boneco", "Venta", "Stadler", "Philips", "Xiaomi"]),
        ("Осушитель", ["Master", "Trotec", "Ballu", "Timberk"]),
        ("Тепловой насос", ["Mitsubishi", "Daikin", "LG", "Panasonic"]),
        ("Чиллер", ["Carrier", "York", "Trane", "Daikin"]),
        ("Фанкойл", ["Carrier", "York", "Daikin", "Trane"]),
    ]
    
    rows = []
    model_names = {
        "Кондиционер": ["S12EQ", "FTXB", "MSZ", "CS", "AR", "FTX", "Gree", "Haier"],
        "Вентиляция": ["2000", "3000", "4000", "5000", "Pro"],
        "Обогреватель": ["BEC", "TCH", "EIH", "BHH", "BHP"],
        "Увлажнитель": ["W200", "LW25", "Oskar", "HU", "CJXJSQ"],
        "Осушитель": ["DH", "BD", "TRO", "BAL"],
        "Тепловой насос": ["Zubadan", "Altherma", "Multi", "VRF"],
        "Чиллер": ["30XA", "YCIV", "RTAD", "VRV"],
        "Фанкойл": ["42MV", "40RM", "FD", "FCQ"],
    }
    
    for eq_type, manufacturers in equipment_types:
        models = model_names.get(eq_type, ["Model1", "Model2", "Model3"])
        for manufacturer in manufacturers[:3]:  # Берем первые 3 производителя
            for model in models[:2]:  # Берем первые 2 модели
                rows.append([eq_type, f"{manufacturer} {model}", manufacturer])
    
    write_csv(IMPORT_DIR / "equipment_models.csv", ["equipment_type_name", "name", "manufacturer"], rows)
    print(f"[OK] Сгенерировано {len(rows)} моделей оборудования")


def generate_fault_types() -> None:
    """Расширяет типы неисправностей"""
    rows = [
        ["Не включается"],
        ["Не охлаждает"],
        ["Не греет"],
        ["Шум/вибрация"],
        ["Протечка"],
        ["Не работает пульт"],
        ["Не работает дисплей"],
        ["Запах гари"],
        ["Искрит"],
        ["Выбивает автомат"],
        ["Течет фреон"],
        ["Не работает вентиляция"],
        ["Замерзает блок"],
        ["Другое"],
    ]
    write_csv(IMPORT_DIR / "fault_types.csv", ["name"], rows)
    print(f"[OK] Сгенерировано {len(rows)} типов неисправностей")


def generate_parts() -> None:
    """Расширяет запчасти"""
    rows = [
        ["Датчик температуры"],
        ["Плата управления"],
        ["Фреон R410A"],
        ["Фреон R22"],
        ["Компрессор"],
        ["Вентилятор"],
        ["Фильтр"],
        ["Датчик давления"],
        ["Термостат"],
        ["Конденсатор"],
        ["Испаритель"],
        ["Капиллярная трубка"],
        ["Реле пусковое"],
        ["Датчик влажности"],
        ["Дисплей"],
        ["Пульт управления"],
    ]
    write_csv(IMPORT_DIR / "parts.csv", ["name"], rows)
    print(f"[OK] Сгенерировано {len(rows)} запчастей")


def generate_tickets(count: int = 500) -> None:
    """Генерирует заявки"""
    # Читаем существующие данные для связей
    customers = []
    with (IMPORT_DIR / "customers.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        customers = list(reader)
    
    equipment_models = []
    with (IMPORT_DIR / "equipment_models.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        equipment_models = list(reader)
    
    fault_types = []
    with (IMPORT_DIR / "fault_types.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fault_types = list(reader)
    
    statuses = [
        ("open", "Открыта"),
        ("in_repair", "В процессе ремонта"),
        ("waiting_parts", "Ожидание комплектующих"),
        ("completed", "Завершена"),
    ]
    
    operators = ["operator"] + [f"operator{i}" for i in range(1, 6)]
    specialists = ["specialist"] + [f"specialist{i}" for i in range(1, 11)]
    
    start_date = datetime.now() - timedelta(days=180)  # 6 месяцев назад
    end_date = datetime.now()
    
    rows = []
    request_numbers = set()
    
    for _ in range(count):
        created_at = generate_date(start_date, end_date)
        created_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        request_number = generate_request_number(created_dt)
        
        # Убеждаемся, что номер уникален
        while request_number in request_numbers:
            request_number = generate_request_number(created_dt)
        request_numbers.add(request_number)
        
        customer = random.choice(customers)
        equipment = random.choice(equipment_models)
        problem = random.choice(PROBLEM_DESCRIPTIONS)
        fault_type = random.choice(fault_types) if random.random() > 0.1 else None  # 90% имеют тип неисправности
        status_code, status_name = random.choice(statuses)
        operator = random.choice(operators)
        specialist = random.choice(specialists) if random.random() > 0.2 else ""  # 80% имеют специалиста
        
        # Если статус завершен, добавляем дату завершения
        completed_at = ""
        if status_code == "completed":
            completed_dt = created_dt + timedelta(
                days=random.randint(1, 30),
                hours=random.randint(1, 8)
            )
            completed_at = completed_dt.strftime("%Y-%m-%d %H:%M:%S")
        
        rows.append([
            request_number,
            created_at,
            customer["full_name"],
            customer["phone"],
            equipment["equipment_type_name"],
            equipment["name"],
            problem,
            fault_type["name"] if fault_type else "",
            status_code,
            operator,
            specialist,
            completed_at
        ])
    
    write_csv(
        IMPORT_DIR / "tickets.csv",
        ["request_number", "created_at", "customer_full_name", "customer_phone",
         "equipment_type_name", "equipment_model_name", "problem_description",
         "fault_type_name", "status_code", "opened_by_username",
         "assigned_specialist_username", "completed_at"],
        rows
    )
    print(f"[OK] Сгенерировано {count} заявок")


def generate_ticket_comments() -> None:
    """Генерирует комментарии к заявкам"""
    # Читаем заявки
    tickets = []
    with (IMPORT_DIR / "tickets.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tickets = list(reader)
    
    specialists = ["specialist"] + [f"specialist{i}" for i in range(1, 11)]
    operators = ["operator"] + [f"operator{i}" for i in range(1, 6)]
    
    rows = []
    
    for ticket in tickets:
        # От 1 до 5 комментариев на заявку
        comment_count = random.randint(1, 5)
        created_dt = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M:%S")
        
        for i in range(comment_count):
            # Комментарии распределены по времени
            comment_dt = created_dt + timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 8)
            )
            comment_at = comment_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Специалисты пишут больше комментариев
            username = random.choice(specialists) if random.random() > 0.3 else random.choice(operators)
            comment = random.choice(COMMENTS)
            
            rows.append([
                ticket["request_number"],
                username,
                comment_at,
                comment
            ])
    
    write_csv(
        IMPORT_DIR / "ticket_comments.csv",
        ["request_number", "username", "created_at", "body"],
        rows
    )
    print(f"[OK] Сгенерировано {len(rows)} комментариев")


def generate_ticket_parts() -> None:
    """Генерирует запчасти для заявок"""
    # Читаем заявки и запчасти
    tickets = []
    with (IMPORT_DIR / "tickets.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tickets = list(reader)
    
    parts = []
    with (IMPORT_DIR / "parts.csv").open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        parts = list(reader)
    
    specialists = ["specialist"] + [f"specialist{i}" for i in range(1, 11)]
    
    rows = []
    
    for ticket in tickets:
        # Только для заявок в процессе или завершенных добавляем запчасти
        if ticket["status_code"] in ["in_repair", "waiting_parts", "completed"]:
            # От 0 до 3 запчастей на заявку
            parts_count = random.randint(0, 3)
            created_dt = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M:%S")
            
            used_parts = set()
            for _ in range(parts_count):
                part = random.choice(parts)
                part_name = part["name"]
                
                # Убеждаемся, что запчасть не повторяется для одной заявки
                if part_name in used_parts:
                    continue
                used_parts.add(part_name)
                
                part_dt = created_dt + timedelta(
                    days=random.randint(1, 20),
                    hours=random.randint(0, 8)
                )
                part_at = part_dt.strftime("%Y-%m-%d %H:%M:%S")
                quantity = random.randint(1, 5)
                username = random.choice(specialists)
                
                rows.append([
                    ticket["request_number"],
                    part_name,
                    str(quantity),
                    username,
                    part_at
                ])
    
    write_csv(
        IMPORT_DIR / "ticket_parts.csv",
        ["request_number", "part_name", "quantity", "created_by_username", "created_at"],
        rows
    )
    print(f"[OK] Сгенерировано {len(rows)} записей о запчастях")


def main() -> None:
    """Главная функция генерации данных"""
    print("Генерация тестовых данных для task2...")
    print("-" * 50)
    
    # Базовые данные (не меняем)
    roles = [["code", "name"], ["admin", "Администратор"], ["operator", "Оператор"], ["specialist", "Специалист"]]
    write_csv(IMPORT_DIR / "roles.csv", ["code", "name"], roles[1:])
    print("[OK] Роли сохранены")
    
    statuses = [
        ["code", "name", "is_final"],
        ["open", "Открыта", "0"],
        ["in_repair", "В процессе ремонта", "0"],
        ["waiting_parts", "Ожидание комплектующих", "0"],
        ["completed", "Завершена", "1"],
    ]
    write_csv(IMPORT_DIR / "ticket_statuses.csv", statuses[0], statuses[1:])
    print("[OK] Статусы сохранены")
    
    # Генерируем расширенные данные
    generate_customers(100)
    generate_users()
    generate_equipment_types()
    generate_equipment_models()
    generate_fault_types()
    generate_parts()
    generate_tickets(500)
    generate_ticket_comments()
    generate_ticket_parts()
    
    print("-" * 50)
    print("[OK] Генерация завершена!")
    print(f"\nДанные сохранены в: {IMPORT_DIR}")
    print("\nДля импорта данных выполните:")
    print("  python tools/task2_manage.py import")


if __name__ == "__main__":
    main()

