"""Claude Academy tab: the course catalog, your status on each course, and a study path built from the agent track."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import claude_academy as ca
from ..agents.base import attach, upsert_resource
from ..agents.updates import CATEGORIES, fetch_updates
from ..db import get_db, session_scope
from ..llm import get_llm
from ..models import LearningPath, Lesson, Module, User, utcnow
from ..providers import Candidate
from .common import USER_ID, iso, progress_map, spawn

log = logging.getLogger("study.claude")

router = APIRouter(prefix="/api/claude-academy", tags=["claude-academy"])

Status = Literal["todo", "doing", "done"]
SETTINGS_KEY = "claude_academy"


class StatusIn(BaseModel):
    status: Status


def _statuses(db: Session) -> dict[str, str]:
    user = db.get(User, USER_ID)
    return dict((user.settings or {}).get(SETTINGS_KEY, {}))


def _path(db: Session) -> LearningPath | None:
    return db.scalars(select(LearningPath).where(LearningPath.slug == ca.PATH_SLUG)).first()


def _path_lesson_progress(db: Session, path: LearningPath | None) -> dict[str, dict]:
    """Lessons done per course, read from the study path (module order follows the agent track)."""
    if path is None:
        return {}
    by_title = {c["title"]: c["slug"] for c in ca.AGENT_TRACK}
    lessons = [l for m in path.modules for l in m.lessons]
    prog = progress_map(db, [l.id for l in lessons])
    out = {}
    for m in path.modules:
        slug = by_title.get(m.title)
        if slug:
            done = sum(1 for l in m.lessons if (p := prog.get(l.id)) and p.status == "done")
            out[slug] = {"done": done, "total": len(m.lessons), "module_id": m.id}
    return out


@router.get("")
def catalog(db: Session = Depends(get_db)):
    statuses = _statuses(db)
    path = _path(db)
    in_path = _path_lesson_progress(db, path)
    courses = [{**c, "outline": [{"title": t, "lessons": ls} for t, ls in c["outline"]],
                "status": statuses.get(c["slug"], "todo"), "path_progress": in_path.get(c["slug"])}
               for c in ca.COURSES]
    track_hours = sum(c["hours"] or 0 for c in ca.AGENT_TRACK)
    return {
        "base_url": ca.BASE_URL, "checked_on": ca.CHECKED_ON, "groups": ca.GROUPS, "courses": courses,
        "track": {"hours": track_hours, "courses": len(ca.AGENT_TRACK),
                  "lessons": sum(c["lessons"] for c in ca.AGENT_TRACK)},
        "path_id": path.id if path else None,
    }


@router.put("/courses/{slug}/status")
def set_status(slug: str, body: StatusIn, db: Session = Depends(get_db)):
    if slug not in ca.BY_SLUG:
        raise HTTPException(404, f"No Claude Academy course '{slug}'")
    user = db.get(User, USER_ID)
    settings = dict(user.settings or {})
    statuses = dict(settings.get(SETTINGS_KEY, {}))
    if body.status == "todo":
        statuses.pop(slug, None)
    else:
        statuses[slug] = body.status
    settings[SETTINGS_KEY] = statuses
    user.settings = settings  # reassign so SQLAlchemy sees the JSON change
    db.commit()
    return {"slug": slug, "status": body.status}


@router.post("/path")
def create_path(db: Session = Depends(get_db)):
    """Turn the agent track into a study path: one module per course, one lesson per course lesson."""
    existing = _path(db)
    if existing:
        return {"path_id": existing.id, "created": False}
    top = db.scalar(select(func.max(LearningPath.position))) or 0
    hours = sum(c["hours"] or 0 for c in ca.AGENT_TRACK)
    path = LearningPath(slug=ca.PATH_SLUG, title=ca.PATH_TITLE, summary=ca.PATH_SUMMARY, level="intermediate",
                        hours_per_week=5, weeks=max(1, math.ceil(hours / 5)), status="ready", position=top + 1,
                        sources=["youtube", "arxiv", "semantic_scholar"])
    for mi, c in enumerate(ca.AGENT_TRACK):
        titles = [t for _, ls in c["outline"] for t in ls]
        minutes = max(5, round((c["hours"] or 1) * 60 / max(1, len(titles))))
        mod = Module(idx=mi, title=c["title"], summary=c["summary"] + (f"\n\nWhy it matters: {c['why']}" if c["why"] else ""),
                     keywords=[f"{c['title']} Claude"], paper_keywords=[c["title"]],
                     objectives=[c["why"]] if c["why"] else [])
        mod.lessons = [Lesson(idx=li, title=t, keywords=[t, "Claude"], est_minutes=minutes,
                              objectives=[f"Complete '{t}' in {c['title']} on Claude Academy"])
                       for li, t in enumerate(titles)]
        path.modules.append(mod)
    db.add(path)
    db.flush()

    # Link every lesson to its course page so the lesson view has a one-click way to the real content.
    for mod, c in zip(path.modules, ca.AGENT_TRACK):
        res = upsert_resource(db, Candidate(
            kind="course", source="claude_academy", external_id=c["slug"], title=c["title"], url=c["url"],
            author="Anthropic", summary=c["summary"], duration_min=round((c["hours"] or 0) * 60) or None,
            meta={"lessons": c["lessons"], "free": True}))
        for lesson in mod.lessons:
            attach(db, lesson.id, res.id, rank=0, why="The official course on Claude Academy (free).",
                   added_by="seed")
    db.commit()
    return {"path_id": path.id, "created": True}


# ---------------------------------------------------------------- new updates (LLM + web search)

UPDATES_KEY = "ai_updates"
STALE_AFTER = timedelta(minutes=20)  # a refresh still "running" after this was cut off (e.g. server restart)


class RefreshIn(BaseModel):
    days: int = Field(45, ge=7, le=180)


def _read_updates(user: User) -> dict:
    st = dict((user.settings or {}).get(UPDATES_KEY) or {"status": "idle", "items": []})
    if st.get("status") == "running" and st.get("started_at"):
        if utcnow() - datetime.fromisoformat(st["started_at"]) > STALE_AFTER:
            st.update(status="failed", error="The refresh was interrupted. Try again.")
    return st


def _write_updates(db: Session, **changes) -> dict:
    user = db.get(User, USER_ID)
    settings = dict(user.settings or {})
    st = {**_read_updates(user), **changes}
    settings[UPDATES_KEY] = st
    user.settings = settings
    return st


def _updates_out(st: dict) -> dict:
    fmt = lambda k: iso(datetime.fromisoformat(st[k])) if st.get(k) else None  # noqa: E731
    return {"status": st.get("status", "idle"), "error": st.get("error"), "headline": st.get("headline", ""),
            "items": st.get("items", []), "dropped": st.get("dropped", 0), "days": st.get("days", 45),
            "started_at": fmt("started_at"), "fetched_at": fmt("fetched_at"), "categories": CATEGORIES}


async def _run_refresh(days: int) -> None:
    with session_scope() as db:
        previous = {i["url"] for i in _read_updates(db.get(User, USER_ID)).get("items", [])}
    try:
        res = await fetch_updates(get_llm(), [c["title"] for c in ca.COURSES], days=days)
    except Exception as exc:  # LLM unavailable, timeout, bad output
        log.warning("Updates refresh failed: %s", exc)
        with session_scope() as db:
            _write_updates(db, status="failed", error=str(exc)[:500])
        return
    items = [i | {"is_new": bool(previous) and i["url"] not in previous} for i in res["items"]]
    with session_scope() as db:
        _write_updates(db, status="ready", error=None, headline=res["headline"], items=items,
                       dropped=res["dropped"], fetched_at=utcnow().isoformat())


@router.get("/updates")
def get_updates(db: Session = Depends(get_db)):
    return _updates_out(_read_updates(db.get(User, USER_ID)))


@router.post("/updates/refresh")
async def refresh_updates(body: RefreshIn | None = None, db: Session = Depends(get_db)):
    """Start a web search for the latest news. Keeps showing the last results until the new ones arrive."""
    body = body or RefreshIn()
    if _read_updates(db.get(User, USER_ID)).get("status") == "running":
        return get_updates(db)
    st = _write_updates(db, status="running", error=None, days=body.days, started_at=utcnow().isoformat())
    db.commit()
    spawn(_run_refresh(body.days))
    return _updates_out(st)
