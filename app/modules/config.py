"""config.py - centralized configuration.

Keeps model names and file paths in one place so they can be changed
without touching agent logic (for example, swapping the chat model).
Values are read from the environment (.env) with sensible defaults.

Phase 0: only paths and model-name defaults are declared. Nothing here
performs I/O at import time, so importing this module is always safe.
"""

import os
from pathlib import Path

# Project root = two levels up from this file (app/modules/config.py).
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Data locations (created/populated in later phases).
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"            # Chroma persistent vector store.
SQLITE_DB_PATH = DATA_DIR / "tech.db"       # SQLite scheduling database.

# Model names. Overridable via .env so they can be changed in one place.
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
