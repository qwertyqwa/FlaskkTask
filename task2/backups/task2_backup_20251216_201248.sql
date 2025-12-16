BEGIN TRANSACTION;
CREATE TABLE customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (phone, full_name)
);
INSERT INTO "customers" VALUES(1,'Иванов Иван Иванович','+7 (999) 123-45-67','2025-12-16 13:12:34');
INSERT INTO "customers" VALUES(2,'Петров Петр Петрович','+7 (999) 111-22-33','2025-12-16 13:12:34');
CREATE TABLE equipment_models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  manufacturer TEXT,
  UNIQUE (equipment_type_id, name),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT
);
INSERT INTO "equipment_models" VALUES(1,1,'LG S12EQ','LG');
INSERT INTO "equipment_models" VALUES(2,1,'Daikin FTXB','Daikin');
INSERT INTO "equipment_models" VALUES(3,2,'VentPro 2000','VentPro');
CREATE TABLE equipment_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);
INSERT INTO "equipment_types" VALUES(1,'Кондиционер');
INSERT INTO "equipment_types" VALUES(2,'Вентиляция');
CREATE TABLE fault_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);
INSERT INTO "fault_types" VALUES(1,'Не включается');
INSERT INTO "fault_types" VALUES(2,'Не охлаждает');
INSERT INTO "fault_types" VALUES(3,'Шум/вибрация');
INSERT INTO "fault_types" VALUES(4,'Протечка');
INSERT INTO "fault_types" VALUES(5,'Другое');
CREATE TABLE parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);
INSERT INTO "parts" VALUES(1,'Датчик температуры');
INSERT INTO "parts" VALUES(2,'Плата управления');
INSERT INTO "parts" VALUES(3,'Фреон R410A');
CREATE TABLE roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE
);
INSERT INTO "roles" VALUES(1,'admin','Администратор');
INSERT INTO "roles" VALUES(2,'operator','Оператор');
INSERT INTO "roles" VALUES(3,'specialist','Специалист');
CREATE TABLE ticket_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);
INSERT INTO "ticket_comments" VALUES(1,1,3,'Провел диагностику. Требуется датчик.','2025-12-10 11:00:00');
INSERT INTO "ticket_comments" VALUES(2,2,3,'Заправка фреоном выполнена. Проверка работы.','2025-12-11 11:00:00');
CREATE TABLE ticket_parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  part_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL CHECK(quantity > 0),
  created_by_user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (ticket_id, part_id),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE RESTRICT,
  FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);
INSERT INTO "ticket_parts" VALUES(1,1,1,1,3,'2025-12-10 11:10:00');
INSERT INTO "ticket_parts" VALUES(2,2,3,1,3,'2025-12-11 10:30:00');
CREATE TABLE ticket_status_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  old_status_id INTEGER,
  new_status_id INTEGER NOT NULL,
  changed_by_user_id INTEGER NOT NULL,
  changed_at TEXT NOT NULL DEFAULT (datetime('now')),
  comment TEXT,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (old_status_id) REFERENCES ticket_statuses(id) ON DELETE SET NULL,
  FOREIGN KEY (new_status_id) REFERENCES ticket_statuses(id) ON DELETE RESTRICT,
  FOREIGN KEY (changed_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
);
INSERT INTO "ticket_status_history" VALUES(1,1,NULL,1,2,'2025-12-10 10:00:00','Создание заявки');
INSERT INTO "ticket_status_history" VALUES(2,2,NULL,4,2,'2025-12-11 09:30:00','Создание заявки');
INSERT INTO "ticket_status_history" VALUES(3,2,NULL,4,2,'2025-12-11 12:00:00','Завершение заявки');
CREATE TABLE ticket_statuses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  is_final INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "ticket_statuses" VALUES(1,'open','Открыта',0);
INSERT INTO "ticket_statuses" VALUES(2,'in_repair','В процессе ремонта',0);
INSERT INTO "ticket_statuses" VALUES(3,'waiting_parts','Ожидание комплектующих',0);
INSERT INTO "ticket_statuses" VALUES(4,'completed','Завершена',1);
CREATE TABLE tickets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_number TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  customer_id INTEGER NOT NULL,
  equipment_model_id INTEGER NOT NULL,
  problem_description TEXT NOT NULL,
  fault_type_id INTEGER,
  status_id INTEGER NOT NULL,
  opened_by_user_id INTEGER NOT NULL,
  assigned_specialist_user_id INTEGER,
  completed_at TEXT,
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
  FOREIGN KEY (equipment_model_id) REFERENCES equipment_models(id) ON DELETE RESTRICT,
  FOREIGN KEY (fault_type_id) REFERENCES fault_types(id) ON DELETE SET NULL,
  FOREIGN KEY (status_id) REFERENCES ticket_statuses(id) ON DELETE RESTRICT,
  FOREIGN KEY (opened_by_user_id) REFERENCES users(id) ON DELETE RESTRICT,
  FOREIGN KEY (assigned_specialist_user_id) REFERENCES users(id) ON DELETE SET NULL
);
INSERT INTO "tickets" VALUES(1,'R-20251210-0001','2025-12-10 10:00:00',1,1,'Не включается после включения в сеть',1,1,2,3,NULL,'2025-12-10 10:00:00');
INSERT INTO "tickets" VALUES(2,'R-20251211-0001','2025-12-11 09:30:00',2,2,'Плохо охлаждает',2,4,2,3,'2025-12-11 12:00:00','2025-12-11 12:00:00');
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role_id INTEGER NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);
INSERT INTO "users" VALUES(1,'admin','scrypt:32768:8:1$nStAoYjxanQmjas3$84aab3b275a838cccd3999ef53a88dbc9de0b5ca49dd5a76ca76a426c4f4c204031288584738c16349b8c3f48a7fba13681130c64621f728796dcff4a6e085fd','Администратор',1,1,'2025-12-16 13:12:34');
INSERT INTO "users" VALUES(2,'operator','scrypt:32768:8:1$pOnzOuts9dZpGjXL$d1d0d3d7cf2da44ae0acc2886d97815834a8c318a118490993a74f49b98120b1334a44637d5a2a82c159c83e1d38b1de1ceb9a518f0e17bf5da5c212f4b70336','Оператор',2,1,'2025-12-16 13:12:34');
INSERT INTO "users" VALUES(3,'specialist','scrypt:32768:8:1$zaeyrSRWJWAWutiQ$06b98980c3025a7e5a6cc58cf3d55eb90804b3bd2f44394f73f54527fe187923fb3a9fad34816ba6c557639ee20cd4be8b83a7f61840897fabb5c5bc77564fd7','Специалист',3,1,'2025-12-16 13:12:34');
CREATE INDEX idx_tickets_status_id ON tickets(status_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_assigned_specialist ON tickets(assigned_specialist_user_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('roles',3);
INSERT INTO "sqlite_sequence" VALUES('users',3);
INSERT INTO "sqlite_sequence" VALUES('ticket_statuses',4);
INSERT INTO "sqlite_sequence" VALUES('equipment_types',2);
INSERT INTO "sqlite_sequence" VALUES('equipment_models',3);
INSERT INTO "sqlite_sequence" VALUES('fault_types',5);
INSERT INTO "sqlite_sequence" VALUES('customers',2);
INSERT INTO "sqlite_sequence" VALUES('parts',3);
INSERT INTO "sqlite_sequence" VALUES('tickets',2);
INSERT INTO "sqlite_sequence" VALUES('ticket_status_history',3);
INSERT INTO "sqlite_sequence" VALUES('ticket_comments',2);
INSERT INTO "sqlite_sequence" VALUES('ticket_parts',2);
COMMIT;
