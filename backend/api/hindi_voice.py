"""Hindi Voice tab: competencies, courses, technical modules, models, datasets, papers, launch playbook, testing,
data plan, an LLM research refresh and a Hindi utterance generator.

Review Q&A for the technical modules uses the shared Q&A endpoints in api/claude.py (module slugs start "hv-").
"""

from __future__ import annotations

import math
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import hindi_voice as hv
from ..agents.base import attach, upsert_resource
from ..agents.hindi_voice import STYLES, SlotSpec, find_research, generate_utterances
from ..db import get_db
from ..llm import get_llm
from ..models import AcademyQA, LearningPath, Lesson, Module, User
from ..providers import Candidate
from . import bgjobs
from .common import USER_ID, progress_map

router = APIRouter(prefix="/api/hindi-voice", tags=["hindi-voice"])
SETTINGS_KEY = "hindi_voice"
RESEARCH_KEY = "hv-research"
UTTER_KEY = "hv-utterances"

STEP_IDS = {f"{p['id']}:{i}" for p in hv.PLAYBOOK for i in range(len(p["steps"]))}
SKILL_NAMES = {s[0] for a in hv.COMPETENCIES for s in a["skills"]}
COURSE_IDS = {c["id"] for c in hv.COURSES}


def _state(db: Session) -> dict:
    user = db.get(User, USER_ID)
    st = dict((user.settings or {}).get(SETTINGS_KEY) or {})
    return {"skills": dict(st.get("skills") or {}), "courses": dict(st.get("courses") or {}),
            "steps": list(st.get("steps") or [])}


def _save_state(db: Session, st: dict) -> None:
    user = db.get(User, USER_ID)
    user.settings = {**(user.settings or {}), SETTINGS_KEY: st}  # reassign so SQLAlchemy sees the JSON change


def _path(db: Session) -> LearningPath | None:
    return db.scalars(select(LearningPath).where(LearningPath.slug == hv.PATH_SLUG)).first()


def _module_progress(db: Session, path: LearningPath | None) -> dict[str, dict]:
    if path is None:
        return {}
    by_title = {m["title"]: m["slug"] for m in hv.MODULES}
    prog = progress_map(db, [l.id for m in path.modules for l in m.lessons])
    out = {}
    for m in path.modules:
        if slug := by_title.get(m.title):
            done = sum(1 for l in m.lessons if (p := prog.get(l.id)) and p.status == "done")
            out[slug] = {"done": done, "total": len(m.lessons)}
    return out


@router.get("")
def overview(db: Session = Depends(get_db)):
    st = _state(db)
    path = _path(db)
    prog = _module_progress(db, path)
    qa: dict[str, dict] = {}
    for slug, status, n in db.execute(select(AcademyQA.course_slug, AcademyQA.status, func.count())
                                      .where(AcademyQA.course_slug.like("hv-%"))
                                      .group_by(AcademyQA.course_slug, AcademyQA.status)):
        d = qa.setdefault(slug, {"total": 0, "known": 0, "review": 0})
        d["total"] += n
        if status in ("known", "review"):
            d[status] += n
    empty = {"total": 0, "known": 0, "review": 0}
    return {
        "checked_on": hv.CHECKED_ON,
        "competencies": [{"id": a["id"], "title": a["title"],
                          "skills": [{"name": n, "need": need, "why": why, "level": st["skills"].get(n, 0)}
                                     for n, need, why in a["skills"]]} for a in hv.COMPETENCIES],
        "phases": hv.PHASES,
        "courses": [{**c, "status": st["courses"].get(c["id"], "todo")} for c in hv.COURSES],
        "sides": hv.SIDES,
        "modules": [{**{k: v for k, v in m.items() if k != "outline"},
                     "outline": [{"title": t, "lessons": ls} for t, ls in m["outline"]],
                     "qa": qa.get(m["slug"], empty), "path_progress": prog.get(m["slug"])} for m in hv.MODULES],
        "model_kinds": hv.MODEL_KINDS, "models": hv.MODELS,
        "dataset_kinds": hv.DATASET_KINDS, "datasets": hv.DATASETS,
        "paper_topics": hv.PAPER_TOPICS, "papers": hv.PAPERS,
        "playbook": hv.PLAYBOOK, "steps_done": [s for s in st["steps"] if s in STEP_IDS],
        "testing": hv.TESTING, "test_sizing": hv.TEST_SIZING,
        "variability": hv.VARIABILITY, "sourcing": hv.SOURCING, "generation": hv.GENERATION,
        "platform_notes": hv.PLATFORM_NOTES,
        "path_id": path.id if path else None,
    }


class StateIn(BaseModel):
    kind: Literal["skill", "course", "step"]
    key: str
    value: int | str | bool


@router.put("/state")
def set_state(body: StateIn, db: Session = Depends(get_db)):
    """Your self-rating on a skill (0-4), your status on a course, or a playbook step ticked off."""
    st = _state(db)
    if body.kind == "skill":
        if body.key not in SKILL_NAMES or not isinstance(body.value, int) or not 0 <= body.value <= 4:
            raise HTTPException(400, "Unknown skill or level (0-4)")
        st["skills"][body.key] = body.value
    elif body.kind == "course":
        if body.key not in COURSE_IDS or body.value not in ("todo", "doing", "done"):
            raise HTTPException(400, "Unknown course or status")
        st["courses"][body.key] = body.value
    else:
        if body.key not in STEP_IDS:
            raise HTTPException(400, "Unknown playbook step")
        steps = set(st["steps"])
        steps.add(body.key) if body.value else steps.discard(body.key)
        st["steps"] = sorted(steps)
    _save_state(db, st)
    db.commit()
    return {"ok": True}


@router.post("/path")
def create_path(db: Session = Depends(get_db)):
    """Turn the technical modules into a study path: one module per technical module, one lesson per topic."""
    existing = _path(db)
    if existing:
        return {"path_id": existing.id, "created": False}
    top = db.scalar(select(func.max(LearningPath.position))) or 0
    lessons = sum(m["lessons"] for m in hv.MODULES)
    path = LearningPath(slug=hv.PATH_SLUG, title=hv.PATH_TITLE, summary=hv.PATH_SUMMARY, level="intermediate",
                        hours_per_week=5, weeks=max(1, math.ceil(lessons * 0.75 / 5)), status="ready",
                        position=top + 1, sources=["youtube", "arxiv", "semantic_scholar"])
    for mi, m in enumerate(hv.MODULES):
        mod = Module(idx=mi, title=m["title"], summary=m["summary"], keywords=[m["title"], "Hindi speech"],
                     paper_keywords=[m["title"]], objectives=[m["summary"]])
        topics = [t for _, ls in m["outline"] for t in ls]
        mod.lessons = [Lesson(idx=li, title=t, keywords=[t, "Hindi"], est_minutes=45,
                              objectives=[f"Explain and apply: {t}"]) for li, t in enumerate(topics)]
        path.modules.append(mod)
    db.add(path)
    db.flush()
    by_url = {c["url"]: c for c in hv.COURSES}
    for mod, m in zip(path.modules, hv.MODULES):
        for rank, url in enumerate([m["url"], *m["refs"]][:3]):
            c = by_url.get(url)
            is_paper = url.startswith(hv.ARXIV)
            paper = next((p for p in hv.PAPERS if p["url"] == url), None)
            res = upsert_resource(db, Candidate(
                kind="paper" if is_paper else "course" if c else "article",
                source="arxiv" if is_paper else "web",
                external_id=url.removeprefix(hv.ARXIV) if is_paper else url,
                title=(paper or c or {}).get("title") or url.split("//", 1)[-1].rstrip("/"), url=url,
                author=(c or {}).get("provider", ""), summary=(paper or {}).get("why") or (c or {}).get("covers", ""),
                year=(paper or {}).get("year"), meta={"hindi_voice": True}))
            for lesson in mod.lessons:
                attach(db, lesson.id, res.id, rank=rank, why="Key reference for this module.", added_by="seed")
    db.commit()
    return {"path_id": path.id, "created": True}


# ---------------------------------------------------------------- research refresh


class ResearchIn(BaseModel):
    months: int = Field(12, ge=1, le=36)


def _research_out(db: Session) -> dict:
    st = bgjobs.read(db.get(User, USER_ID), RESEARCH_KEY)
    out = bgjobs.public(st)
    return {"status": out["status"], "error": out["error"], "started_at": out["started_at"],
            "fetched_at": out["fetched_at"], "summary": st.get("summary", ""), "items": st.get("items", []),
            "dropped": st.get("dropped", 0), "months": (st.get("params") or {}).get("months", 12)}


@router.get("/research")
def get_research(db: Session = Depends(get_db)):
    return _research_out(db)


@router.post("/research/refresh")
async def refresh_research(body: ResearchIn | None = None, db: Session = Depends(get_db)):
    body = body or ResearchIn()
    known = [m["name"] for m in hv.MODELS] + [d["name"] for d in hv.DATASETS] + [p["title"] for p in hv.PAPERS]
    previous = {i["url"] for i in _research_out(db)["items"]}

    async def work(_prev: dict) -> dict:
        res = await find_research(get_llm(), known, months=body.months)
        res["items"] = [i | {"is_new": bool(previous) and i["url"] not in previous} for i in res["items"]]
        return res

    bgjobs.start(db, RESEARCH_KEY, work, months=body.months)
    return _research_out(db)


# ---------------------------------------------------------------- utterance generator


class UtterIn(BaseModel):
    intent: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_.]*$")
    description: str = Field("", max_length=400)
    slots: list[SlotSpec] = Field(default_factory=list, max_length=8)
    count: int = Field(30, ge=5, le=80)
    styles: list[Literal["devanagari", "romanized", "hinglish"]] = Field(default_factory=lambda: list(STYLES),
                                                                         min_length=1)


def _utter_out(db: Session) -> dict:
    st = bgjobs.read(db.get(User, USER_ID), UTTER_KEY)
    out = bgjobs.public(st)
    return {"status": out["status"], "error": out["error"], "started_at": out["started_at"],
            "fetched_at": out["fetched_at"], "items": st.get("items", []),
            "dropped_slots": st.get("dropped_slots", 0), "params": st.get("params")}


@router.get("/utterances")
def get_utterances(db: Session = Depends(get_db)):
    return _utter_out(db)


@router.post("/utterances/generate")
async def make_utterances(body: UtterIn, db: Session = Depends(get_db)):
    async def work(_prev: dict) -> dict:
        return await generate_utterances(get_llm(), body.intent, body.description, body.slots, body.count,
                                         list(body.styles))

    bgjobs.start(db, UTTER_KEY, work, **body.model_dump())
    return _utter_out(db)
