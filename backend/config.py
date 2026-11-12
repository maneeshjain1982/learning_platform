"""Settings, read from environment variables (all optional)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("STUDY_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_URL = os.environ.get("STUDY_DB_URL", f"sqlite:///{(DATA_DIR / 'study.db').as_posix()}")

# LLM Bridge (D:\Y26\work_dir\LLM_Bridge) — runs the signed-in vendor CLI, no API keys.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "claude")
LLM_MODEL = os.environ.get("LLM_MODEL", "sonnet")          # planning, lesson notes, tutor
LLM_FAST_MODEL = os.environ.get("LLM_FAST_MODEL", "haiku")  # ranking, short notes
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "420"))
LLM_MAX_PARALLEL = int(os.environ.get("LLM_MAX_PARALLEL", "3"))

FRONTEND_DIST = ROOT / "frontend" / "dist"
HTTP_USER_AGENT = "StudyCompanion/0.1 (personal learning app)"
