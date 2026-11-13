"""Claude Academy tab: the course catalog, your status on each course, and a study path built from the agent track."""

from __future__ import annotations

import logging
import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import claude_academy as ca
from ..agents.base import attach, upsert_resource
from ..agents.review import SYSTEM as CLAUDE_SYSTEM, write_course_qa
from ..agents.updates import CATEGORIES, fetch_updates
from ..db import get_db, session_scope
from ..llm import get_llm
from ..models import AcademyQA, LearningPath, Lesson, Module, QAMark, User
from ..providers import Candidate
from ..voice_langs import MODULE_INDEX
from . import bgjobs
from ..auth import user_slug
from .common import progress_map, qa_counts, require_admin, uid

log = logging.getLogger("study.claude")

router = APIRouter(prefix="/api/claude-academy", tags=["claude-academy"])

Status = Literal["todo", "doing", "done"]
SETTINGS_KEY = "claude_academy"


class StatusIn(BaseModel):
    status: Status


def _statuses(db: Session) -> dict[str, str]:
    user = db.get(User, uid())
    return dict((user.settings or {}).get(SETTINGS_KEY, {}))


def _path(db: Session) -> LearningPath | None:
    return db.scalars(select(LearningPath).where(LearningPath.user_id == uid()).where(LearningPath.slug == user_slug(ca.PATH_SLUG))).first()


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
    qa = qa_counts(db)
    courses = [{**c, "outline": [{"title": t, "lessons": ls} for t, ls in c["outline"]],
                "status": statuses.get(c["slug"], "todo"), "path_progress": in_path.get(c["slug"]),
                "qa": qa.get(c["slug"], {"total": 0, "known": 0, "review": 0})}
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
    user = db.get(User, uid())
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
    path = LearningPath(slug=user_slug(ca.PATH_SLUG), user_id=uid(), title=ca.PATH_TITLE, summary=ca.PATH_SUMMARY, level="intermediate",
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

UPDATES_KEY = "updates"


class RefreshIn(BaseModel):
    days: int = Field(45, ge=7, le=180)


def _updates_state(db: Session) -> dict:
    user = db.get(User, uid())
    st = bgjobs.read(user, UPDATES_KEY)
    legacy = (user.settings or {}).get("ai_updates")  # results saved before the shared job store existed
    if st.get("status") == "idle" and legacy and legacy.get("items"):
        st = {**legacy, "status": "ready"}
    return st


def _updates_out(st: dict) -> dict:
    out = bgjobs.public(st)
    return {"status": out["status"], "error": out["error"], "headline": st.get("headline", ""),
            "items": st.get("items", []), "dropped": st.get("dropped", 0),
            "days": (st.get("params") or {}).get("days", st.get("days", 45)),
            "started_at": out["started_at"], "fetched_at": out["fetched_at"], "categories": CATEGORIES}


@router.get("/updates")
def get_updates(db: Session = Depends(get_db)):
    return _updates_out(_updates_state(db))


@router.post("/updates/refresh")
async def refresh_updates(body: RefreshIn | None = None, db: Session = Depends(get_db)):
    """Start a web search for the latest news. Keeps showing the last results until the new ones arrive."""
    body = body or RefreshIn()
    previous_urls = {i["url"] for i in _updates_state(db).get("items", [])}

    async def work(_prev: dict) -> dict:
        res = await fetch_updates(get_llm(), [c["title"] for c in ca.COURSES], days=body.days)
        items = [i | {"is_new": bool(previous_urls) and i["url"] not in previous_urls} for i in res["items"]]
        return {"headline": res["headline"], "items": items, "dropped": res["dropped"]}

    bgjobs.start(db, UPDATES_KEY, work, days=body.days)
    return _updates_out(_updates_state(db))


# ---------------------------------------------------------------- review Q&A per lesson

QAStatus = Literal["new", "review", "known"]


class QAGenerateIn(BaseModel):
    per_lesson: int = Field(2, ge=1, le=4)


class QAStatusIn(BaseModel):
    status: QAStatus


def _qa_course(slug: str) -> dict:
    c = ca.BY_SLUG.get(slug) or MODULE_INDEX.get(slug, (None, None))[1]  # Voice modules share these endpoints
    if c is None:
        raise HTTPException(404, f"No course or module '{slug}'")
    if not c["outline"]:
        raise HTTPException(400, "This course has no lesson list yet, so there's nothing to write questions for.")
    return c


def _qa_item(q: AcademyQA, mark: str | None = None) -> dict:
    return {"id": q.id, "lesson_idx": q.lesson_idx, "lesson_title": q.lesson_title, "question": q.question,
            "answer_md": q.answer_md, "key_points": q.key_points, "references": q.references,
            "status": mark or "new"}


def _marks(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {m.qa_id: m.status for m in db.scalars(select(QAMark).where(QAMark.user_id == uid(),
                                                                      QAMark.qa_id.in_(ids)))}


@router.get("/qa/{slug}")
def get_qa(slug: str, db: Session = Depends(get_db)):
    c = _qa_course(slug)
    rows = list(db.scalars(select(AcademyQA).where(AcademyQA.course_slug == slug)
                           .order_by(AcademyQA.lesson_idx, AcademyQA.position, AcademyQA.id)))
    marks = _marks(db, [q.id for q in rows])
    st = bgjobs.public(bgjobs.read(db.get(User, uid()), f"qa:{slug}"))
    lessons = [t for _, ls in c["outline"] for t in ls]
    return {"slug": slug, "title": c["title"], "lessons": lessons, "items": [_qa_item(q, marks.get(q.id)) for q in rows],
            "job": {k: st.get(k) for k in ("status", "error", "started_at", "fetched_at")}}


@router.post("/qa/{slug}/generate")
async def generate_qa(slug: str, body: QAGenerateIn | None = None, db: Session = Depends(get_db)):
    """Write (or rewrite) review Q&A for every lesson of a course in the background."""
    c = _qa_course(slug)
    body = body or QAGenerateIn()

    async def work(_prev: dict) -> dict:
        system = MODULE_INDEX[slug][0].QA_SYSTEM if slug in MODULE_INDEX else CLAUDE_SYSTEM
        items = await write_course_qa(get_llm(), c, body.per_lesson, system)
        with session_scope() as s:
            # Keep every account's "know it / review again" marks for questions that come back word for word.
            old = list(s.scalars(select(AcademyQA).where(AcademyQA.course_slug == slug)))
            text = {q.id: q.question for q in old}
            kept = [(m.user_id, text[m.qa_id], m.status) for m in
                    s.scalars(select(QAMark).where(QAMark.qa_id.in_(list(text))))] if text else []
            for q in old:
                s.delete(q)
            s.flush()
            new = {}
            for it in items:
                q = AcademyQA(course_slug=slug, **it)
                s.add(q)
                new.setdefault(it["question"], q)
            s.flush()
            for user_id, question, status in kept:
                if question in new:
                    s.add(QAMark(user_id=user_id, qa_id=new[question].id, status=status))
        return {"count": len(items)}

    bgjobs.start(db, f"qa:{slug}", work, per_lesson=body.per_lesson)
    return get_qa(slug, db)


class QAEditIn(BaseModel):
    status: QAStatus | None = None
    question: str | None = Field(None, min_length=3, max_length=2000)
    answer_md: str | None = Field(None, min_length=1, max_length=20000)
    key_points: list[str] | None = None


@router.patch("/qa/items/{qa_id}")
def edit_qa(qa_id: int, body: QAEditIn, db: Session = Depends(get_db)):
    """Mark a question (any account), or edit its text (admin: questions are shared by all accounts)."""
    q = db.get(AcademyQA, qa_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    edits = body.model_dump(exclude_none=True, exclude={"status"})
    if edits:
        require_admin(db)
        for k, v in edits.items():
            setattr(q, k, v.strip() if isinstance(v, str) else [x.strip() for x in v if x.strip()])
    if body.status:
        m = db.get(QAMark, (uid(), qa_id))
        if m is None:
            db.add(QAMark(user_id=uid(), qa_id=qa_id, status=body.status))
        else:
            m.status = body.status
    db.commit()
    return _qa_item(q, _marks(db, [qa_id]).get(qa_id))


@router.delete("/qa/items/{qa_id}")
def delete_qa(qa_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    q = db.get(AcademyQA, qa_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()
    return {"ok": True}
