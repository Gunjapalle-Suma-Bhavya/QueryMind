import re
from typing import Dict, List, Any, Optional

# Lexicon patterns for ambiguity detection
SUPERLATIVE_PATTERNS = [
    (r"\b(best|top|leading|champion)\b", "superlative_high"),
    (r"\b(worst|lowest|bottom|underperforming|poorest)\b", "superlative_low"),
    (r"\b(highest|most)\b", "superlative_generic"),
]

TEMPORAL_PATTERNS = [
    (r"\b(last\s+month|previous\s+month)\b", "last_month"),
    (r"\b(recent|recently|lately)\b", "recent"),
    (r"\b(this\s+month|current\s+month)\b", "this_month"),
    (r"\b(last\s+quarter|previous\s+quarter|q[1-4])\b", "quarter"),
    (r"\b(inactive\s+period|long\s+time)\b", "temporal_gap"),
]

STATUS_PATTERNS = [
    (r"\b(churned|churn|lost\s+customer|lapsed)\b", "churned_customer"),
    (r"\b(active|active\s+customer|regular)\b", "active_customer"),
    (r"\b(vip|high\s+value|valuable|key\s+account)\b", "vip_customer"),
    (r"\b(dead\s+stock|slow\s+moving|stagnant)\b", "slow_moving_inventory"),
]

METRIC_PATTERNS = [
    (r"\b(sales|performance)\b", "sales_performance"),
    (r"\b(profitable|profit|margin)\b", "most_profitable_product"),
    (r"\b(return\s+rate|returns|returned)\b", "highest_return_rate"),
    (r"\b(discount|promotion|discounted)\b", "discount_impact"),
]

class AmbiguityDetector:
    def __init__(self):
        pass

    def analyze(self, query: str) -> Dict[str, Any]:
        """
        Scans a natural language query and detects semantic ambiguities.
        Returns a structured assessment including ambiguity score, matched concepts,
        and explanations of why the query is ambiguous.
        """
        text = query.lower().strip()
        matched_rules: List[str] = []
        detected_categories: List[str] = []
        reasons: List[str] = []

        # 1. Check Superlative Ambiguity
        has_superlative = False
        for pattern, kind in SUPERLATIVE_PATTERNS:
            if re.search(pattern, text):
                has_superlative = True
                detected_categories.append("superlative")
                break

        # Check entity context for superlatives
        is_customer_query = bool(re.search(r"\b(customer|client|buyer|user|account)\b", text))
        is_product_query = bool(re.search(r"\b(product|item|good|sku|category)\b", text))

        if has_superlative and is_customer_query:
            matched_rules.append("best_customer")
            reasons.append(
                "Superlative 'best customer' is ambiguous: Does 'best' mean highest monetary revenue ($), "
                "highest order frequency (count), or largest quantity of physical units purchased?"
            )
        elif has_superlative and is_product_query:
            if re.search(r"\b(profit|margin|earning)\b", text):
                matched_rules.append("most_profitable_product")
                reasons.append(
                    "Metric 'most profitable' is ambiguous: Rank by absolute gross dollar margin ($) "
                    "or by gross margin percentage (%)?"
                )
            elif re.search(r"\b(worst|underperforming|slow|dead)\b", text):
                matched_rules.append("slow_moving_inventory")
                reasons.append(
                    "Metric 'underperforming product' is ambiguous: Does it signify low sales volume, "
                    "dead warehouse stock, or low customer review ratings?"
                )
            else:
                matched_rules.append("top_product")
                reasons.append(
                    "Superlative 'top product' is ambiguous: Does 'top' refer to total dollar sales volume ($), "
                    "raw unit quantity sold, or average customer review rating?"
                )

        # 2. Check Temporal Ambiguity
        for pattern, kind in TEMPORAL_PATTERNS:
            if re.search(pattern, text):
                detected_categories.append("temporal")
                if kind == "last_month":
                    matched_rules.append("last_month")
                    reasons.append(
                        "Temporal term 'last month' is ambiguous: Should reporting aggregate the closed calendar "
                        "month (e.g., May 1st-31st) or a trailing rolling 30-day window?"
                    )
                elif kind == "recent":
                    reasons.append(
                        "Temporal term 'recent' is undefined: Specifies no bounded date range (7 days? 30 days? 90 days?)."
                    )
                break

        # 3. Check Lifecycle & Status Ambiguity
        for pattern, rule_alias in STATUS_PATTERNS:
            if re.search(pattern, text):
                detected_categories.append("lifecycle")
                if rule_alias not in matched_rules:
                    matched_rules.append(rule_alias)
                if rule_alias == "churned_customer":
                    reasons.append(
                        "Status 'churned customer' is ambiguous: Is churn determined by explicit CRM database flag, "
                        "or behaviorally by 90+ days without a completed purchase?"
                    )
                elif rule_alias == "active_customer":
                    reasons.append(
                        "Status 'active customer' is ambiguous: Does active imply an account status flag, "
                        "or at least one completed transaction in the past 60 days?"
                    )
                elif rule_alias == "vip_customer":
                    reasons.append(
                        "Classification 'VIP customer' has no qualification defined: Should eligibility require "
                        "$2,000+ lifetime completed spend, high order count, or explicit segment labeling?"
                    )
                elif rule_alias == "slow_moving_inventory":
                    reasons.append(
                        "Classification 'slow-moving inventory' is ambiguous: What is the threshold for excess stock "
                        "relative to low sales velocity?"
                    )

        # 4. Check Financial Semantics Ambiguity
        for pattern, rule_alias in METRIC_PATTERNS:
            if re.search(pattern, text):
                if rule_alias not in matched_rules:
                    matched_rules.append(rule_alias)
                    detected_categories.append("financial")
                if rule_alias == "highest_return_rate":
                    reasons.append(
                        "Metric 'return rate' lacks statistical sample threshold: Should single-order items with 1 return (100%) "
                        "be filtered by a minimum order volume (e.g., >= 5 orders)?"
                    )
                elif rule_alias == "discount_impact":
                    reasons.append(
                        "Metric 'discount impact' is ambiguous: Refers to gross promotional dollar loss or percentage discount rate?"
                    )

        # Remove duplicates
        matched_rules = list(dict.fromkeys(matched_rules))
        detected_categories = list(dict.fromkeys(detected_categories))

        # Check explicit metric qualification
        # If user explicitly specifies e.g. "by revenue", ambiguity drops
        explicit_metric_overridden = False
        if re.search(r"\b(by\s+revenue|by\s+sales\s+amount|by\s+dollar|by\s+quantity|by\s+units|by\s+rating)\b", text):
            explicit_metric_overridden = True

        ambiguity_score = 0.0
        if reasons:
            base_score = min(1.0, len(reasons) * 0.35 + (0.3 if has_superlative else 0.1))
            ambiguity_score = round(base_score if not explicit_metric_overridden else base_score * 0.4, 2)

        is_ambiguous = ambiguity_score >= 0.35

        return {
            "query": query,
            "is_ambiguous": is_ambiguous,
            "ambiguity_score": ambiguity_score,
            "detected_categories": detected_categories,
            "matched_rules": matched_rules,
            "reasons": reasons,
            "explicit_metric_overridden": explicit_metric_overridden
        }

if __name__ == "__main__":
    detector = AmbiguityDetector()
    samples = [
        "Show me last month's best customer",
        "Who is our top product?",
        "List all churned customers",
        "Which product has the highest return rate?",
        "How many total orders are in the database?",
        "Show me best customer by revenue in May 2024"
    ]
    for s in samples:
        res = detector.analyze(s)
        print(f"Query: '{s}' -> Ambiguous: {res['is_ambiguous']} (Score: {res['ambiguity_score']}) Rules: {res['matched_rules']}")
