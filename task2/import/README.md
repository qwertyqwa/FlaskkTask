# Task2 import (CSV)

Файлы в этой папке — пример структуры данных для импорта в БД задания 2.

Импорт выполняется командой: `python3 tools/task2_manage.py import`

## Форматы файлов

- `roles.csv`: `code,name`
- `users.csv`: `username,password,full_name,role_code,is_active`
- `ticket_statuses.csv`: `code,name,is_final`
- `equipment_types.csv`: `name`
- `equipment_models.csv`: `equipment_type_name,name,manufacturer`
- `fault_types.csv`: `name`
- `customers.csv`: `full_name,phone`
- `parts.csv`: `name`
- `tickets.csv`: `request_number,created_at,customer_full_name,customer_phone,equipment_type_name,equipment_model_name,problem_description,fault_type_name,status_code,opened_by_username,assigned_specialist_username,completed_at`
- `ticket_comments.csv`: `request_number,username,created_at,body`
- `ticket_parts.csv`: `request_number,part_name,quantity,created_by_username,created_at`

