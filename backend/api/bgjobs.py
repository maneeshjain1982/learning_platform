"""Small background jobs whose state lives in the user's settings JSON.

Used by the LLM research features (news, certifications, jobs, review Q&A). Each job has a key; its state is
{"status": idle|running|ready|failed, "started_at", "fetched_at", "error", ...result fields}. The last good
result stays visible while a new run is in progress.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable

from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import User, utcnow
from .common import USER_ID, iso, spawn

log = logging.getLogger("study.jobs")
STALE_AFTER = timedelta(hours=6)  # backstop only; server start marks unfinished runs failed (recover_interrupted)
ROOT = "jobs"


def read(user: User, key: str) -> dict:
    st = dict(((user.settings or {}).get(ROOT) or {}).get(key) or {"status": "idle"})
    if st.get("status") == "running" and st.get("started_at"):
        if utcnow() - datetime.fromisoformat(st["started_at"]) > STALE_AFTER:
            st.update(status="failed", error="The last run was interrupted. Try again.")
    return st


def write(db: Session, key: str, **changes) -> dict:
    user = db.get(User, USER_ID)
    settings = dict(user.settings or {})
    jobs = dict(settings.get(ROOT) or {})
    st = {**read(user, key), **changes}
    jobs[key] = st
    settings[ROOT] = jobs
    user.settings = settings  # reassign so SQLAlchemy sees the JSON change
    return st


def public(st: dict) -> dict:
    """State for the API: timestamps as ISO-with-Z."""
    out = dict(st)
    for k in ("started_at", "fetched_at"):
        out[k] = iso(datetime.fromisoformat(st[k])) if st.get(k) else None
    out.setdefault("status", "idle")
    out.setdefault("error", None)
    return out


def start(db: Session, key: str, work: Callable[[dict], Awaitable[dict[str, Any]]], **params) -> dict:
    """Start `work(previous_state)` in the background unless already running. Its returned dict is merged
    into the state with status=ready; an exception marks the job failed and keeps the previous result."""
    user = db.get(User, USER_ID)
    previous = read(user, key)
    if previous.get("status") == "running":
        return previous
    st = write(db, key, status="running", error=None, started_at=utcnow().isoformat(), params=params)
    db.commit()

    async def run():
        try:
            result = await work(previous)
        except Exception as exc:  # LLM unavailable, timeout, bad output
            log.warning("Job %s failed: %s", key, exc)
            with session_scope() as s:
                write(s, key, status="failed", error=str(exc)[:500])
            return
        with session_scope() as s:
            write(s, key, status="ready", error=None, fetched_at=utcnow().isoformat(), **result)

    spawn(run())
    return st


def recover_interrupted(db: Session) -> None:
    """Runs can't survive a server restart: mark any left 'running' as failed so the UI offers a retry."""
    user = db.get(User, USER_ID)
    jobs = dict(((user.settings or {}) if user else {}).get(ROOT) or {})
    changed = {k: {**v, "status": "failed", "error": "Interrupted by a server restart. Try again."}
               for k, v in jobs.items() if v.get("status") == "running"}
    if changed:
        user.settings = {**user.settings, ROOT: {**jobs, **changed}}
