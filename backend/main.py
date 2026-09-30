import os
import sys

# Ensure project root is in sys.path so 'backend' package imports work from any working directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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

from backend.database.db_manager import (
    init_db,
    execute_query,
    get_db_connection,
    get_schema_summary
)
from backend.engine.clarification_engine import ClarificationEngine
from backend.engine.sql_generator import SQLGenerator
from backend.engine.nl_synthesizer import NLSynthesizer
from backend.benchmark.benchmark_runner import BenchmarkRunner

# Initialize Database on startup
init_db()

app = FastAPI(
    title="QueryMind: English-to-SQL Clarification Engine API",
    description="Enterprise Text-to-SQL system with semantic ambiguity detection, classification rules, and 50-query failure benchmark.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clarification_engine = ClarificationEngine()
sql_generator = SQLGenerator()
nl_synthesizer = NLSynthesizer()
benchmark_runner = BenchmarkRunner()

class QueryRequest(BaseModel):
    query: str
    mode: str = "guided"  # 'guided' or 'baseline'
    selected_metric: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    llm_provider: Optional[str] = None

class TestKeyRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None

def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "********"
    return key[:4] + "..." + key[-4:]

def _update_env_files(
    gemini_key: Optional[str] = None,
    openai_key: Optional[str] = None,
    openai_base_url: Optional[str] = None,
    provider: Optional[str] = None
):
    current_gemini = os.getenv("GEMINI_API_KEY", "")
    current_openai = os.getenv("OPENAI_API_KEY", "")
    current_openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    current_provider = os.getenv("LLM_PROVIDER", "auto")

    new_gemini = gemini_key.strip() if gemini_key is not None else current_gemini
    new_openai = openai_key.strip() if openai_key is not None else current_openai
    new_openai_base = openai_base_url.strip() if openai_base_url is not None else current_openai_base
    if not new_openai_base:
        new_openai_base = "https://api.openai.com/v1"
    new_provider = provider.strip().lower() if provider is not None else current_provider

    content = f"""# ==========================================================
# QueryMind Environment Configuration
# ==========================================================
# Note: You can edit this file or set keys directly in the Web UI.

# 1. Google Gemini API Key
# Get your API key from https://aistudio.google.com/app/apikey
GEMINI_API_KEY={new_gemini}

# 2. OpenAI API Key & Custom Base URL (for AI Credits Platform / Relays)
# Standard OpenAI: https://api.openai.com/v1
# AI Credits Platform: Use your custom provider base URL and API key
OPENAI_API_KEY={new_openai}
OPENAI_BASE_URL={new_openai_base}

# 3. Preferred LLM Provider: 'auto', 'gemini', 'openai', or 'semantic_engine'
# - 'auto': Uses Gemini if key present, else OpenAI, else built-in semantic engine
# - 'gemini': Explicitly calls Gemini API (gemini-1.5-flash)
# - 'openai': Explicitly calls OpenAI-compatible API using OPENAI_BASE_URL (gpt-4o-mini)
# - 'semantic_engine': High-speed deterministic engine (works offline with 0 keys)
LLM_PROVIDER={new_provider}

# 4. Server Configuration
PORT=8000
HOST=0.0.0.0
"""
    for target in [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(PROJECT_ROOT, "env.config"),
        os.path.join(PROJECT_ROOT, "backend", ".env")
    ]:
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Warning: could not write {target}: {e}")

    if gemini_key is not None:
        os.environ["GEMINI_API_KEY"] = new_gemini
    if openai_key is not None:
        os.environ["OPENAI_API_KEY"] = new_openai
    if openai_base_url is not None:
        os.environ["OPENAI_BASE_URL"] = new_openai_base
    if provider is not None:
        os.environ["LLM_PROVIDER"] = new_provider

    sql_generator._refresh_keys()

class ClassificationRulePayload(BaseModel):
    rule_id: str
    category: str
    term_alias: str
    title: str
    description: str
    primary_metric: str
    primary_sql_expression: str
    filter_conditions: str
    alternative_metrics: List[Dict[str, Any]]
    temporal_interpretation: Optional[str] = ""
    rationale: str
    why_baseline_fails: str

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "text-to-sql-clarification-engine", "version": "1.0.0"}

@app.get("/api/config")
def get_system_config():
    sql_generator._refresh_keys()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_base_url = (os.getenv("OPENAI_BASE_URL", "") or os.getenv("OPENAI_API_BASE", "") or "https://api.openai.com/v1").strip()
    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()

    active_desc = "Built-in Semantic Engine (100% Offline / Zero-Setup)"
    if provider == "gemini" and gemini_key:
        active_desc = "Google Gemini (gemini-1.5-flash)"
    elif provider == "openai" and openai_key:
        if "api.openai.com" in openai_base_url:
            active_desc = "OpenAI (gpt-4o-mini)"
        else:
            active_desc = f"OpenAI Compatible AI Credits ({openai_base_url})"
    elif provider == "auto":
        if gemini_key:
            active_desc = "Google Gemini (gemini-1.5-flash) [Auto]"
        elif openai_key:
            if "api.openai.com" in openai_base_url:
                active_desc = "OpenAI (gpt-4o-mini) [Auto]"
            else:
                active_desc = f"OpenAI Compatible AI Credits ({openai_base_url}) [Auto]"
        else:
            active_desc = "Built-in Semantic Engine (Offline Fallback)"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        cust_cnt = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders")
        ord_cnt = cursor.fetchone()[0]
    except Exception:
        cust_cnt = 0
        ord_cnt = 0
    finally:
        conn.close()

    return {
        "has_gemini_key": bool(gemini_key),
        "has_openai_key": bool(openai_key),
        "gemini_masked_key": _mask_key(gemini_key),
        "openai_masked_key": _mask_key(openai_key),
        "openai_base_url": openai_base_url,
        "active_provider": provider,
        "active_model_desc": active_desc,
        "database_connected": True,
        "customer_count": cust_cnt,
        "order_count": ord_cnt,
        "env_file_location": os.path.join(PROJECT_ROOT, ".env"),
        "visible_config_file": os.path.join(PROJECT_ROOT, "env.config")
    }

@app.post("/api/config")
def update_system_config(req: ConfigUpdateRequest):
    _update_env_files(
        gemini_key=req.gemini_api_key,
        openai_key=req.openai_api_key,
        openai_base_url=req.openai_base_url,
        provider=req.llm_provider
    )
    return {
        "status": "success",
        "message": "Configuration updated successfully and saved to .env and env.config."
    }

@app.post("/api/test-key")
def test_key(req: TestKeyRequest):
    success, message = sql_generator.test_connection(req.provider, req.api_key, base_url=req.base_url)
    return {"success": success, "message": message}

@app.post("/api/query")
def process_user_query(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    # 1. Ambiguity & Clarification Analysis
    clarification_result = clarification_engine.process(req.query, selected_metric=req.selected_metric)

    # 2. SQL Generation (Baseline vs Guided)
    try:
        gen_result = sql_generator.generate_sql(
            query=req.query,
            mode=req.mode,
            clarification_context=clarification_result,
            selected_metric=req.selected_metric
        )
        sql = gen_result["sql"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL Generation Error: {str(e)}")

    # 3. Database Execution
    try:
        db_res = execute_query(sql)
    except Exception as e:
        return {
            "query": req.query,
            "conversational_answer": f"The query encountered a database execution error: {str(e)}",
            "data": [],
            "columns": [],
            "row_count": 0,
            "clarification": clarification_result,
            "execution_details": {
                "sql": sql,
                "execution_time_ms": 0,
                "error": str(e),
                "mode": req.mode
            }
        }

    # 4. Natural Language Answer Synthesis (Executive summary, SQL hidden)
    conversational_answer = nl_synthesizer.synthesize(
        query=req.query,
        query_result=db_res,
        clarification_context=clarification_result,
        mode=req.mode
    )

    model_name = gen_result.get("model_used", "Built-in Semantic Engine")

    return {
        "query": req.query,
        "conversational_answer": conversational_answer,
        "data": db_res["results"],
        "columns": db_res["columns"],
        "row_count": db_res["row_count"],
        "clarification": clarification_result,
        "model_used": model_name,
        "execution_details": {
            "sql": sql,
            "execution_time_ms": db_res["execution_time_ms"],
            "rule_applied": gen_result.get("classification_rule", "None"),
            "mode": req.mode,
            "baseline_vulnerability": gen_result.get("baseline_vulnerability", ""),
            "model_used": model_name
        }
    }

@app.get("/api/classification-rules")
def list_classification_rules():
    """Returns all enterprise classification rules from database."""
    return clarification_engine.get_all_rules()

@app.post("/api/classification-rules")
def save_classification_rule(payload: ClassificationRulePayload):
    """Creates or updates a classification rule in the registry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO metric_classification_rules (
                rule_id, category, term_alias, title, description,
                primary_metric, primary_sql_expression, filter_conditions,
                alternative_metrics, temporal_interpretation, rationale, why_baseline_fails
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.rule_id,
            payload.category,
            payload.term_alias,
            payload.title,
            payload.description,
            payload.primary_metric,
            payload.primary_sql_expression,
            payload.filter_conditions,
            json.dumps(payload.alternative_metrics),
            payload.temporal_interpretation,
            payload.rationale,
            payload.why_baseline_fails
        ))
        conn.commit()
        return {"status": "success", "rule_id": payload.rule_id}
    finally:
        conn.close()

@app.post("/api/benchmark/run")
def run_benchmark():
    """Triggers the full 50-query benchmark evaluation."""
    return benchmark_runner.run_all()

@app.get("/api/benchmark/results")
def get_benchmark_results():
    """Retrieves cached benchmark evaluation statistics."""
    return benchmark_runner.get_cached_results()

@app.get("/api/schema")
def get_schema():
    """Returns relational schema structure and reference guidelines."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row["name"] for row in cursor.fetchall()]

        schema_details = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [dict(c) for c in cursor.fetchall()]
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cursor.fetchone()["cnt"]
            schema_details[table] = {
                "columns": cols,
                "row_count": cnt
            }

        return {
            "tables": schema_details,
            "summary_text": get_schema_summary()
        }
    finally:
        conn.close()

# Mount frontend production build if available
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(FRONTEND_DIST):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting QueryMind backend server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)

