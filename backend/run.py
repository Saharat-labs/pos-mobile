#!/usr/bin/env python3
"""Run script for POS-MOBILE Backend."""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load .env if exists
env_file = backend_dir / ".env"
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    # Ensure data directory exists
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📁 Data dir: {settings.DATA_DIR}")
    print(f"🌐 Server: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 Docs: http://{settings.HOST}:{settings.PORT}/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )