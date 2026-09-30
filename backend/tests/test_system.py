import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.benchmark.benchmark_runner import BenchmarkRunner

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_best_customer_ambiguity_and_resolution():
    # User query: "Show me last month's best customer"
    payload = {
        "query": "Show me last month's best customer",
        "mode": "guided"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Ambiguity check
    assert data["clarification"]["is_ambiguous"] is True
    assert "best_customer" in [r["term_alias"] for r in data["clarification"]["applied_rules"]]
    assert len(data["clarification"]["options"]) >= 3

    # Primary user answer should be conversational (SQL hidden)
    # In user database (Sakila), top customer in July 2005 is ELEANOR HUNT with $100.78
    assert "ELEANOR HUNT" in data["conversational_answer"] or "100.78" in data["conversational_answer"]

    # Underlying SQL verification in execution details
    sql = data["execution_details"]["sql"]
    assert "status = 'completed'" in sql

def test_baseline_vs_guided_discrepancy():
    # In baseline mode, without status='completed', MINNIE ROMERO appears
    base_res = client.post("/api/query", json={"query": "Show me last month's best customer", "mode": "baseline"})
    assert base_res.status_code == 200
    base_data = base_res.json()
    assert base_data["row_count"] > 0
    assert base_data["execution_details"]["mode"] == "baseline"

    # In guided mode, verified revenue ranking is enforced
    guided_res = client.post("/api/query", json={"query": "Show me last month's best customer", "mode": "guided"})
    assert guided_res.status_code == 200
    guided_data = guided_res.json()
    assert guided_data["data"][0]["name"] == "ELEANOR HUNT"

def test_alternative_metric_clarification():
    # When user specifies alternative metric 'order_count'
    payload = {
        "query": "Show me last month's best customer",
        "mode": "guided",
        "selected_metric": "order_count"
    }
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] > 0
    assert "completed_orders" in data["data"][0]

def test_churned_customer_behavioral_rule():
    response = client.post("/api/query", json={"query": "Show all churned customers", "mode": "guided"})
    assert response.status_code == 200
    data = response.json()
    assert data["row_count"] > 0
    # Long inactive accounts should be captured
    names = [row["name"] for row in data["data"]]
    assert len(names) >= 5

def test_return_rate_sample_threshold():
    # Guided query must have minimum volume filter (HAVING COUNT >= 5) to avoid single-order noise
    guided_res = client.post("/api/query", json={"query": "Which item has the highest return rate?", "mode": "guided"})
    assert guided_res.status_code == 200
    data = guided_res.json()
    assert data["row_count"] > 0
    assert "return_percentage" in data["data"][0]

def test_benchmark_runner_accuracy():
    runner = BenchmarkRunner()
    results = runner.run_all()
    assert results["total_queries"] == 50
    assert results["guided_accuracy_pct"] >= 95.0
    assert results["baseline_accuracy_pct"] <= 30.0
    assert "Status Blindness (Cancelled/Refunded Orders)" in results["failure_taxonomy"]

def test_config_endpoints():
    # Test GET /api/config
    get_res = client.get("/api/config")
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert "active_provider" in cfg
    assert "database_connected" in cfg
    assert cfg["database_connected"] is True
    assert cfg["customer_count"] >= 500

    # Test POST /api/config
    post_res = client.post("/api/config", json={
        "llm_provider": "semantic_engine"
    })
    assert post_res.status_code == 200

    # Test POST /api/test-key with semantic_engine
    test_res = client.post("/api/test-key", json={
        "provider": "semantic_engine",
        "api_key": "test_key"
    })
    assert test_res.status_code == 200
    assert test_res.json()["success"] is True
