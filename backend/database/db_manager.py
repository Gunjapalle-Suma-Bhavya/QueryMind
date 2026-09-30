import os
import sqlite3
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from backend.database.seed_classification_rules import seed_classification_rules

DB_PATH = os.path.join(os.path.dirname(__file__), "enterprise_retail.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

# Business Reference Anchor Date for deterministic benchmark evaluations
REFERENCE_DATE = datetime(2024, 6, 15)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reseed: bool = False):
    """Initializes the database schema using user-supplied database files."""
    user_db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_db-master")
    if os.path.exists(user_db_dir):
        from backend.database.user_db_loader import load_user_db
        if not os.path.exists(DB_PATH) or force_reseed:
            print(f"Detected user database folder: {user_db_dir}. Building database from user files...")
            load_user_db()
            return

    if os.path.exists(DB_PATH) and not force_reseed:
        # Check if already seeded
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM metric_classification_rules")
            rule_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM orders")
            order_count = cursor.fetchone()[0]
            conn.close()
            if rule_count >= 10 and order_count >= 300:
                print(f"Database already populated: {order_count} orders, {rule_count} classification rules.")
                return
        except Exception:
            pass

    print("Initializing schema and seeding enterprise data...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_db_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()

    # Seed classification rules
    seed_classification_rules(conn)

    # Seed operational business data
    _seed_enterprise_data(conn)
    conn.close()
    print("Database initialization and seeding completed successfully.")

def _seed_enterprise_data(conn: sqlite3.Connection):
    random.seed(42)
    cursor = conn.cursor()

    # 1. Seed Customers (60 realistic accounts)
    first_names = ["Sarah", "Marcus", "Elena", "David", "Jessica", "Liam", "Amara", "Robert", "Chloe", "Alexander",
                   "Maya", "Carlos", "Fatima", "Ethan", "Zoe", "James", "Emma", "Noah", "Olivia", "William",
                   "Sophia", "Lucas", "Ava", "Henry", "Isabella", "Benjamin", "Mia", "Daniel", "Charlotte", "Matthew"]
    last_names = ["Connor", "Vance", "Rostova", "Miller", "Chen", "Smith", "Johnson", "Williams", "Brown", "Jones",
                  "Garcia", "Martinez", "Rodriguez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
                  "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark"]
    countries = ["United States", "Canada", "United Kingdom", "Germany", "France", "Australia", "Japan", "Singapore"]
    segments = ["Consumer", "SMB", "Enterprise", "VIP"]

    customer_records = []
    # Explicit engineered benchmark customers:
    customer_records.append(("Sarah Connor", "sarah.connor@cyberdyne.io", "Enterprise", "United States", "active", "2023-01-15"))
    customer_records.append(("Marcus Vance", "marcus.vance@techfail.org", "Consumer", "United States", "active", "2023-03-10"))
    customer_records.append(("Elena Rostova", "elena.rostova@globalcorp.eu", "SMB", "Germany", "active", "2023-02-20"))
    customer_records.append(("David Miller", "david.miller@lapsedaccount.net", "Consumer", "Canada", "active", "2022-08-01"))
    customer_records.append(("Arthur Pendelton", "arthur.p@royallogistics.uk", "VIP", "United Kingdom", "active", "2022-11-12"))

    for i in range(5, 60):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{i}@example.com"
        seg = random.choice(segments)
        country = random.choice(countries)
        status = "active" if random.random() > 0.15 else "inactive"
        created_days_ago = random.randint(100, 600)
        created_at = (REFERENCE_DATE - timedelta(days=created_days_ago)).strftime("%Y-%m-%d")
        customer_records.append((name, email, seg, country, status, created_at))

    cursor.executemany("""
        INSERT INTO customers (name, email, segment, country, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, customer_records)

    # 2. Seed Products (35 varied items across 5 categories)
    product_data = [
        # Electronics
        ("Ultra HD 4K Monitor 32-inch", "Electronics", 649.99, 320.00, 45, "active"),
        ("Noise-Cancelling Wireless Headphones", "Electronics", 299.99, 130.00, 80, "active"),
        ("USB-C Fast Charging Multi-Hub", "Electronics", 49.99, 14.50, 150, "active"),
        ("Ergonomic Mechanical Keyboard", "Electronics", 129.99, 48.00, 60, "active"),
        ("Precision Wireless Mouse", "Electronics", 59.99, 21.00, 95, "active"),
        ("Smart 4K Web Camera Pro", "Electronics", 119.99, 45.00, 30, "active"),
        ("Portable SSD Drive 2TB", "Electronics", 179.99, 78.00, 40, "active"),
        ("Pro Wireless Earbuds", "Electronics", 149.99, 52.00, 0, "active"), # 0 stock, popular
        # Furniture
        ("Smart Ergonomic Desk", "Furniture", 599.99, 280.00, 25, "active"),
        ("Executive Lumbar Mesh Chair", "Furniture", 349.99, 160.00, 35, "active"),
        ("Dual Monitor Steel Arm", "Furniture", 89.99, 32.00, 70, "active"),
        ("Adjustable Footrest Platform", "Furniture", 44.99, 15.00, 50, "active"),
        ("Under-Desk Cable Organizer", "Furniture", 29.99, 8.00, 110, "active"),
        # Office Supplies
        ("Old Laser Printer Cartridge Legacy", "Office Supplies", 79.99, 35.00, 65, "active"), # Dead stock
        ("Recycled Copy Paper 5-Pack", "Office Supplies", 39.99, 18.00, 200, "active"),
        ("Gel Ink Rollerball Pens 12pk", "Office Supplies", 18.99, 5.20, 180, "active"),
        ("Hardcover Executive Notebook", "Office Supplies", 24.99, 6.50, 140, "active"),
        ("Heavy Duty Desktop Stapler", "Office Supplies", 34.99, 12.00, 75, "active"),
        ("Whiteboard Magnetic Eraser Set", "Office Supplies", 14.99, 3.80, 90, "active"),
        # Apparel
        ("Merino Wool Tech Sweater", "Apparel", 119.99, 42.00, 45, "active"),
        ("Breathable Performance Polo", "Apparel", 49.99, 16.00, 90, "active"),
        ("Water-Resistant Commuter Jacket", "Apparel", 169.99, 68.00, 30, "active"),
        ("Organic Cotton Casual T-Shirt", "Apparel", 29.99, 8.50, 160, "active"),
        # Accessories
        ("Waterproof Laptop Sleeve 15-inch", "Accessories", 39.99, 11.00, 85, "active"),
        ("Travel Cable Organizer Pouch", "Accessories", 22.99, 6.00, 120, "active"),
        ("Insulated Stainless Water Bottle", "Accessories", 34.99, 10.50, 130, "active"),
        ("Blue Light Blocking Glasses", "Accessories", 45.00, 12.00, 70, "active"),
        ("Novelty Stress Ball", "Accessories", 9.99, 1.80, 15, "active") # low volume test item
    ]

    cursor.executemany("""
        INSERT INTO products (name, category, price, cost_price, stock_quantity, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, product_data)

    # 3. Seed Orders and Order Items
    # Specific benchmark scenarios:
    # Customer 1 (Sarah Connor):
    # Orders in May 2024 (Last month relative to June 2024):
    # Sarah places 4 large completed orders in May 2024 totaling $4,850.
    orders_data = []
    order_items_data = []

    # Sarah Connor: Customer ID 1
    sarah_may_dates = ["2024-05-04", "2024-05-12", "2024-05-19", "2024-05-27"]
    sarah_order_totals = [1420.00, 1250.00, 1100.00, 1080.00]
    for date_str, amt in zip(sarah_may_dates, sarah_order_totals):
        orders_data.append((1, date_str, amt, 50.0, 0.0, "completed", "Credit Card"))

    # Marcus Vance: Customer ID 2
    # Marcus places 8 CANCELLED orders of $3,500 each in May 2024, and 1 completed order of $45!
    # Without classification (checking completed status), Marcus appears to have $28,000+!
    for d in ["2024-05-02", "2024-05-06", "2024-05-10", "2024-05-15", "2024-05-20", "2024-05-22", "2024-05-25", "2024-05-29"]:
        orders_data.append((2, d, 3500.00, 0.0, 15.0, "cancelled", "Credit Card"))
    orders_data.append((2, "2024-05-11", 45.00, 0.0, 5.0, "completed", "Credit Card"))

    # Elena Rostova: Customer ID 3
    # Elena has 14 frequent small completed orders in May 2024 totaling $850.
    # Baseline ranking by COUNT(order_id) would wrongly pick Elena as 'best customer'.
    for day in range(1, 15):
        d_str = f"2024-05-{day:02d}"
        orders_data.append((3, d_str, 60.00, 5.0, 0.0, "completed", "PayPal"))

    # David Miller: Customer ID 4 (Churned: last order in Nov 2023)
    orders_data.append((4, "2023-09-15", 320.00, 0.0, 0.0, "completed", "Credit Card"))
    orders_data.append((4, "2023-11-10", 450.00, 20.0, 0.0, "completed", "Credit Card"))

    # Arthur Pendelton: Customer ID 5 (VIP: Lifetime spend over $3,500 across 2023-2024)
    for q_date, q_amt in [("2023-04-10", 900.00), ("2023-08-15", 1100.00), ("2024-01-20", 950.00), ("2024-04-05", 800.00)]:
        orders_data.append((5, q_date, q_amt, 40.0, 0.0, "completed", "Wire Transfer"))

    # Smart Ergonomic Desk (Product ID 9): High return rate test
    # Has 8 completed/returned orders, 5 of which are returned!
    for r_day in range(1, 9):
        status = "returned" if r_day <= 5 else "completed"
        cust = random.randint(6, 25)
        orders_data.append((cust, f"2024-04-{r_day*3:02d}", 599.99, 0.0, 25.0, status, "Credit Card"))

    # Novelty Stress Ball (Product ID 28): Low volume return test
    # 1 single order, returned! Return rate = 100%, but volume = 1!
    orders_data.append((10, "2024-04-18", 9.99, 0.0, 3.0, "returned", "Credit Card"))

    # General random orders (350+ realistic orders across 2023-01 to 2024-06)
    statuses = ["completed", "completed", "completed", "completed", "completed", "returned", "cancelled", "pending"]
    pay_methods = ["Credit Card", "PayPal", "Wire Transfer", "Apple Pay"]

    for _ in range(350):
        cust_id = random.randint(6, 59)
        # Distribute dates across last 18 months
        days_ago = random.randint(1, 500)
        o_date = (REFERENCE_DATE - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        total = round(random.uniform(25.0, 850.0), 2)
        discount = round(random.uniform(0.0, 40.0), 2) if random.random() > 0.6 else 0.0
        shipping = 10.0 if total < 100 else 0.0
        st = random.choice(statuses)
        pm = random.choice(pay_methods)
        orders_data.append((cust_id, o_date, total, discount, shipping, st, pm))

    cursor.executemany("""
        INSERT INTO orders (customer_id, order_date, total_amount, discount_amount, shipping_cost, status, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, orders_data)

    # 4. Seed Order Items
    # Fetch all order ids
    cursor.execute("SELECT order_id, total_amount FROM orders")
    order_rows = cursor.fetchall()

    for row in order_rows:
        oid = row["order_id"]
        if 34 <= oid <= 41:
            # Smart Ergonomic Desk orders (Product ID 9)
            order_items_data.append((oid, 9, 1, 599.99, 0.0))
        elif oid == 42:
            # Novelty Stress Ball (Product ID 28)
            order_items_data.append((oid, 28, 1, 9.99, 0.0))
        elif 1 <= oid <= 4:
            # Sarah Connor purchases Monitors and Keyboards
            order_items_data.append((oid, 1, 2, 649.99, 0.0))
        else:
            # Generate 1 to 3 items per general order (excluding targeted benchmark test items 9 and 28)
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                pid = random.choice([p for p in range(1, 28) if p not in (9, 28)])
                cursor.execute("SELECT price FROM products WHERE product_id = ?", (pid,))
                p_price = cursor.fetchone()["price"]
                qty = random.randint(1, 4)
                order_items_data.append((oid, pid, qty, p_price, 0.0))

    cursor.executemany("""
        INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount)
        VALUES (?, ?, ?, ?, ?)
    """, order_items_data)

    # 5. Seed Product Reviews
    reviews_data = []
    comments_5 = ["Exceptional quality and build!", "Five stars, transformed my home office workflow.", "Super fast shipping and premium finish.", "Worth every single penny."]
    comments_1 = ["Broke within two weeks.", "Terrible customer support and defective parts.", "Not as advertised, requesting return.", "Extremely disappointed with build quality."]
    comments_3 = ["Decent product for the price.", "Works fine, but manual was lacking.", "Average build quality, does the job."]

    for pid in range(1, 28):
        num_revs = random.randint(3, 8)
        for _ in range(num_revs):
            cid = random.randint(1, 55)
            # Desk has lower ratings, Monitor has high ratings
            if pid == 9: # Desk with return issue
                rating = random.choice([1, 2, 2, 3])
                cmt = random.choice(comments_1)
            elif pid == 1 or pid == 2:
                rating = random.choice([4, 5, 5, 5])
                cmt = random.choice(comments_5)
            else:
                rating = random.randint(1, 5)
                cmt = random.choice(comments_3) if rating == 3 else (random.choice(comments_5) if rating >= 4 else random.choice(comments_1))

            r_date = (REFERENCE_DATE - timedelta(days=random.randint(10, 300))).strftime("%Y-%m-%d")
            reviews_data.append((pid, cid, rating, cmt, r_date))

    cursor.executemany("""
        INSERT INTO product_reviews (product_id, customer_id, rating, comment, review_date)
        VALUES (?, ?, ?, ?, ?)
    """, reviews_data)

    conn.commit()
    print(f"Seeded {len(customer_records)} customers, {len(product_data)} products, {len(orders_data)} orders.")

def execute_query(sql: str, params: tuple = (), max_rows: int = 200) -> Dict[str, Any]:
    """
    Safely executes read-only SQL queries with guardrails against mutations.
    """
    # Guardrails: Read-only verification
    sanitized_sql = sql.strip().rstrip(";")
    upper_tokens = sanitized_sql.upper().split()
    first_token = upper_tokens[0] if upper_tokens else ""

    if first_token not in ("SELECT", "WITH"):
        raise ValueError(f"Security Guardrail Violation: Only read-only SELECT queries are permitted. Blocked command: '{first_token}'")

    forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA"]
    for word in upper_tokens:
        if word in forbidden_keywords:
            raise ValueError(f"Security Guardrail Violation: Mutation keyword '{word}' detected.")

    start_time = time.time()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sanitized_sql, params)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows)
        # Convert sqlite3.Row to regular dicts/lists for JSON serialization
        results = [dict(zip(columns, row)) for row in rows]
        execution_time_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "columns": columns,
            "results": results,
            "row_count": len(results),
            "execution_time_ms": execution_time_ms,
            "sql": sanitized_sql
        }
    finally:
        conn.close()

def get_schema_summary() -> str:
    """Returns a textual schema representation for prompt augmentation."""
    return """
Database Tables:
1. customers (customer_id INT PK, name TEXT, email TEXT, segment TEXT ['Consumer','SMB','Enterprise','VIP'], country TEXT, status TEXT ['active','inactive'], created_at DATE)
2. products (product_id INT PK, name TEXT, category TEXT ['Electronics','Furniture','Office Supplies','Apparel','Accessories'], price REAL, cost_price REAL, stock_quantity INT, status TEXT)
3. orders (order_id INT PK, customer_id INT FK, order_date DATE, total_amount REAL, discount_amount REAL, shipping_cost REAL, status TEXT ['completed','cancelled','returned','pending'], payment_method TEXT)
4. order_items (order_item_id INT PK, order_id INT FK, product_id INT FK, quantity INT, unit_price REAL, discount REAL)
5. product_reviews (review_id INT PK, product_id INT FK, customer_id INT FK, rating INT [1-5], comment TEXT, review_date DATE)
6. metric_classification_rules (rule_id TEXT PK, category TEXT, term_alias TEXT, title TEXT, primary_metric TEXT, primary_sql_expression TEXT, filter_conditions TEXT, alternative_metrics TEXT, temporal_interpretation TEXT, rationale TEXT)

Business Reference Date Anchor: 2024-06-15
Reference 'last month': May 2024 (2024-05-01 to 2024-05-31)
Reference 'last 60 days': 2024-04-16 to 2024-06-15
Reference 'last 90 days': 2024-03-17 to 2024-06-15
"""

if __name__ == "__main__":
    init_db(force_reseed=True)
    res = execute_query("SELECT COUNT(*) as total_orders FROM orders")
    print("Test Query Result:", res)
