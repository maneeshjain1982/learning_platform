"""Shared helpers for the API routers: background tasks and serializers."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Coroutine

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (AgentRun, Bookmark, LearningPath, Lesson, LessonResource, Progress, Resource, SavedResource,
                      utcnow)
from ..providers import search_links

log = logging.getLogger("study.api")
_tasks: set[asyncio.Task] = set()
from ..auth import uid  # noqa: E402,F401  (the signed-in user; re-exported for the routers)


def spawn(coro: Coroutine) -> None:
    """Run agent work in the background on the server's event loop."""
    task = asyncio.get_running_loop().create_task(coro)
    _tasks.add(task)

    def _done(t: asyncio.Task):
        _tasks.discard(t)
        if not t.cancelled() and t.exception():
            log.error("Background task failed: %s", t.exception())

    task.add_done_callback(_done)


def owner_of(obj) -> int | None:
    """The account that owns a row, following lesson -> module -> path; None for shared rows."""
    if isinstance(obj, Lesson):
        obj = obj.module
    if hasattr(obj, "path") and isinstance(getattr(obj, "path", None), LearningPath):
        obj = obj.path
    return getattr(obj, "user_id", None)


def get_or_404(db: Session, model, id_: int):
    """Fetch a row; rows that belong to another account look the same as missing ones."""
    obj = db.get(model, id_)
    if obj is None or (owner := owner_of(obj)) is not None and owner != uid():
        raise HTTPException(404, f"{model.__name__} {id_} not found")
    return obj


def require_admin(db: Session) -> None:
    from ..models import User
    u = db.get(User, uid())
    if u is None or u.role != "admin":
        raise HTTPException(403, "Only the admin account can change shared content.")


def qa_counts(db: Session, prefix: str = "") -> dict[str, dict]:
    """Review-question counts per course/module slug, with the signed-in account's marks."""
    from ..models import AcademyQA, QAMark
    q = (select(AcademyQA.course_slug, QAMark.status, func.count())
         .outerjoin(QAMark, (QAMark.qa_id == AcademyQA.id) & (QAMark.user_id == uid()))
         .group_by(AcademyQA.course_slug, QAMark.status))
    if prefix:
        q = q.where(AcademyQA.course_slug.like(f"{prefix}%"))
    out: dict[str, dict] = {}
    for slug, status, n in db.execute(q):
        d = out.setdefault(slug, {"total": 0, "known": 0, "review": 0})
        d["total"] += n
        if status in ("known", "review"):
            d[status] += n
    return out


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def progress_map(db: Session, lesson_ids: list[int]) -> dict[int, Progress]:
    if not lesson_ids:
        return {}
    rows = db.scalars(select(Progress).where(Progress.user_id == uid(), Progress.lesson_id.in_(lesson_ids)))
    return {p.lesson_id: p for p in rows}


def saved_ids(db: Session) -> set[int]:
    return set(db.scalars(select(SavedResource.resource_id).where(SavedResource.user_id == uid())))


def resource_out(r: Resource, *, why: str = "", saved: set[int] | None = None, added_by: str | None = None) -> dict:
    return {
        "id": r.id, "kind": r.kind, "source": r.source, "title": r.title, "url": r.url, "author": r.author,
        "year": r.year, "duration_min": r.duration_min, "summary": r.summary, "thumbnail": r.thumbnail,
        "external_id": r.external_id, "citations": (r.meta or {}).get("citations"), "pdf": (r.meta or {}).get("pdf"),
        "why": why, "saved": r.id in (saved or set()), "added_by": added_by,
        "has_summary": bool((r.meta or {}).get("ai_summary")),
    }


def lesson_resources(db: Session, lesson_ids: list[int], saved: set[int] | None = None) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {i: [] for i in lesson_ids}
    if not lesson_ids:
        return out
    rows = db.scalars(select(LessonResource).where(LessonResource.lesson_id.in_(lesson_ids))
                      .order_by(LessonResource.rank))
    for lr in rows:
        out[lr.lesson_id].append(resource_out(lr.resource, why=lr.why, saved=saved, added_by=lr.added_by))
    return out


def path_summary(db: Session, path: LearningPath) -> dict:
    lessons = [l for m in path.modules for l in m.lessons]
    prog = progress_map(db, [l.id for l in lessons])
    done = sum(1 for l in lessons if prog.get(l.id) and prog[l.id].status == "done")
    current = next((l for l in lessons if not (prog.get(l.id) and prog[l.id].status == "done")), None)
    last = max((p.updated_at for p in prog.values()), default=None)
    return {
        "id": path.id, "title": path.title, "summary": path.summary, "level": path.level, "status": path.status,
        "hours_per_week": path.hours_per_week, "weeks": path.weeks, "is_seed": path.is_seed,
        "show_on_home": path.show_on_home, "position": path.position, "kind": path.kind,
        "modules": len(path.modules), "lessons": len(lessons), "done": done,
        "pct": round(100 * done / len(lessons)) if lessons else 0,
        "current_lesson_id": current.id if current else None,
        "last_activity": iso(last), "created_at": iso(path.created_at),
    }


def bookmark_out(b: Bookmark, path_titles: dict[int, str] | None = None) -> dict:
    return {
        "id": b.id, "kind": b.kind, "title": b.title, "url": b.url, "provider": b.provider, "note": b.note,
        "path_id": b.path_id, "path_title": (path_titles or {}).get(b.path_id) if b.path_id else None,
        "show_on_home": b.show_on_home, "status": b.status, "created_at": iso(b.created_at),
    }


def module_links(keywords: list[str], title: str) -> list[dict]:
    q = (keywords or [title])[0]
    return search_links(q)


def week_stats(db: Session, path: LearningPath | None) -> dict:
    since = utcnow() - timedelta(days=7)
    from ..models import ChatMessage, ChatSession

    done_rows = db.scalars(select(Progress).where(Progress.user_id == uid(), Progress.status == "done",
                                                  Progress.completed_at >= since)).all()
    minutes = 0
    for p in done_rows:
        lesson = db.get(Lesson, p.lesson_id)
        minutes += max(p.minutes_spent, lesson.est_minutes if lesson else 0)
    questions = db.scalar(
        select(func.count(ChatMessage.id)).join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.user_id == uid(), ChatMessage.role == "user", ChatMessage.created_at >= since)) or 0
    goal_h = path.hours_per_week if path else 5
    return {"minutes": minutes, "goal_minutes": goal_h * 60, "lessons_done": len(done_rows),
            "questions": questions}


def last_run(db: Session, path_id: int) -> dict | None:
    run = db.scalars(select(AgentRun).where(AgentRun.path_id == path_id).order_by(AgentRun.id.desc())).first()
    return run_out(run) if run else None


def run_out(run: AgentRun) -> dict:
    return {
        "id": run.id, "kind": run.kind, "status": run.status, "error": run.error, "path_id": run.path_id,
        "requirement_id": run.requirement_id, "started_at": iso(run.started_at), "finished_at": iso(run.finished_at),
        "steps": [{"agent": s.agent, "status": s.status, "summary": s.summary, "chips": s.chips or [],
                   "started_at": iso(s.started_at), "finished_at": iso(s.finished_at)} for s in run.steps],
    }
