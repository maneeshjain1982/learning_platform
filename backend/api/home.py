from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import orchestrator
from ..db import get_db
from ..llm import LLMUnavailable
from ..models import Bookmark, FocusNote, LearningPath, Lesson, Progress, User
from .common import (uid, bookmark_out, get_or_404, last_run, lesson_resources, module_links, path_summary,
                     progress_map, saved_ids, week_stats)

router = APIRouter(prefix="/api/home", tags=["home"])

# Home page cards, in default order. "admin" cards only show for the admin account.
CARDS = [("continue", "Continue learning"), ("week", "This week"), ("paths", "My paths"), ("news", "Tech News"),
         ("picks", "Videos & papers for now"), ("links", "My links"), ("jobs", "Hot jobs")]
ADMIN_CARDS = {"jobs"}
DEFAULT_OFF = {"links"}


def _layout(user: User) -> list[dict]:
    """Your home cards in your order: saved choices first, then any new cards with their defaults."""
    allowed = {k: label for k, label in CARDS if k not in ADMIN_CARDS or user.role == "admin"}
    saved = [c for c in ((user.settings or {}).get("home_layout") or []) if c.get("id") in allowed]
    ids = {c["id"] for c in saved}
    rest = [{"id": k, "on": k not in DEFAULT_OFF} for k in allowed if k not in ids]
    return [{"id": c["id"], "label": allowed[c["id"]], "on": bool(c.get("on", True))} for c in saved + rest]


class LayoutCard(BaseModel):
    id: str
    on: bool


@router.get("/layout")
def get_layout(db: Session = Depends(get_db)):
    return _layout(db.get(User, uid()))


@router.put("/layout")
def put_layout(cards: list[LayoutCard], db: Session = Depends(get_db)):
    user = db.get(User, uid())
    known = {c["id"] for c in _layout(user)}
    if any(c.id not in known for c in cards):
        raise HTTPException(422, "Unknown card")
    user.settings = {**(user.settings or {}), "home_layout": [c.model_dump() for c in cards]}
    db.commit()
    return _layout(user)


def _active_path(db: Session, path_id: int | None, visible: list[LearningPath]) -> LearningPath | None:
    """The chosen path if it's still on the home page, else the one studied most recently, else the first."""
    ids = {p.id for p in visible}
    if path_id in ids:
        return db.get(LearningPath, path_id)
    for prog in db.scalars(select(Progress).where(Progress.user_id == uid()).order_by(Progress.updated_at.desc())):
        lesson = db.get(Lesson, prog.lesson_id)
        if lesson and lesson.module.path_id in ids:
            return lesson.module.path
    return next((p for p in visible if p.status != "failed"), None)


def _my_links(db: Session, path: LearningPath | None) -> list[dict]:
    """Your own courses and links for the home page: general ones plus those added to the active path."""
    q = (select(Bookmark).where(Bookmark.user_id == uid(), Bookmark.show_on_home.is_(True))
         .order_by(Bookmark.position, Bookmark.id))
    titles = {p.id: p.title for p in db.scalars(select(LearningPath).where(LearningPath.user_id == uid()))}
    return [bookmark_out(b, titles) for b in db.scalars(q)
            if b.path_id is None or (path is not None and b.path_id == path.id)]


@router.get("")
def home(path_id: int | None = None, db: Session = Depends(get_db)):
    user = db.get(User, uid())
    all_paths = list(db.scalars(select(LearningPath).where(LearningPath.user_id == uid()).order_by(LearningPath.position, LearningPath.id)))
    visible = [p for p in all_paths if p.show_on_home]
    paths = [path_summary(db, p) for p in visible]
    hidden = len(all_paths) - len(visible)
    path = _active_path(db, path_id, visible)
    if path is None:
        return {"user": {"name": user.name if user else "Learner"}, "layout": _layout(user), "paths": paths,
                "hidden_paths": hidden,
                "my_links": _my_links(db, None), "active": None}

    lessons = [l for m in path.modules for l in m.lessons]
    prog = progress_map(db, [l.id for l in lessons])
    is_done = lambda l: l.id in prog and prog[l.id].status == "done"  # noqa: E731
    current = next((l for l in lessons if not is_done(l)), None)
    cur_mod = current.module if current else (path.modules[-1] if path.modules else None)

    modules = []
    for m in path.modules:
        n_done = sum(1 for l in m.lessons if is_done(l))
        state = "done" if n_done == len(m.lessons) and m.lessons else ("now" if cur_mod and m.id == cur_mod.id else "next")
        modules.append({"id": m.id, "idx": m.idx, "title": m.title, "state": state, "lessons": len(m.lessons),
                        "done": n_done, "minutes": sum(l.est_minutes for l in m.lessons),
                        "resources_status": m.resources_status})

    videos, papers, links = [], [], []
    if cur_mod:
        res = lesson_resources(db, [l.id for l in cur_mod.lessons], saved_ids(db))
        seen = set()
        # current lesson first, then the rest of the module
        order = sorted(cur_mod.lessons, key=lambda l: (l.id != (current.id if current else None), l.idx))
        for l in order:
            for r in res[l.id]:
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                r = {**r, "lesson_title": l.title, "lesson_id": l.id}
                (videos if r["kind"] == "video" else papers if r["kind"] == "paper" else []).append(r)
        for kw in (cur_mod.keywords or [cur_mod.title])[:2]:
            links += [{**lk, "query": kw} for lk in module_links([kw], kw) if lk["source"] in ("coursera", "udemy")]

    cont = None
    if current:
        m_lessons = current.module.lessons
        cont = {"lesson_id": current.id, "title": current.title, "module_idx": current.module.idx,
                "module_title": current.module.title, "lesson_idx": current.idx, "est_minutes": current.est_minutes,
                "started": current.id in prog, "module_done": sum(1 for l in m_lessons if is_done(l)),
                "module_lessons": len(m_lessons)}

    note = db.get(FocusNote, current.id) if current else None
    return {
        "user": {"name": user.name if user else "Learner"},
        "layout": _layout(user),
        "paths": paths,
        "hidden_paths": hidden,
        "my_links": _my_links(db, path),
        "active": {
            **path_summary(db, path),
            "modules_detail": modules,
            "continue": cont,
            "focus_note": note.text if note else None,
            "videos": videos[:8], "papers": papers[:6], "course_links": links,
            "current_module": {"id": cur_mod.id, "title": cur_mod.title, "idx": cur_mod.idx,
                               "resources_status": cur_mod.resources_status} if cur_mod else None,
            "week": week_stats(db, path),
            "last_run": last_run(db, path.id),
        },
    }


@router.post("/focus/{lesson_id}")
async def focus_note(lesson_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Lesson, lesson_id)
    try:
        return {"text": await orchestrator.compose_focus_note(lesson_id)}
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
