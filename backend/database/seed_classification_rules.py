import json
import sqlite3
from typing import List, Dict, Any

RULES: List[Dict[str, Any]] = [
    {
        "rule_id": "rule_best_customer",
        "category": "superlative",
        "term_alias": "best_customer",
        "title": "Best / Top Customer Definition",
        "description": "Determines which customer is considered 'best' or 'top' in reporting periods.",
        "primary_metric": "Total Revenue from Completed Orders ($)",
        "primary_sql_expression": "SUM(orders.total_amount)",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "revenue", "label": "Total Net Revenue ($)", "sql": "SUM(orders.total_amount)", "filter": "orders.status = 'completed'"},
            {"key": "order_count", "label": "Total Completed Orders", "sql": "COUNT(DISTINCT orders.order_id)", "filter": "orders.status = 'completed'"},
            {"key": "units_purchased", "label": "Total Items Purchased", "sql": "SUM(order_items.quantity)", "filter": "orders.status = 'completed'"},
            {"key": "avg_order_value", "label": "Average Order Value ($)", "sql": "AVG(orders.total_amount)", "filter": "orders.status = 'completed'"}
        ]),
        "temporal_interpretation": "Requires pairing with specified date window; defaults to all-time if unspecified.",
        "rationale": "Enterprise GAAP revenue recognition standard: Only completed and paid orders constitute valid revenue. Cancelled, refunded, or pending orders must be excluded to prevent financial distortion.",
        "why_baseline_fails": "Baseline Text-to-SQL naively uses COUNT(*) or SUM(total_amount) without checking orders.status, causing customers with multiple cancelled or fraudulent high-dollar transactions to be incorrectly crowned as the 'best customer'."
    },
    {
        "rule_id": "rule_top_product",
        "category": "superlative",
        "term_alias": "top_product",
        "title": "Top / Best Selling Product",
        "description": "Defines what makes a product 'top' or 'best' in sales and merchandising.",
        "primary_metric": "Total Revenue from Completed Orders ($)",
        "primary_sql_expression": "SUM(order_items.quantity * order_items.unit_price)",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "revenue", "label": "Total Sales Revenue ($)", "sql": "SUM(order_items.quantity * order_items.unit_price)", "filter": "orders.status = 'completed'"},
            {"key": "units_sold", "label": "Total Quantity Sold", "sql": "SUM(order_items.quantity)", "filter": "orders.status = 'completed'"},
            {"key": "review_rating", "label": "Average Customer Rating", "sql": "AVG(product_reviews.rating)", "filter": "1=1"},
            {"key": "net_profit", "label": "Total Gross Margin ($)", "sql": "SUM((order_items.unit_price - products.cost_price) * order_items.quantity)", "filter": "orders.status = 'completed'"}
        ]),
        "temporal_interpretation": "Aggregated across specified period or all-time.",
        "rationale": "Commercial performance in financial statements is ranked by dollar revenue impact, while inventory management might track units sold.",
        "why_baseline_fails": "Baseline models alternate erratically between ranking by stock quantity, product ID, review rating, or unit count, without applying the required completed order filter."
    },
    {
        "rule_id": "rule_last_month",
        "category": "temporal",
        "term_alias": "last_month",
        "title": "Last Month Temporal Boundary",
        "description": "Standardizes the definition of 'last month' across all reporting queries.",
        "primary_metric": "Previous Complete Calendar Month",
        "primary_sql_expression": "order_date >= date('2024-05-01') AND order_date <= date('2024-05-31')",
        "filter_conditions": "order_date >= date('2024-05-01') AND order_date <= date('2024-05-31')",
        "alternative_metrics": json.dumps([
            {"key": "calendar_month", "label": "Preceding Calendar Month (e.g., May 1 - May 31)", "desc": "Closed calendar cycle"},
            {"key": "rolling_30d", "label": "Trailing 30-Day Window", "desc": "Past 30 days from reference date"}
        ]),
        "temporal_interpretation": "Relative to business reference period: full closed month prior to current transaction date.",
        "rationale": "Financial and sales bookkeeping closes at the end of each calendar month. Using rolling 30 days mixes current incomplete operational data with historical figures.",
        "why_baseline_fails": "Baseline systems use `date('now', '-30 days')` or `strftime('%m', order_date) = strftime('%m', 'now') - 1`, which fails across year boundaries (January to December) and compares partial months unfairly."
    },
    {
        "rule_id": "rule_churned_customer",
        "category": "lifecycle",
        "term_alias": "churned_customer",
        "title": "Customer Churn Definition",
        "description": "Standard criteria for classifying a customer account as churned / lost.",
        "primary_metric": "Customers with prior orders but no completed order in the last 90 days",
        "primary_sql_expression": "MAX(orders.order_date) < date('2024-03-01')",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "90d_inactivity", "label": "90 Days Inactivity with Historical Orders", "desc": "No orders in >= 90 days"},
            {"key": "180d_inactivity", "label": "180 Days Inactivity", "desc": "Long-term lapsed customers"},
            {"key": "profile_churned", "label": "Flagged as Churned in CRM", "desc": "customers.status = 'churned'"}
        ]),
        "temporal_interpretation": "Inactivity threshold measured against reference business date.",
        "rationale": "In subscription and recurring e-commerce, customer churn is behavioral (lapse in transaction frequency) rather than an explicit opt-out status flag in a database table.",
        "why_baseline_fails": "Baseline LLMs execute `SELECT * FROM customers WHERE status = 'churned'`, returning zero records because CRM status fields are rarely manually updated, missing 100% of behaviorally churned clients."
    },
    {
        "rule_id": "rule_active_customer",
        "category": "lifecycle",
        "term_alias": "active_customer",
        "title": "Active Customer Definition",
        "description": "Standard criteria for identifying currently active customer accounts.",
        "primary_metric": "Placed at least 1 completed purchase in past 60 days",
        "primary_sql_expression": "EXISTS (SELECT 1 FROM orders WHERE orders.customer_id = customers.customer_id AND orders.status = 'completed' AND orders.order_date >= date('2024-04-01'))",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "60d_transaction", "label": "Transacted in Last 60 Days", "desc": "Recent completed order"},
            {"key": "30d_transaction", "label": "Transacted in Last 30 Days", "desc": "High-frequency active buyer"},
            {"key": "account_active", "label": "Account Status Active", "desc": "customers.status = 'active'"}
        ]),
        "temporal_interpretation": "Trailing 60 days from reference date.",
        "rationale": "Account registration status is not equivalent to commercial activity. A customer registered as 'active' who hasn't purchased in two years is commercially dormant.",
        "why_baseline_fails": "Baseline queries filter by `WHERE customers.status = 'active'`, mistakenly reporting inactive and dormant users as active consumers."
    },
    {
        "rule_id": "rule_vip_customer",
        "category": "lifecycle",
        "term_alias": "vip_customer",
        "title": "VIP / High-Value Customer Tier",
        "description": "Classification boundary for VIP customer treatment and executive reporting.",
        "primary_metric": "Lifetime Completed Spend >= $2,000",
        "primary_sql_expression": "SUM(orders.total_amount) >= 2000",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "spend_2000", "label": "Lifetime Spend >= $2,000", "desc": "Primary high-value benchmark"},
            {"key": "order_count_5", "label": "Frequent Buyer (>= 5 completed orders)", "desc": "High engagement volume"},
            {"key": "segment_vip", "label": "Assigned to VIP Segment", "desc": "customers.segment = 'VIP'"}
        ]),
        "temporal_interpretation": "Lifetime cumulative window.",
        "rationale": "High-touch support and loyalty benefits require strict qualification based on realized cumulative cash flow.",
        "why_baseline_fails": "Baseline systems fabricate arbitrary thresholds (e.g. `total_amount > 500` or `segment = 'VIP'`), excluding loyal enterprise buyers who exceed $2,000 spend but belong to the 'Enterprise' segment."
    },
    {
        "rule_id": "rule_most_profitable_product",
        "category": "financial",
        "term_alias": "most_profitable_product",
        "title": "Most Profitable Product",
        "description": "Differentiates gross dollar contribution margin from percentage profit margin.",
        "primary_metric": "Total Net Dollar Gross Margin ($)",
        "primary_sql_expression": "SUM((order_items.unit_price - products.cost_price) * order_items.quantity)",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "gross_margin_dollars", "label": "Total Gross Margin ($)", "desc": "Realized cumulative dollar profit"},
            {"key": "margin_percentage", "label": "Gross Margin Percentage (%)", "desc": "AVG((price - cost_price) / price * 100)"}
        ]),
        "temporal_interpretation": "Lifetime or specified period.",
        "rationale": "A $2 phone screen protector sold at a 90% margin makes only $1.80 per unit, while an enterprise laptop at a 20% margin produces $300 profit per unit. Corporate profit is maximized by dollar contribution.",
        "why_baseline_fails": "Baseline LLMs consistently calculate `(price - cost)/price` and sort by percentage, recommending low-value commodity items that generate virtually no real cash profit."
    },
    {
        "rule_id": "rule_slow_moving_inventory",
        "category": "financial",
        "term_alias": "slow_moving_inventory",
        "title": "Slow-Moving / Dead Inventory",
        "description": "Identifies excess stock with sluggish consumer demand.",
        "primary_metric": "In-stock inventory (> 20 units) with less than 3 units sold in the last 60 days",
        "primary_sql_expression": "products.stock_quantity > 20 AND COALESCE(SUM(order_items.quantity), 0) < 3",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "dead_stock", "label": "High Stock (>20) + Low Sales (<3 in 60d)", "desc": "Capital-trapping products"},
            {"key": "zero_sales", "label": "Zero Sales in Last 90 Days", "desc": "Completely dormant items"}
        ]),
        "temporal_interpretation": "60-day trailing sales period.",
        "rationale": "Warehouse operations must prevent tying up working capital in stagnant stock, while filtering out out-of-stock items whose sales were zero simply because inventory was depleted.",
        "why_baseline_fails": "Baseline queries simply sort by `stock_quantity DESC` or find items with 0 orders, mistaking out-of-stock bestsellers (stock=0) or newly cataloged products for dead stock."
    },
    {
        "rule_id": "rule_highest_return_rate",
        "category": "financial",
        "term_alias": "highest_return_rate",
        "title": "Highest Product Return Rate",
        "description": "Calculates return rate with statistical minimum volume threshold.",
        "primary_metric": "Return Percentage with Minimum 5 Total Orders",
        "primary_sql_expression": "CAST(SUM(CASE WHEN orders.status = 'returned' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(orders.order_id) * 100",
        "filter_conditions": "COUNT(orders.order_id) >= 5",
        "alternative_metrics": json.dumps([
            {"key": "rate_with_threshold", "label": "Return Rate with >= 5 Orders", "desc": "Statistically meaningful returns"},
            {"key": "absolute_returned_items", "label": "Total Returned Units", "desc": "Absolute count of returns"}
        ]),
        "temporal_interpretation": "All-time or specified timeframe.",
        "rationale": "Without a minimum order threshold, a product purchased once and returned has a 100% return rate, causing random one-off items to eclipse genuinely defective high-volume products.",
        "why_baseline_fails": "Baseline systems compute `returned / total` without a `HAVING COUNT(*) >= 5` clause, surfacing fringe products with 1 order instead of high-risk operational defects."
    },
    {
        "rule_id": "rule_discount_impact",
        "category": "financial",
        "term_alias": "discount_impact",
        "title": "Discount Impact / Cost of Promotion",
        "description": "Measures total promotional dollars surrendered across orders.",
        "primary_metric": "Total Discount Amount Granted on Completed Orders ($)",
        "primary_sql_expression": "SUM(orders.discount_amount)",
        "filter_conditions": "orders.status = 'completed'",
        "alternative_metrics": json.dumps([
            {"key": "total_discount_dollars", "label": "Total Discount ($)", "desc": "Cumulative promotional dollar loss"},
            {"key": "discount_rate", "label": "Average Discount Percentage", "desc": "AVG(discount_amount / (total_amount + discount_amount) * 100)"}
        ]),
        "temporal_interpretation": "Aggregated by customer, product category, or time window.",
        "rationale": "Finance teams audit promotions by evaluating total margin eroded rather than nominal coupon usage counts.",
        "why_baseline_fails": "Baseline queries routinely ignore whether the order was actually completed or cancelled, reporting promotional costs on orders that were never fulfilled."
    }
]

def seed_classification_rules(conn: sqlite3.Connection):
    cursor = conn.cursor()
    for rule in RULES:
        cursor.execute("""
            INSERT OR REPLACE INTO metric_classification_rules (
                rule_id, category, term_alias, title, description,
                primary_metric, primary_sql_expression, filter_conditions,
                alternative_metrics, temporal_interpretation, rationale, why_baseline_fails
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule["rule_id"],
            rule["category"],
            rule["term_alias"],
            rule["title"],
            rule["description"],
            rule["primary_metric"],
            rule["primary_sql_expression"],
            rule["filter_conditions"],
            rule["alternative_metrics"],
            rule["temporal_interpretation"],
            rule["rationale"],
            rule["why_baseline_fails"]
        ))
    conn.commit()
    print(f"Successfully seeded {len(RULES)} enterprise classification rules.")

if __name__ == "__main__":
    conn = sqlite3.connect("enterprise_retail.db")
    seed_classification_rules(conn)
    conn.close()
