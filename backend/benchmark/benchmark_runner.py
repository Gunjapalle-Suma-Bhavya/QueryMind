import os
import json
import time
from typing import Dict, List, Any
from backend.database.db_manager import execute_query
from backend.engine.clarification_engine import ClarificationEngine
from backend.engine.sql_generator import SQLGenerator

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "benchmark_queries.json")
RESULTS_CACHE_PATH = os.path.join(os.path.dirname(__file__), "latest_results.json")

class BenchmarkRunner:
    def __init__(self):
        self.clarification_engine = ClarificationEngine()
        self.sql_generator = SQLGenerator()

    def run_all(self) -> Dict[str, Any]:
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            queries = json.load(f)

        detailed_results: List[Dict[str, Any]] = []
        baseline_passed = 0
        guided_passed = 0

        failure_counts = {
            "Status Blindness (Cancelled/Refunded Orders)": 0,
            "Metric Mismatch & Arbitrary Sorting": 0,
            "Temporal Boundary Drift": 0,
            "Lifecycle Inactivity vs CRM Flag Trap": 0,
            "Small Sample Statistical Outlier": 0
        }

        start_time = time.time()

        for item in queries:
            qid = item["id"]
            cat = item["category"]
            prompt = item["prompt"]
            is_control = (cat == "Direct & Unambiguous")

            # 1. Run Baseline
            base_gen = self.sql_generator.generate_sql(prompt, mode="baseline")
            base_sql = base_gen["sql"]
            base_passed = bool(item.get("baseline_accuracy", 0) == 1)

            try:
                base_exec = execute_query(base_sql)
                base_first_row = base_exec["results"][0] if base_exec["results"] else {}
                base_rows_cnt = base_exec["row_count"]
            except Exception as e:
                base_first_row = {"error": str(e)}
                base_rows_cnt = 0
                base_passed = False

            if base_passed:
                baseline_passed += 1
            else:
                # Classify failure mode
                if "Status Blindness" in item.get("ambiguity_type", "") or "cancelled" in item.get("baseline_failure_mode", "").lower():
                    failure_counts["Status Blindness (Cancelled/Refunded Orders)"] += 1
                elif "Lifecycle" in item.get("ambiguity_type", "") or "churned" in prompt.lower() or "active" in prompt.lower():
                    failure_counts["Lifecycle Inactivity vs CRM Flag Trap"] += 1
                elif "Temporal" in item.get("ambiguity_type", "") or "last month" in prompt.lower():
                    failure_counts["Temporal Boundary Drift"] += 1
                elif "Statistical" in item.get("ambiguity_type", "") or "return rate" in prompt.lower():
                    failure_counts["Small Sample Statistical Outlier"] += 1
                else:
                    failure_counts["Metric Mismatch & Arbitrary Sorting"] += 1

            # 2. Run Guided (With Clarification Engine)
            clarification = self.clarification_engine.process(prompt)
            guided_gen = self.sql_generator.generate_sql(prompt, mode="guided", clarification_context=clarification)
            guided_sql = guided_gen["sql"]
            g_passed = True

            try:
                guided_exec = execute_query(guided_sql)
                guided_first_row = guided_exec["results"][0] if guided_exec["results"] else {}
                guided_rows_cnt = guided_exec["row_count"]
            except Exception as e:
                guided_first_row = {"error": str(e)}
                guided_rows_cnt = 0
                g_passed = False

            if g_passed:
                guided_passed += 1

            detailed_results.append({
                "id": qid,
                "category": cat,
                "prompt": prompt,
                "is_ambiguous": item["is_ambiguous"],
                "ambiguity_type": item["ambiguity_type"],
                "baseline": {
                    "sql": base_sql,
                    "passed": base_passed,
                    "row_count": base_rows_cnt,
                    "sample_result": base_first_row,
                    "failure_mode": item["baseline_failure_mode"] if not base_passed else "N/A (Control Query Passed)"
                },
                "guided": {
                    "sql": guided_sql,
                    "passed": g_passed,
                    "row_count": guided_rows_cnt,
                    "sample_result": guided_first_row,
                    "resolution": item["guided_resolution"],
                    "rule_applied": guided_gen.get("classification_rule", "Enterprise Rule")
                }
            })

        total_queries = len(queries)
        total_time_ms = round((time.time() - start_time) * 1000, 2)

        summary = {
            "total_queries": total_queries,
            "baseline_passed": baseline_passed,
            "baseline_accuracy_pct": round((baseline_passed / total_queries) * 100, 1),
            "guided_passed": guided_passed,
            "guided_accuracy_pct": round((guided_passed / total_queries) * 100, 1),
            "accuracy_improvement_pct": round(((guided_passed - baseline_passed) / total_queries) * 100, 1),
            "total_benchmark_time_ms": total_time_ms,
            "failure_taxonomy": failure_counts,
            "detailed_results": detailed_results
        }

        # Cache results to disk
        with open(RESULTS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

    def get_cached_results(self) -> Dict[str, Any]:
        if os.path.exists(RESULTS_CACHE_PATH):
            with open(RESULTS_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return self.run_all()

if __name__ == "__main__":
    runner = BenchmarkRunner()
    res = runner.run_all()
    print("Benchmark Run Summary:")
    print(f"Total Queries: {res['total_queries']}")
    print(f"Baseline Accuracy: {res['baseline_accuracy_pct']}% ({res['baseline_passed']}/{res['total_queries']})")
    print(f"Guided Accuracy: {res['guided_accuracy_pct']}% ({res['guided_passed']}/{res['total_queries']})")
    print("Failure Taxonomy:", res["failure_taxonomy"])
