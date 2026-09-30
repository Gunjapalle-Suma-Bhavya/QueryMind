#!/usr/bin/env python3
"""
=============================================================================
QueryMind - Enterprise Text-to-SQL Clarification Engine
=============================================================================
Start both backend API and frontend single-page application on one single port:
    python run.py
=============================================================================
"""
import os
import sys

# Ensure root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uvicorn
from backend.main import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print("=" * 65)
    print(f"🚀 QueryMind Enterprise Server starting at http://localhost:{port}")
    print(f"📡 API Health: http://localhost:{port}/api/health")
    print(f"⚙️  API Config: http://localhost:{port}/api/config")
    print(f"💻 Web App UI: http://localhost:{port}")
    print("=" * 65)
    uvicorn.run(app, host=host, port=port)
