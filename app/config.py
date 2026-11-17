from __future__ import annotations
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# Load the project-root .env explicitly. This file is next to README.md and
# .env.example, not inside app/ or scripts/.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=False)
except Exception:
    # Shell environment variables still work when python-dotenv is unavailable.
    pass

PRACTICE_DATA_DIR = BASE_DIR / "practice_data"
STORAGE_DIR = BASE_DIR / "storage"
FRONTEND_DIR = BASE_DIR / "frontend"
DEFAULT_AS_OF_DATE = os.getenv("DEFAULT_AS_OF_DATE", "2026-11-15")

# Accept the app's canonical names as well as common provider-specific names.
# For Groq, sensible OpenAI-compatible defaults are supplied when only
# GROQ_API_KEY is present. Explicit LLM_* values always take precedence.
_groq_key = os.getenv("GROQ_API_KEY", "").strip()
_openai_key = os.getenv("OPENAI_API_KEY", "").strip()
LLM_API_KEY = (os.getenv("LLM_API_KEY", "").strip() or _groq_key or _openai_key)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

if _groq_key:
    LLM_BASE_URL = LLM_BASE_URL or "https://api.groq.com/openai/v1"
    LLM_MODEL = LLM_MODEL or "openai/gpt-oss-120b"
elif _openai_key:
    LLM_BASE_URL = LLM_BASE_URL or "https://api.openai.com/v1"

# Treat common copy/paste placeholders as missing configuration.
if LLM_API_KEY.lower() in {"your_api_key", "your_actual_api_key", "paste_api_key_here", "changeme"}:
    LLM_API_KEY = ""

EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "auto").strip().lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2").strip()
DATASETS = {
    "nimbus_8": PRACTICE_DATA_DIR / "data",
    "nimbus_40": PRACTICE_DATA_DIR / "data_scale_40",
}

LLM_MISSING_SETTINGS = [
    name for name, value in (
        ("LLM_API_KEY (or GROQ_API_KEY / OPENAI_API_KEY)", LLM_API_KEY),
        ("LLM_BASE_URL", LLM_BASE_URL),
        ("LLM_MODEL", LLM_MODEL),
    ) if not value
]
LLM_CONFIGURED = not LLM_MISSING_SETTINGS
