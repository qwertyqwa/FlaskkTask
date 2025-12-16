PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS ticket_parts;
DROP TABLE IF EXISTS parts;
DROP TABLE IF EXISTS ticket_comments;
DROP TABLE IF EXISTS ticket_status_history;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS ticket_statuses;
DROP TABLE IF EXISTS fault_types;
DROP TABLE IF EXISTS equipment_models;
DROP TABLE IF EXISTS equipment_types;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

CREATE TABLE roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE
);

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

CREATE TABLE customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name TEXT NOT NULL,
  phone TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (phone, full_name)
);

CREATE TABLE equipment_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE equipment_models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  manufacturer TEXT,
  UNIQUE (equipment_type_id, name),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id) ON DELETE RESTRICT
);

CREATE TABLE fault_types (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE ticket_statuses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL UNIQUE,
  is_final INTEGER NOT NULL DEFAULT 0
);

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

CREATE INDEX idx_tickets_status_id ON tickets(status_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_assigned_specialist ON tickets(assigned_specialist_user_id);

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

CREATE TABLE ticket_comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE parts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

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

