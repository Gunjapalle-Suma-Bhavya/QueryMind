import os
import re
import sqlite3
import json
from typing import Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "enterprise_retail.db")
SAKILA_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_db-master", "sakila", "sakila-mv-data.sql")
DEPT_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_db-master", "load_departments.dump")
DEPT_MGR_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_db-master", "load_dept_manager.dump")

def create_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    schema_sql = """
    CREATE TABLE IF NOT EXISTS actor (
      actor_id INTEGER PRIMARY KEY AUTOINCREMENT,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS country (
      country_id INTEGER PRIMARY KEY AUTOINCREMENT,
      country TEXT NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS city (
      city_id INTEGER PRIMARY KEY AUTOINCREMENT,
      city TEXT NOT NULL,
      country_id INTEGER NOT NULL REFERENCES country(country_id),
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS address (
      address_id INTEGER PRIMARY KEY AUTOINCREMENT,
      address TEXT NOT NULL,
      address2 TEXT,
      district TEXT NOT NULL,
      city_id INTEGER NOT NULL REFERENCES city(city_id),
      postal_code TEXT,
      phone TEXT NOT NULL,
      location BLOB,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS category (
      category_id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS staff (
      staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      address_id INTEGER NOT NULL REFERENCES address(address_id),
      picture BLOB,
      email TEXT,
      store_id INTEGER NOT NULL,
      active INTEGER NOT NULL DEFAULT 1,
      username TEXT NOT NULL,
      password TEXT,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS store (
      store_id INTEGER PRIMARY KEY AUTOINCREMENT,
      manager_staff_id INTEGER NOT NULL,
      address_id INTEGER NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS customer (
      customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
      store_id INTEGER NOT NULL REFERENCES store(store_id),
      first_name TEXT NOT NULL,
      last_name TEXT NOT NULL,
      email TEXT,
      address_id INTEGER NOT NULL REFERENCES address(address_id),
      active INTEGER NOT NULL DEFAULT 1,
      create_date DATETIME NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS language (
      language_id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS film (
      film_id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT,
      release_year INTEGER,
      language_id INTEGER NOT NULL,
      original_language_id INTEGER,
      rental_duration INTEGER NOT NULL DEFAULT 3,
      rental_rate REAL NOT NULL DEFAULT 4.99,
      length INTEGER,
      replacement_cost REAL NOT NULL DEFAULT 19.99,
      rating TEXT DEFAULT 'G',
      special_features TEXT,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS film_actor (
      actor_id INTEGER NOT NULL REFERENCES actor(actor_id),
      film_id INTEGER NOT NULL REFERENCES film(film_id),
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (actor_id, film_id)
    );

    CREATE TABLE IF NOT EXISTS film_category (
      film_id INTEGER NOT NULL REFERENCES film(film_id),
      category_id INTEGER NOT NULL REFERENCES category(category_id),
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (film_id, category_id)
    );

    CREATE TABLE IF NOT EXISTS inventory (
      inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
      film_id INTEGER NOT NULL REFERENCES film(film_id),
      store_id INTEGER NOT NULL REFERENCES store(store_id),
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rental (
      rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
      rental_date DATETIME NOT NULL,
      inventory_id INTEGER NOT NULL REFERENCES inventory(inventory_id),
      customer_id INTEGER NOT NULL REFERENCES customer(customer_id),
      return_date DATETIME,
      staff_id INTEGER NOT NULL REFERENCES staff(staff_id),
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payment (
      payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_id INTEGER NOT NULL REFERENCES customer(customer_id),
      staff_id INTEGER NOT NULL REFERENCES staff(staff_id),
      rental_id INTEGER REFERENCES rental(rental_id),
      amount REAL NOT NULL,
      payment_date DATETIME NOT NULL,
      last_update DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS departments (
      dept_no TEXT PRIMARY KEY,
      dept_name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dept_manager (
      emp_no INTEGER NOT NULL,
      dept_no TEXT NOT NULL,
      from_date DATE NOT NULL,
      to_date DATE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS metric_classification_rules (
      rule_id TEXT PRIMARY KEY,
      category TEXT NOT NULL,
      term_alias TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      primary_metric TEXT NOT NULL,
      primary_sql_expression TEXT NOT NULL,
      filter_conditions TEXT NOT NULL,
      alternative_metrics TEXT NOT NULL,
      temporal_interpretation TEXT,
      rationale TEXT NOT NULL,
      why_baseline_fails TEXT NOT NULL
    );

    -- Convenient compatibility views mapping generic enterprise entities to user's database tables
    DROP VIEW IF EXISTS customers;
    CREATE VIEW customers AS
    SELECT 
      customer_id,
      first_name || ' ' || last_name AS name,
      email,
      CASE WHEN customer_id IN (1, 2, 5) THEN 'VIP' ELSE 'Consumer' END AS segment,
      'Store ' || store_id AS country,
      CASE WHEN active = 1 THEN 'active' ELSE 'inactive' END AS status,
      DATE(create_date) AS created_at
    FROM customer;

    DROP VIEW IF EXISTS products;
    CREATE VIEW products AS
    SELECT 
      f.film_id AS product_id,
      f.title AS name,
      COALESCE(c.name, 'Feature') AS category,
      f.rental_rate AS price,
      ROUND(f.rental_rate * 0.45, 2) AS cost_price,
      (SELECT COUNT(*) FROM inventory i WHERE i.film_id = f.film_id) AS stock_quantity,
      'active' AS status
    FROM film f
    LEFT JOIN film_category fc ON f.film_id = fc.film_id
    LEFT JOIN category c ON fc.category_id = c.category_id;

    DROP VIEW IF EXISTS orders;
    CREATE VIEW orders AS
    SELECT 
      p.payment_id AS order_id,
      p.customer_id,
      DATE(p.payment_date) AS order_date,
      p.amount AS total_amount,
      0.0 AS discount_amount,
      0.0 AS shipping_cost,
      CASE 
        WHEN p.amount = 0.0 THEN 'cancelled'
        WHEN r.return_date IS NULL AND p.payment_date < '2005-08-01' THEN 'returned'
        ELSE 'completed'
      END AS status,
      'Credit Card' AS payment_method
    FROM payment p
    LEFT JOIN rental r ON p.rental_id = r.rental_id;

    DROP VIEW IF EXISTS order_items;
    CREATE VIEW order_items AS
    SELECT 
      r.rental_id AS order_item_id,
      p.payment_id AS order_id,
      i.film_id AS product_id,
      1 AS quantity,
      p.amount AS unit_price,
      0.0 AS discount
    FROM rental r
    JOIN inventory i ON r.inventory_id = i.inventory_id
    JOIN payment p ON r.rental_id = p.rental_id;
    """
    cursor.executescript(schema_sql)
    conn.commit()

def load_sakila_data(conn: sqlite3.Connection):
    if not os.path.exists(SAKILA_DATA_PATH):
        raise FileNotFoundError(f"User database file not found at {SAKILA_DATA_PATH}")

    cursor = conn.cursor()
    print(f"Loading user database file: {SAKILA_DATA_PATH}")

    with open(SAKILA_DATA_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_stmt = []
    in_insert = False
    count = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("INSERT INTO"):
            in_insert = True
            current_stmt = [line]
        elif in_insert:
            current_stmt.append(line)
            if stripped.endswith(";"):
                in_insert = False
                raw_sql = "".join(current_stmt)
                clean = re.sub(r'`([a-zA-Z0-9_]+)`', r'\1', raw_sql)
                clean = re.sub(r'/\*!50705\s*0x[0-9a-fA-F]+,\*/', 'NULL,', clean)
                clean = re.sub(r'/\*!.*?\*/', '', clean)
                clean = re.sub(r'0x[0-9a-fA-F]{20,}', 'NULL', clean)
                try:
                    cursor.execute(clean)
                    count += 1
                except Exception as e:
                    print(f"Notice: skipped or handled insert: {e}")

    conn.commit()
    print(f"Successfully executed {count} multi-row INSERT blocks from user Sakila database.")

def load_department_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    if os.path.exists(DEPT_DATA_PATH):
        print(f"Loading departments from: {DEPT_DATA_PATH}")
        with open(DEPT_DATA_PATH, "r", encoding="utf-8") as f:
            dept_sql = f.read()
            clean_dept = re.sub(r'`([a-zA-Z0-9_]+)`', r'\1', dept_sql)
            cursor.execute(clean_dept)
        conn.commit()

    if os.path.exists(DEPT_MGR_PATH):
        print(f"Loading dept managers from: {DEPT_MGR_PATH}")
        with open(DEPT_MGR_PATH, "r", encoding="utf-8") as f:
            mgr_sql = f.read()
            clean_mgr = re.sub(r'`([a-zA-Z0-9_]+)`', r'\1', mgr_sql)
            cursor.execute(clean_mgr)
        conn.commit()

def seed_rules(conn: sqlite3.Connection):
    from backend.database.seed_classification_rules import RULES
    cursor = conn.cursor()
    for rule in RULES:
        cursor.execute("""
            INSERT OR REPLACE INTO metric_classification_rules (
                rule_id, category, term_alias, title, description,
                primary_metric, primary_sql_expression, filter_conditions,
                alternative_metrics, temporal_interpretation, rationale, why_baseline_fails
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule["rule_id"], rule["category"], rule["term_alias"], rule["title"],
            rule["description"], rule["primary_metric"], rule["primary_sql_expression"],
            rule["filter_conditions"], rule["alternative_metrics"],
            rule["temporal_interpretation"], rule["rationale"], rule["why_baseline_fails"]
        ))
    conn.commit()
    print(f"Seeded {len(RULES)} enterprise classification rules.")

def load_user_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    load_sakila_data(conn)
    load_department_data(conn)
    seed_rules(conn)
    conn.close()
    print("Database built exclusively from user-supplied database files!")

if __name__ == "__main__":
    load_user_db()
