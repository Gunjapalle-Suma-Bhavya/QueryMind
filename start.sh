#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " 🚀 QueryMind Enterprise Text-to-SQL System"
echo "=========================================================="

# 1. Sync Configuration Files (.env and env.config)
if [ ! -f "env.config" ]; then
    if [ -f ".env" ]; then
        cp .env env.config
    elif [ -f ".env.example" ]; then
        cp .env.example env.config
        cp .env.example .env
    fi
fi
[ -f "env.config" ] && [ ! -f ".env" ] && cp env.config .env
[ -f "env.config" ] && cp env.config backend/.env 2>/dev/null || true

# 2. Check Python Virtual Environment
if [ ! -d "backend/venv" ]; then
    echo "[1/3] Creating Python virtual environment and installing dependencies..."
    python3 -m venv backend/venv
    ./backend/venv/bin/pip install --upgrade pip
    ./backend/venv/bin/pip install -r backend/requirements.txt
fi

# 3. Verify Database
echo "[2/3] Verifying database schema (from test_db-master)..."
PYTHONPATH=. ./backend/venv/bin/python -c "from backend.database.db_manager import init_db; init_db()"

# 4. Verify Frontend Build
if [ ! -d "frontend/dist" ] || [ ! -f "frontend/dist/index.html" ]; then
    echo "[3/3] Building frontend assets..."
    cd frontend && npm install && npm run build && cd ..
fi

echo "=========================================================="
echo " ✅ All checks passed! Starting QueryMind..."
echo " 🌐 Web UI & API live at: http://localhost:8000"
echo " 🔑 Config file: $DIR/env.config or UI Settings dialog"
echo " (Press CTRL+C to stop)"
echo "=========================================================="

PYTHONPATH=. ./backend/venv/bin/python run.py
