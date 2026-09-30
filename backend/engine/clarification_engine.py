import json
import sqlite3
from typing import Dict, List, Any, Optional
from backend.database.db_manager import get_db_connection
from backend.engine.ambiguity_detector import AmbiguityDetector

class ClarificationEngine:
    def __init__(self):
        self.detector = AmbiguityDetector()

    def get_rule_from_db(self, term_alias: str) -> Optional[Dict[str, Any]]:
        """Retrieves an enterprise classification rule by term alias."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metric_classification_rules WHERE term_alias = ?", (term_alias,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            try:
                res["alternative_metrics"] = json.loads(res["alternative_metrics"])
            except Exception:
                pass
            return res
        finally:
            conn.close()

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Retrieves all active enterprise classification rules."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metric_classification_rules ORDER BY category, title")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["alternative_metrics"] = json.loads(item["alternative_metrics"])
                except Exception:
                    pass
                results.append(item)
            return results
        finally:
            conn.close()

    def process(self, query: str, selected_metric: Optional[str] = None) -> Dict[str, Any]:
        """
        Detects ambiguity, binds against classification rules, and generates clarification metadata.
        """
        analysis = self.detector.analyze(query)
        matched_rules = analysis["matched_rules"]

        applied_rules: List[Dict[str, Any]] = []
        for alias in matched_rules:
            rule = self.get_rule_from_db(alias)
            if rule:
                applied_rules.append(rule)

        clarification_required = analysis["is_ambiguous"] and len(applied_rules) > 0
        primary_rule = applied_rules[0] if applied_rules else None

        # Build interactive clarification options
        options = []
        if primary_rule and isinstance(primary_rule.get("alternative_metrics"), list):
            for alt in primary_rule["alternative_metrics"]:
                is_active = False
                if selected_metric:
                    is_active = (alt.get("key") == selected_metric)
                else:
                    # Default is the first alternative or 'revenue' / primary key
                    is_active = (alt.get("key") in ("revenue", "calendar_month", "90d_inactivity", "spend_2000", "dead_stock", "rate_with_threshold", primary_rule["alternative_metrics"][0].get("key")))

                options.append({
                    "key": alt.get("key"),
                    "label": alt.get("label"),
                    "description": alt.get("desc") or alt.get("sql", ""),
                    "is_active": is_active,
                    "sql": alt.get("sql", ""),
                    "filter": alt.get("filter", "")
                })

        # Clarification prompt for end-user visibility
        clarification_message = ""
        if clarification_required and primary_rule:
            active_opt = next((o for o in options if o["is_active"]), None)
            active_label = active_opt["label"] if active_opt else primary_rule["primary_metric"]
            clarification_message = (
                f"Resolved using Enterprise Classification Registry: Classified based on {active_label}. "
                f"You can choose an alternative interpretation below."
            )

        return {
            "query": query,
            "is_ambiguous": analysis["is_ambiguous"],
            "ambiguity_score": analysis["ambiguity_score"],
            "reasons": analysis["reasons"],
            "applied_rules": applied_rules,
            "primary_rule": primary_rule,
            "options": options,
            "selected_metric": selected_metric,
            "clarification_message": clarification_message
        }

if __name__ == "__main__":
    engine = ClarificationEngine()
    test_res = engine.process("Show me last month's best customer")
    print("Clarification Process Output:")
    print("Is Ambiguous:", test_res["is_ambiguous"])
    print("Reasons:", test_res["reasons"])
    print("Clarification Message:", test_res["clarification_message"])
    print("Options:", test_res["options"])
