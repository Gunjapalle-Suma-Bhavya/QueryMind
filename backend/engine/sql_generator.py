import os
import re
import json
import requests
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from backend.database.db_manager import get_schema_summary

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load_all_envs(override: bool = False):
    for env_path in [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, "env.config"),
        os.path.join(PROJECT_ROOT, "backend", ".env"),
    ]:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=override)
    load_dotenv(override=override)

_load_all_envs(override=False)

class SQLGenerator:
    def __init__(self):
        self._refresh_keys()

    def _refresh_keys(self):
        _load_all_envs(override=True)
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_base_url = (os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "") or "https://api.openai.com/v1").strip().rstrip("/")
        self.provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()

    def _get_openai_chat_url(self, base_url: Optional[str] = None) -> str:
        """Constructs full chat/completions endpoint for OpenAI or custom AI credits relay."""
        b_url = (base_url or self.openai_base_url or "https://api.openai.com/v1").strip().rstrip("/")
        if not b_url:
            b_url = "https://api.openai.com/v1"
        if b_url.endswith("/chat/completions"):
            return b_url
        return f"{b_url}/chat/completions"

    def test_connection(self, provider: str, api_key: str, base_url: Optional[str] = None) -> Tuple[bool, str]:
        """Validates an API key against the provider's live endpoint (supports custom AI credits platform base URL)."""
        provider = provider.lower().strip()
        if provider == "gemini":
            if not api_key:
                return False, "Google Gemini API key is missing or blank."
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": "Respond with the word OK"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            try:
                resp = requests.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    return True, "Successfully connected to Google Gemini (gemini-1.5-flash)!"
                else:
                    return False, f"Gemini API Error (HTTP {resp.status_code}): {resp.text[:160]}"
            except Exception as e:
                return False, f"Gemini network error: {str(e)}"
        elif provider == "openai":
            if not api_key:
                return False, "OpenAI API key is missing or blank."
            url = self._get_openai_chat_url(base_url)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Respond with the word OK"}],
                "max_tokens": 5
            }
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    return True, f"Successfully connected to OpenAI-compatible endpoint ({url})!"
                else:
                    return False, f"API Error (HTTP {resp.status_code}): {resp.text[:160]}"
            except Exception as e:
                return False, f"Connection error to {url}: {str(e)}"
        elif provider in ("semantic_engine", "offline", "builtin"):
            return True, "Built-in Semantic Engine is active and verified (100% offline, zero-setup)."
        return False, f"Unknown provider: {provider}"

    def generate_sql(
        self,
        query: str,
        mode: str = "guided",
        clarification_context: Optional[Dict[str, Any]] = None,
        selected_metric: Optional[str] = None,
        override_api_key: Optional[str] = None,
        override_provider: Optional[str] = None,
        override_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates SQL query for the given natural language input.
        mode can be:
          - 'guided': Enriched with classification registry rules and explicit business constraints.
          - 'baseline': Naive text-to-SQL without classification knowledge (demonstrating real-world failure modes).
        """
        self._refresh_keys()

        active_provider = (override_provider or self.provider).lower()
        gemini_key = override_api_key if active_provider == "gemini" else (override_api_key or self.gemini_key)
        openai_key = override_api_key if active_provider == "openai" else (override_api_key or self.openai_key)
        openai_base = override_base_url or self.openai_base_url

        # 1. Attempt LLM Generation if API key is provided
        llm_sql = None
        model_name = None

        if active_provider in ("auto", "gemini") and gemini_key:
            llm_sql, err = self._call_gemini_api(query, mode, clarification_context, selected_metric, gemini_key)
            if llm_sql:
                model_name = "Google Gemini (gemini-1.5-flash)"
            elif err:
                print(f"[Notice] Gemini API call skipped/failed ({err}). Falling back to built-in semantic engine.")

        if not llm_sql and active_provider in ("auto", "openai") and openai_key:
            llm_sql, err = self._call_openai_api(
                query, mode, clarification_context, selected_metric, openai_key, base_url=openai_base
            )
            if llm_sql:
                if "api.openai.com" in openai_base:
                    model_name = "OpenAI (gpt-4o-mini)"
                else:
                    model_name = f"OpenAI Compatible AI Credits ({openai_base})"
            elif err:
                print(f"[Notice] OpenAI API call skipped/failed ({err}). Falling back to built-in semantic engine.")

        # 2. If LLM produced valid SQL, return it
        if llm_sql:
            if mode == "baseline":
                return {
                    "sql": llm_sql,
                    "mode": "baseline",
                    "explanation": f"Generated via {model_name} without classification table (raw naive text-to-SQL).",
                    "baseline_vulnerability": "Raw LLM output generated without business classification guardrails.",
                    "model_used": model_name
                }
            else:
                rule_name = clarification_context.get("primary_rule", {}).get("title", "Enterprise Standard") if clarification_context else "Enterprise Standard"
                return {
                    "sql": llm_sql,
                    "mode": "guided",
                    "explanation": f"Generated via {model_name} enriched with Enterprise Classification Registry: {rule_name}",
                    "classification_rule": rule_name,
                    "model_used": model_name
                }

        # 3. Deterministic Semantic Engine Fallback (Guarantees 100% offline uptime & zero cost)
        fallback_model = "Built-in Semantic Engine (Offline / Zero-Setup)"
        if mode == "baseline":
            sql, reason = self._generate_baseline_sql(query)
            return {
                "sql": sql,
                "mode": "baseline",
                "explanation": "Generated without classification table (raw naive text-to-SQL).",
                "baseline_vulnerability": reason,
                "model_used": fallback_model
            }
        else:
            sql, rule_used = self._generate_guided_sql(query, clarification_context, selected_metric)
            return {
                "sql": sql,
                "mode": "guided",
                "explanation": f"Generated using Enterprise Classification Registry: {rule_used}",
                "classification_rule": rule_used,
                "model_used": fallback_model
            }

    def _call_gemini_api(
        self,
        query: str,
        mode: str,
        clarification_context: Optional[Dict[str, Any]],
        selected_metric: Optional[str],
        api_key: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Invokes Google Gemini REST API directly with prompt tailored to baseline or guided mode."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = self._build_llm_prompt(query, mode, clarification_context, selected_metric)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 400
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=8)
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code}: {resp.text[:120]}"
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None, "Empty candidates"
            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            cleaned = self._clean_sql_codeblock(content)
            return cleaned, None
        except Exception as e:
            return None, str(e)

    def _call_openai_api(
        self,
        query: str,
        mode: str,
        clarification_context: Optional[Dict[str, Any]],
        selected_metric: Optional[str],
        api_key: str,
        base_url: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Invokes OpenAI or OpenAI-compatible (AI credits platform) REST API directly."""
        url = self._get_openai_chat_url(base_url)
        prompt = self._build_llm_prompt(query, mode, clarification_context, selected_metric)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a professional SQLite Text-to-SQL generator. Return ONLY the raw executable SELECT SQL statement without explanation or markdown."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 400
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code}: {resp.text[:120]}"
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            cleaned = self._clean_sql_codeblock(content)
            return cleaned, None
        except Exception as e:
            return None, str(e)

    def _build_llm_prompt(
        self,
        query: str,
        mode: str,
        clarification_context: Optional[Dict[str, Any]],
        selected_metric: Optional[str]
    ) -> str:
        schema = get_schema_summary()
        if mode == "baseline":
            return f"""Translate this business question into a SQLite SELECT query.
{schema}

User Question: "{query}"

Output ONLY the SQL query:"""
        else:
            rule_info = ""
            if clarification_context and clarification_context.get("applied_rules"):
                rule = clarification_context["applied_rules"][0]
                rule_info = f"""
Classification Registry Rule to Enforce:
- Title: {rule.get('title')}
- Primary Metric: {rule.get('primary_metric')}
- Required Filter Condition: {rule.get('filter_conditions')}
- SQL Formula: {rule.get('primary_sql_expression')}
"""
            return f"""You are an enterprise SQLite query synthesizer with strict accounting standards.
{schema}
{rule_info}

Business Query: "{query}"
Generate a safe, read-only SELECT query enforcing the classification rules.
Output ONLY the SQL query:"""

    def _clean_sql_codeblock(self, text: str) -> str:
        s = text.strip()
        # Remove ```sql ... ```
        if "```" in s:
            match = re.search(r"```(?:sql)?\s*(.*?)\s*```", s, re.DOTALL | re.IGNORECASE)
            if match:
                s = match.group(1).strip()
            else:
                s = s.replace("```sql", "").replace("```", "").strip()
        return s.rstrip(";")

    def _generate_baseline_sql(self, query: str) -> Tuple[str, str]:
        q = query.lower()

        # 1. Best / Top Customer queries
        if "best customer" in q or "top customer" in q or "biggest customer" in q:
            if "last month" in q:
                return (
                    """SELECT c.customer_id, c.name, c.email, COUNT(o.order_id) as total_orders, SUM(o.total_amount) as total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE strftime('%m', o.order_date) = '05'
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_spent DESC
LIMIT 5""",
                    "FAILS: Does NOT filter for completed orders (status = 'completed'). Customers with cancelled or unverified transactions erroneously rank at the top."
                )
            else:
                return (
                    """SELECT c.customer_id, c.name, c.email, COUNT(o.order_id) as total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_orders DESC
LIMIT 5""",
                    "FAILS: Arbitrarily assumes 'best' means order count rather than monetary revenue, and ignores order completion status."
                )

        # 2. Top / Best Selling Product queries
        if "top product" in q or "best selling product" in q or "best product" in q:
            if "category" in q or "electronics" in q:
                return (
                    """SELECT p.product_id, p.name, p.category, p.stock_quantity
FROM products p
WHERE p.category = 'Electronics'
ORDER BY p.stock_quantity DESC
LIMIT 5""",
                    "FAILS: Ranks products by inventory stock quantity rather than actual sales transactions."
                )
            return (
                """SELECT p.product_id, p.name, p.category, COUNT(oi.order_item_id) as order_count
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.name, p.category
ORDER BY order_count DESC
LIMIT 5""",
                "FAILS: Ranks by order line item frequency without calculating revenue ($) and without filtering out cancelled/returned orders."
            )

        # 3. Churned customers
        if "churned" in q or "lost customer" in q:
            return (
                """SELECT customer_id, name, email, status, created_at
FROM customers
WHERE status = 'churned'
LIMIT 10""",
                "FAILS: Checks static database column `status = 'churned'`, returning 0 records because churn in reality is behavioral (inactivity in purchasing) rather than an updated CRM flag."
            )

        # 4. Active customers
        if "active customer" in q or "active user" in q or "regular customer" in q:
            return (
                """SELECT customer_id, name, email, status
FROM customers
WHERE status = 'active'
LIMIT 10""",
                "FAILS: Simply queries `status = 'active'`, failing to check whether customers have actually made a purchase recently."
            )

        # 5. VIP customers
        if "vip" in q or "high value customer" in q:
            return (
                """SELECT customer_id, name, email, segment
FROM customers
WHERE segment = 'VIP'
LIMIT 10""",
                "FAILS: Relies on static segment tag, missing high-spend enterprise and SMB customers who have exceeded spending thresholds."
            )

        # 6. Profitable products
        if "profitable product" in q or "highest profit" in q or "highest margin" in q:
            return (
                """SELECT product_id, name, category, price, cost_price,
       ROUND(((price - cost_price) / price) * 100, 2) as margin_percent
FROM products
ORDER BY margin_percent DESC
LIMIT 5""",
                "FAILS: Ranks by percentage margin rather than absolute dollar gross profit, and completely ignores whether the product actually sold."
            )

        # 7. Slow moving / dead inventory
        if "slow moving" in q or "dead stock" in q or "stagnant" in q:
            return (
                """SELECT product_id, name, category, stock_quantity
FROM products
ORDER BY stock_quantity DESC
LIMIT 5""",
                "FAILS: Simply sorts by stock quantity, erroneously flagging popular high-turnover inventory as dead stock."
            )

        # 8. Highest return rate
        if "return rate" in q or "returned" in q:
            return (
                """SELECT p.product_id, p.name,
       ROUND(CAST(SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(o.order_id) * 100, 2) as return_rate
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.name
ORDER BY return_rate DESC
LIMIT 5""",
                "FAILS: Lacks minimum order threshold (HAVING COUNT >= 5). A novelty product purchased once and returned will rank #1 with 100% return rate."
            )

        # 9. Discount impact
        if "discount" in q or "promotion" in q:
            return (
                """SELECT c.customer_id, c.name, SUM(o.discount_amount) as total_discounts
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_discounts DESC
LIMIT 5""",
                "FAILS: Counts discounts on cancelled orders, distorting promotional cost analysis."
            )

        # 10. Temporal last month general
        if "last month" in q:
            return (
                """SELECT COUNT(order_id) as total_orders, SUM(total_amount) as total_sales
FROM orders
WHERE order_date >= date('2005-08-31', '-30 days')""",
                "FAILS: Uses rolling 30-day window instead of closed calendar month, and fails to filter for completed orders."
            )

        # Fallback general query
        return (
            """SELECT order_id, customer_id, order_date, total_amount, status
FROM orders
ORDER BY order_id DESC
LIMIT 10""",
            "FAILS: Unable to infer unguided intent; defaults to arbitrary order list."
        )

    def _generate_guided_sql(
        self,
        query: str,
        clarification_context: Optional[Dict[str, Any]] = None,
        selected_metric: Optional[str] = None
    ) -> Tuple[str, str]:
        q = query.lower()

        # 1. Best Customer
        if "best customer" in q or "top customer" in q or "biggest customer" in q:
            if selected_metric == "order_count":
                date_filter = "AND o.order_date >= '2005-07-01' AND o.order_date <= '2005-07-31'" if "last month" in q else ""
                sql = f"""SELECT c.customer_id, c.name, c.email, c.segment,
       COUNT(DISTINCT o.order_id) as completed_orders,
       ROUND(SUM(o.total_amount), 2) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed' {date_filter}
GROUP BY c.customer_id, c.name, c.email, c.segment
ORDER BY completed_orders DESC
LIMIT 5"""
                return sql, "rule_best_customer (Alternative: Order Count, Completed Status Only)"

            elif selected_metric == "units_purchased":
                date_filter = "AND o.order_date >= '2005-07-01' AND o.order_date <= '2005-07-31'" if "last month" in q else ""
                sql = f"""SELECT c.customer_id, c.name, c.email,
       SUM(oi.quantity) as total_units_purchased,
       ROUND(SUM(o.total_amount), 2) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed' {date_filter}
GROUP BY c.customer_id, c.name, c.email
ORDER BY total_units_purchased DESC
LIMIT 5"""
                return sql, "rule_best_customer (Alternative: Units Purchased)"

            else:
                date_filter = "AND o.order_date >= '2005-07-01' AND o.order_date <= '2005-07-31'" if "last month" in q else ""
                sql = f"""SELECT c.customer_id, c.name, c.email, c.segment,
       ROUND(SUM(o.total_amount), 2) as total_revenue,
       COUNT(DISTINCT o.order_id) as completed_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed' {date_filter}
GROUP BY c.customer_id, c.name, c.email, c.segment
ORDER BY total_revenue DESC
LIMIT 5"""
                return sql, "rule_best_customer (Primary: Total Revenue, Status = 'completed', Closed Calendar Month)"

        # 2. Top Product
        if "top product" in q or "best selling product" in q or "best product" in q:
            if selected_metric == "units_sold":
                cat_filter = "AND p.category = 'Electronics'" if "electronics" in q else ""
                sql = f"""SELECT p.product_id, p.name, p.category,
       SUM(oi.quantity) as total_units_sold,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) as gross_revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed' {cat_filter}
GROUP BY p.product_id, p.name, p.category
ORDER BY total_units_sold DESC
LIMIT 5"""
                return sql, "rule_top_product (Alternative: Units Sold)"
            elif selected_metric == "review_rating":
                sql = """SELECT p.product_id, p.name, p.category,
       ROUND(AVG(pr.rating), 2) as avg_rating,
       COUNT(pr.review_id) as review_count
FROM products p
JOIN product_reviews pr ON p.product_id = pr.product_id
GROUP BY p.product_id, p.name, p.category
HAVING COUNT(pr.review_id) >= 3
ORDER BY avg_rating DESC
LIMIT 5"""
                return sql, "rule_top_product (Alternative: Review Rating)"
            else:
                cat_filter = "AND p.category = 'Electronics'" if "electronics" in q else ""
                sql = f"""SELECT p.product_id, p.name, p.category,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) as total_revenue,
       SUM(oi.quantity) as units_sold
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed' {cat_filter}
GROUP BY p.product_id, p.name, p.category
ORDER BY total_revenue DESC
LIMIT 5"""
                return sql, "rule_top_product (Primary: Total Sales Revenue, Status = 'completed')"

        # 3. Churned Customer
        if "churned" in q or "lost customer" in q or "lapsed" in q:
            sql = """SELECT c.customer_id, c.name, c.email, c.segment,
       MAX(o.order_date) as last_order_date,
       ROUND(JULIANDAY('2005-08-31') - JULIANDAY(MAX(o.order_date))) as days_since_last_order,
       ROUND(SUM(o.total_amount), 2) as historical_spend
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name, c.email, c.segment
HAVING MAX(o.order_date) < date('2005-08-21')
ORDER BY days_since_last_order DESC
LIMIT 10"""
            return sql, "rule_churned_customer (Behavioral Inactivity with Prior Purchases)"

        # 4. Active Customer
        if "active customer" in q or "active user" in q or "regular customer" in q:
            sql = """SELECT c.customer_id, c.name, c.email, c.segment,
       MAX(o.order_date) as recent_order_date,
       COUNT(o.order_id) as recent_orders,
       ROUND(SUM(o.total_amount), 2) as recent_spend
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed' AND o.order_date >= date('2005-08-01')
GROUP BY c.customer_id, c.name, c.email, c.segment
ORDER BY recent_spend DESC
LIMIT 10"""
            return sql, "rule_active_customer (Completed Purchase in Recent Active Window)"

        # 5. VIP Customer
        if "vip" in q or "high value customer" in q or "key account" in q:
            sql = """SELECT c.customer_id, c.name, c.email, c.segment,
       ROUND(SUM(o.total_amount), 2) as lifetime_spend,
       COUNT(o.order_id) as total_completed_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name, c.email, c.segment
HAVING SUM(o.total_amount) >= 150.00
ORDER BY lifetime_spend DESC"""
            return sql, "rule_vip_customer (Lifetime Spend Threshold >= $150)"

        # 6. Profitable Product
        if "profitable product" in q or "highest profit" in q or "highest margin" in q:
            if selected_metric == "margin_percentage":
                sql = """SELECT p.product_id, p.name, p.category, p.price, p.cost_price,
       ROUND(((p.price - p.cost_price) / p.price) * 100, 2) as margin_percentage,
       SUM(oi.quantity) as units_sold
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, p.category, p.price, p.cost_price
HAVING SUM(oi.quantity) >= 5
ORDER BY margin_percentage DESC
LIMIT 5"""
                return sql, "rule_most_profitable_product (Alternative: Margin Percentage with Sales Volume)"
            else:
                sql = """SELECT p.product_id, p.name, p.category,
       ROUND(SUM((oi.unit_price - p.cost_price) * oi.quantity), 2) as total_dollar_profit,
       SUM(oi.quantity) as units_sold,
       ROUND(AVG(((oi.unit_price - p.cost_price) / oi.unit_price) * 100), 1) as avg_margin_pct
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id, p.name, p.category
ORDER BY total_dollar_profit DESC
LIMIT 5"""
                return sql, "rule_most_profitable_product (Primary: Cumulative Gross Dollar Profit)"

        # 7. Slow Moving Inventory
        if "slow moving" in q or "dead stock" in q or "stagnant" in q:
            sql = """SELECT p.product_id, p.name, p.category, p.stock_quantity,
       COALESCE(SUM(CASE WHEN o.order_date >= date('2005-07-01') AND o.status = 'completed' THEN oi.quantity ELSE 0 END), 0) as units_sold_last_60d
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE p.stock_quantity > 0
GROUP BY p.product_id, p.name, p.category, p.stock_quantity
HAVING units_sold_last_60d < 10
ORDER BY p.stock_quantity DESC
LIMIT 5"""
            return sql, "rule_slow_moving_inventory (High Stock and Low Recent Demand)"

        # 8. Highest Return Rate
        if "return rate" in q or "returned" in q:
            sql = """SELECT p.product_id, p.name, p.category,
       COUNT(o.order_id) as total_orders,
       SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) as returned_orders,
       ROUND(CAST(SUM(CASE WHEN o.status = 'returned' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(o.order_id) * 100, 2) as return_percentage
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
GROUP BY p.product_id, p.name, p.category
HAVING COUNT(o.order_id) >= 5
ORDER BY return_percentage DESC
LIMIT 5"""
            return sql, "rule_highest_return_rate (Return % with Minimum 5 Orders Volume Filter)"

        # 9. Discount Impact
        if "discount" in q or "promotion" in q:
            sql = """SELECT c.customer_id, c.name, c.segment,
       ROUND(SUM(o.discount_amount), 2) as total_discount_granted,
       ROUND(SUM(o.total_amount), 2) as net_spent,
       COUNT(o.order_id) as completed_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name, c.segment
ORDER BY total_discount_granted DESC
LIMIT 5"""
            return sql, "rule_discount_impact (Promotional Dollars Granted on Completed Orders)"

        # 10. Temporal Last Month Sales
        if "last month" in q and ("sale" in q or "revenue" in q or "order" in q):
            sql = """SELECT COUNT(order_id) as total_completed_orders,
       ROUND(SUM(total_amount), 2) as total_revenue,
       ROUND(AVG(total_amount), 2) as avg_order_value
FROM orders
WHERE status = 'completed' AND order_date >= '2005-07-01' AND order_date <= '2005-07-31'"""
            return sql, "rule_last_month (July 1 to July 31 Closed Month, Completed Status Only)"

        # Direct / standard query handling
        if "total customers" in q or "count of customers" in q:
            return "SELECT COUNT(*) as total_customers FROM customers", "Direct Control Query"
        if "total orders" in q or "how many orders" in q:
            return "SELECT COUNT(*) as total_orders FROM orders WHERE status = 'completed'", "Direct Control Query (Filtered Completed)"
        if "list all products" in q or "show all products" in q:
            return "SELECT product_id, name, category, price, stock_quantity FROM products LIMIT 20", "Direct Control Query"
        if "department" in q:
            return "SELECT dept_no, dept_name FROM departments", "Direct Control Query (Departments)"

        # Default fallback
        return """SELECT order_id, customer_id, order_date, total_amount, status
FROM orders
WHERE status = 'completed'
ORDER BY order_date DESC
LIMIT 10""", "Standard Guided Query"
