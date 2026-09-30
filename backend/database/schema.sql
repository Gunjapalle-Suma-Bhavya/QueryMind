-- E-Commerce Business Relational Schema
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    segment TEXT NOT NULL,          -- 'Enterprise', 'SMB', 'Consumer', 'VIP'
    country TEXT NOT NULL,
    status TEXT NOT NULL,           -- 'active', 'inactive', 'churned'
    created_at DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,         -- 'Electronics', 'Office Supplies', 'Furniture', 'Apparel', 'Accessories'
    price REAL NOT NULL,
    cost_price REAL NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL            -- 'active', 'discontinued', 'out_of_stock'
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    total_amount REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    shipping_cost REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL,           -- 'completed', 'cancelled', 'returned', 'pending'
    payment_method TEXT NOT NULL,   -- 'Credit Card', 'PayPal', 'Wire Transfer', 'Apple Pay'
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS product_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    comment TEXT,
    review_date DATE NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Enterprise Metric Classification Registry Table
CREATE TABLE IF NOT EXISTS metric_classification_rules (
    rule_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,                -- 'superlative', 'temporal', 'lifecycle', 'financial'
    term_alias TEXT NOT NULL,              -- 'best_customer', 'top_product', 'last_month', etc.
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    primary_metric TEXT NOT NULL,          -- e.g. 'Total Net Revenue ($)'
    primary_sql_expression TEXT NOT NULL,  -- e.g. 'SUM(orders.total_amount)'
    filter_conditions TEXT NOT NULL,       -- e.g. "orders.status = 'completed'"
    alternative_metrics TEXT NOT NULL,     -- JSON array of alternatives
    temporal_interpretation TEXT,         -- e.g. 'Previous complete calendar month'
    rationale TEXT NOT NULL,               -- Business accounting justification
    why_baseline_fails TEXT NOT NULL       -- Explanation of silent data errors without this rule
);
