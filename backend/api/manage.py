"""Editing endpoints: your own courses and links, and changes to any path, module or lesson."""

from __future__ import annotations

import html
import re
from typing import Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..models import AgentRun, Bookmark, LearningPath, Lesson, Module, User
from ..providers import youtube_verify
from ..seed import seed_structure
from .common import USER_ID, bookmark_out, get_or_404, path_summary

router = APIRouter(prefix="/api", tags=["manage"])

Direction = Literal["up", "down"]


class MoveIn(BaseModel):
    direction: Direction


def _ensure_idle(db: Session, path_id: int) -> None:
    running = db.scalars(select(AgentRun).where(AgentRun.path_id == path_id, AgentRun.status == "running")).first()
    if running:
        raise HTTPException(409, "Agents are working on this path right now. Try again when they finish.")


def _move(items: list, item, direction: str, attr: str) -> None:
    """Swap `item` with its neighbour and renumber `attr` 0..n-1."""
    items = list(items)
    i = items.index(item)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(items):
        items[i], items[j] = items[j], items[i]
    for n, it in enumerate(items):
        setattr(it, attr, n)


def _renumber(items: list, attr: str = "idx") -> None:
    for n, it in enumerate(items):
        setattr(it, attr, n)


def ordered_paths(db: Session) -> list[LearningPath]:
    return list(db.scalars(select(LearningPath).order_by(LearningPath.position, LearningPath.id)))


# ---------------------------------------------------------------- paths (courses)

Level = Literal["beginner", "intermediate", "advanced"]


class PathIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field("", max_length=4000)
    level: Level = "intermediate"
    hours_per_week: int = Field(5, ge=1, le=60)
    weeks: int = Field(6, ge=1, le=52)
    modules: list[str] = Field(default_factory=list, max_length=30)  # optional module titles to start with


class PathPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=4000)
    level: Level | None = None
    hours_per_week: int | None = Field(None, ge=1, le=60)
    weeks: int | None = Field(None, ge=1, le=52)
    show_on_home: bool | None = None


@router.post("/paths")
def create_path(body: PathIn, db: Session = Depends(get_db)):
    top = db.scalar(select(func.max(LearningPath.position))) or 0
    path = LearningPath(title=body.title.strip(), summary=body.summary.strip(), level=body.level,
                        hours_per_week=body.hours_per_week, weeks=body.weeks, status="ready",
                        sources=["youtube", "coursera", "udemy", "arxiv"], position=top + 1)
    for i, t in enumerate(x.strip() for x in body.modules if x.strip()):
        path.modules.append(Module(idx=i, title=t, keywords=[t], paper_keywords=[t]))
    db.add(path)
    db.commit()
    return path_summary(db, path)


@router.patch("/paths/{path_id}")
def update_path(path_id: int, body: PathPatch, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(path, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return path_summary(db, path)


@router.post("/paths/{path_id}/move")
def move_path(path_id: int, body: MoveIn, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    _move(ordered_paths(db), path, body.direction, "position")
    db.commit()
    return {"ok": True}


@router.delete("/paths/{path_id}")
def delete_path(path_id: int, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    _ensure_idle(db, path_id)
    if path.is_seed and path.slug:
        # Remember it so the starter path isn't recreated on the next server start.
        user = db.get(User, USER_ID)
        settings = dict(user.settings or {})
        settings["removed_seeds"] = sorted(set(settings.get("removed_seeds", [])) | {path.slug})
        user.settings = settings
    db.delete(path)
    db.commit()
    return {"ok": True}


@router.post("/paths/restore-starters")
async def restore_starters(db: Session = Depends(get_db)):
    """Bring back deleted starter paths (Agentic AI, LLM Fundamentals, Agentic Harness)."""
    user = db.get(User, USER_ID)
    user.settings = {k: v for k, v in (user.settings or {}).items() if k != "removed_seeds"}
    db.flush()
    created = seed_structure(db)
    db.commit()
    if created:
        from ..seed import attach_seed_papers
        from .common import spawn

        spawn(attach_seed_papers())
    return {"restored": len(created)}


# ---------------------------------------------------------------- modules

class ModuleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field("", max_length=4000)


class ModulePatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=4000)


def _module_out(m: Module) -> dict:
    return {"id": m.id, "idx": m.idx, "title": m.title, "summary": m.summary}


@router.post("/paths/{path_id}/modules")
def add_module(path_id: int, body: ModuleIn, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    t = body.title.strip()
    mod = Module(idx=len(path.modules), title=t, summary=body.summary.strip(), keywords=[t], paper_keywords=[t])
    path.modules.append(mod)
    db.commit()
    return _module_out(mod)


@router.patch("/modules/{module_id}")
def update_module(module_id: int, body: ModulePatch, db: Session = Depends(get_db)):
    mod = get_or_404(db, Module, module_id)
    if body.title is not None:
        old, mod.title = mod.title, body.title.strip()
        if not mod.keywords or mod.keywords == [old]:
            mod.keywords = [mod.title]  # keep search terms in step with the title for user-made modules
    if body.summary is not None:
        mod.summary = body.summary.strip()
    db.commit()
    return _module_out(mod)


@router.post("/modules/{module_id}/move")
def move_module(module_id: int, body: MoveIn, db: Session = Depends(get_db)):
    mod = get_or_404(db, Module, module_id)
    _move(mod.path.modules, mod, body.direction, "idx")
    db.commit()
    return {"ok": True}


@router.delete("/modules/{module_id}")
def delete_module(module_id: int, db: Session = Depends(get_db)):
    mod = get_or_404(db, Module, module_id)
    path = mod.path
    _ensure_idle(db, path.id)
    path.modules.remove(mod)
    _renumber(path.modules)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- lessons

class LessonIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    est_minutes: int = Field(20, ge=1, le=600)
    objectives: list[str] = Field(default_factory=list, max_length=20)


class LessonPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    est_minutes: int | None = Field(None, ge=1, le=600)
    objectives: list[str] | None = Field(None, max_length=20)


def _lesson_out(l: Lesson) -> dict:
    return {"id": l.id, "idx": l.idx, "title": l.title, "est_minutes": l.est_minutes, "objectives": l.objectives}


def _clean(items: list[str]) -> list[str]:
    return [x.strip() for x in items if x.strip()]


@router.post("/modules/{module_id}/lessons")
def add_lesson(module_id: int, body: LessonIn, db: Session = Depends(get_db)):
    mod = get_or_404(db, Module, module_id)
    t = body.title.strip()
    lesson = Lesson(idx=len(mod.lessons), title=t, est_minutes=body.est_minutes,
                    objectives=_clean(body.objectives), keywords=[t])
    mod.lessons.append(lesson)
    db.commit()
    return _lesson_out(lesson)


@router.patch("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, body: LessonPatch, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    if body.title is not None:
        old, lesson.title = lesson.title, body.title.strip()
        if not lesson.keywords or lesson.keywords == [old]:
            lesson.keywords = [lesson.title]
    if body.est_minutes is not None:
        lesson.est_minutes = body.est_minutes
    if body.objectives is not None:
        lesson.objectives = _clean(body.objectives)
    db.commit()
    return _lesson_out(lesson)


@router.post("/lessons/{lesson_id}/move")
def move_lesson(lesson_id: int, body: MoveIn, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    _move(lesson.module.lessons, lesson, body.direction, "idx")
    db.commit()
    return {"ok": True}


@router.delete("/lessons/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    mod = lesson.module
    _ensure_idle(db, mod.path_id)
    mod.lessons.remove(lesson)
    _renumber(mod.lessons)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- my courses & links

LinkKind = Literal["course", "link", "video", "paper", "doc"]

_PROVIDERS = [  # (host suffix, provider, default kind)
    ("youtube.com", "youtube", "video"), ("youtu.be", "youtube", "video"),
    ("coursera.org", "coursera", "course"), ("udemy.com", "udemy", "course"),
    ("linkedin.com", "linkedin", "course"), ("edx.org", "edx", "course"),
    ("deeplearning.ai", "deeplearning_ai", "course"), ("udacity.com", "udacity", "course"),
    ("arxiv.org", "arxiv", "paper"), ("github.com", "github", "link"),
]


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc or "." not in p.netloc:
        raise HTTPException(422, "Enter a web address, like https://www.udemy.com/course/…")
    return url


def detect(url: str) -> tuple[str, str]:
    host = urlparse(url).netloc.lower().split(":")[0]
    host = host[4:] if host.startswith("www.") else host
    for suffix, provider, kind in _PROVIDERS:
        if host == suffix or host.endswith("." + suffix):
            return provider, kind
    return host, "link"


async def fetch_title(url: str, provider: str) -> str | None:
    """Best effort: the page's own title, so the user doesn't have to type one."""
    try:
        if provider == "youtube":
            cand = await youtube_verify(url)
            return cand.title if cand else None
        async with httpx.AsyncClient(timeout=6, follow_redirects=True,
                                     headers={"User-Agent": config.HTTP_USER_AGENT}) as c:
            r = await c.get(url)
        m = re.search(r"<title[^>]*>(.*?)</title>", r.text[:200_000], re.I | re.S)
        title = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
        return title[:300] or None
    except Exception:  # noqa: BLE001 — a missing title is fine
        return None


class LinkIn(BaseModel):
    url: str = Field(min_length=3, max_length=2000)
    title: str = Field("", max_length=300)
    kind: LinkKind | None = None
    note: str = Field("", max_length=4000)
    path_id: int | None = None
    show_on_home: bool = True

    @field_validator("title", "note")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class LinkPatch(BaseModel):
    url: str | None = Field(None, min_length=3, max_length=2000)
    title: str | None = Field(None, min_length=1, max_length=300)
    kind: LinkKind | None = None
    note: str | None = Field(None, max_length=4000)
    path_id: int | None = None
    clear_path: bool = False  # set true to detach from its path (path_id=None alone means "unchanged")
    show_on_home: bool | None = None
    status: Literal["todo", "doing", "done"] | None = None


@router.get("/links")
def list_links(path_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Bookmark).where(Bookmark.user_id == USER_ID).order_by(Bookmark.position, Bookmark.id)
    if path_id is not None:
        q = q.where(Bookmark.path_id == path_id)
    titles = {p.id: p.title for p in db.scalars(select(LearningPath))}
    return [bookmark_out(b, titles) for b in db.scalars(q)]


@router.post("/links")
async def create_link(body: LinkIn, db: Session = Depends(get_db)):
    url = normalize_url(body.url)
    provider, kind = detect(url)
    if body.path_id is not None:
        get_or_404(db, LearningPath, body.path_id)
    title = body.title or await fetch_title(url, provider) or urlparse(url).netloc
    top = db.scalar(select(func.max(Bookmark.position)).where(Bookmark.user_id == USER_ID)) or 0
    b = Bookmark(user_id=USER_ID, url=url, title=title, provider=provider, kind=body.kind or kind,
                 note=body.note, path_id=body.path_id, show_on_home=body.show_on_home, position=top + 1)
    db.add(b)
    db.commit()
    return bookmark_out(b, {p.id: p.title for p in db.scalars(select(LearningPath))})


@router.patch("/links/{link_id}")
def update_link(link_id: int, body: LinkPatch, db: Session = Depends(get_db)):
    b = get_or_404(db, Bookmark, link_id)
    if body.url is not None:
        b.url = normalize_url(body.url)
        b.provider = detect(b.url)[0]
    if body.path_id is not None:
        get_or_404(db, LearningPath, body.path_id)
        b.path_id = body.path_id
    if body.clear_path:
        b.path_id = None
    for k in ("title", "kind", "note", "show_on_home", "status"):
        v = getattr(body, k)
        if v is not None:
            setattr(b, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return bookmark_out(b, {p.id: p.title for p in db.scalars(select(LearningPath))})


@router.post("/links/{link_id}/move")
def move_link(link_id: int, body: MoveIn, db: Session = Depends(get_db)):
    b = get_or_404(db, Bookmark, link_id)
    items = list(db.scalars(select(Bookmark).where(Bookmark.user_id == USER_ID)
                            .order_by(Bookmark.position, Bookmark.id)))
    _move(items, b, body.direction, "position")
    db.commit()
    return {"ok": True}


@router.delete("/links/{link_id}")
def delete_link(link_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, Bookmark, link_id))
    db.commit()
    return {"ok": True}
