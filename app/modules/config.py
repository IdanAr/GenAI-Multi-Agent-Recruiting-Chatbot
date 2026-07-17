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
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4.1-2025-04-14")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Input files used by the app at run time. These are tracked copies of the
# course-provided data, kept under data/inputs/ so a clean clone is reproducible
# (the original Instructions/ folder is git-ignored).
INPUTS_DIR = DATA_DIR / "inputs"
SCHEDULE_SQL_PATH = INPUTS_DIR / "SQL_DB" / "schedule_seed.sql"
JOB_DESCRIPTION_PDF = INPUTS_DIR / "job_description.pdf"
CONVERSATIONS_JSON = INPUTS_DIR / "sms_conversations.json"

# Chroma collection name for the embedded job description.
CHROMA_COLLECTION = "job_description"
