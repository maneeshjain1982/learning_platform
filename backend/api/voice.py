"""Voice (ASR + NLU) tab, per language (hi, en): competencies, courses, technical modules, models, datasets,
papers, launch playbook, testing, data plan, an LLM research refresh and an utterance generator.

Review Q&A for the technical modules uses the shared Q&A endpoints in api/claude.py (slugs "hv-…", "ev-…").
"""

from __future__ import annotations

import math
from types import ModuleType
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents.base import attach, upsert_resource
from ..agents.voice import SlotSpec, find_research, generate_utterances
from ..db import get_db
from ..llm import get_llm
from ..models import AcademyQA, LearningPath, Lesson, Module, User
from ..providers import Candidate
from ..voice_langs import LANGS
from . import bgjobs
from .common import USER_ID, progress_map

router = APIRouter(prefix="/api/voice", tags=["voice"])


def _lang(code: str) -> ModuleType:
    lang = LANGS.get(code)
    if lang is None:
        raise HTTPException(404, f"No voice content for language '{code}'")
    return lang


@router.get("")
def languages():
    return [{"code": c, "name": l.NAME, "title": l.TITLE} for c, l in LANGS.items()]


def _state(db: Session, lang: ModuleType) -> dict:
    user = db.get(User, USER_ID)
    st = dict((user.settings or {}).get(lang.SETTINGS_KEY) or {})
    return {"skills": dict(st.get("skills") or {}), "courses": dict(st.get("courses") or {}),
            "steps": list(st.get("steps") or [])}


def _save_state(db: Session, lang: ModuleType, st: dict) -> None:
    user = db.get(User, USER_ID)
    user.settings = {**(user.settings or {}), lang.SETTINGS_KEY: st}  # reassign so SQLAlchemy sees the change


def _step_ids(lang: ModuleType) -> set[str]:
    return {f"{p['id']}:{i}" for p in lang.PLAYBOOK for i in range(len(p["steps"]))}


def _path(db: Session, lang: ModuleType) -> LearningPath | None:
    return db.scalars(select(LearningPath).where(LearningPath.slug == lang.PATH_SLUG)).first()


def _module_progress(db: Session, lang: ModuleType, path: LearningPath | None) -> dict[str, dict]:
    if path is None:
        return {}
    by_title = {m["title"]: m["slug"] for m in lang.MODULES}
    prog = progress_map(db, [l.id for m in path.modules for l in m.lessons])
    out = {}
    for m in path.modules:
        if slug := by_title.get(m.title):
            done = sum(1 for l in m.lessons if (p := prog.get(l.id)) and p.status == "done")
            out[slug] = {"done": done, "total": len(m.lessons)}
    return out


@router.get("/{code}")
def overview(code: str, db: Session = Depends(get_db)):
    lang = _lang(code)
    st = _state(db, lang)
    path = _path(db, lang)
    prog = _module_progress(db, lang, path)
    qa: dict[str, dict] = {}
    for slug, status, n in db.execute(select(AcademyQA.course_slug, AcademyQA.status, func.count())
                                      .where(AcademyQA.course_slug.like(f"{lang.SLUG_PREFIX}%"))
                                      .group_by(AcademyQA.course_slug, AcademyQA.status)):
        d = qa.setdefault(slug, {"total": 0, "known": 0, "review": 0})
        d["total"] += n
        if status in ("known", "review"):
            d[status] += n
    empty = {"total": 0, "known": 0, "review": 0}
    steps = _step_ids(lang)
    return {
        "code": lang.CODE, "name": lang.NAME, "title": lang.TITLE, "intro": lang.INTRO,
        "checked_on": lang.CHECKED_ON, "qa_sources": lang.QA_SOURCES,
        "competencies": [{"id": a["id"], "title": a["title"],
                          "skills": [{"name": n, "need": need, "why": why, "level": st["skills"].get(n, 0)}
                                     for n, need, why in a["skills"]]} for a in lang.COMPETENCIES],
        "phases": lang.PHASES,
        "courses": [{**c, "status": st["courses"].get(c["id"], "todo")} for c in lang.COURSES],
        "sides": lang.SIDES,
        "modules": [{**{k: v for k, v in m.items() if k != "outline"},
                     "outline": [{"title": t, "lessons": ls} for t, ls in m["outline"]],
                     "qa": qa.get(m["slug"], empty), "path_progress": prog.get(m["slug"])} for m in lang.MODULES],
        "model_kinds": lang.MODEL_KINDS, "models": lang.MODELS,
        "dataset_kinds": lang.DATASET_KINDS, "datasets": lang.DATASETS,
        "paper_topics": lang.PAPER_TOPICS, "papers": lang.PAPERS,
        "playbook": lang.PLAYBOOK, "steps_done": [s for s in st["steps"] if s in steps],
        "testing": lang.TESTING, "test_sizing": lang.TEST_SIZING,
        "variability": lang.VARIABILITY, "sourcing": lang.SOURCING, "generation": lang.GENERATION,
        "platform_notes": lang.PLATFORM_NOTES,
        "utter_styles": [{"id": k, "label": v[0], "help": v[1]} for k, v in lang.UTTER_STYLES.items()],
        "utter_default": lang.DEFAULT_UTTER,
        "path_id": path.id if path else None,
    }


class StateIn(BaseModel):
    kind: Literal["skill", "course", "step"]
    key: str
    value: int | str | bool


@router.put("/{code}/state")
def set_state(code: str, body: StateIn, db: Session = Depends(get_db)):
    """Your self-rating on a skill (0-4), your status on a course, or a playbook step ticked off."""
    lang = _lang(code)
    st = _state(db, lang)
    if body.kind == "skill":
        names = {s[0] for a in lang.COMPETENCIES for s in a["skills"]}
        if body.key not in names or isinstance(body.value, bool) or not isinstance(body.value, int) \
                or not 0 <= body.value <= 4:
            raise HTTPException(400, "Unknown skill or level (0-4)")
        st["skills"][body.key] = body.value
    elif body.kind == "course":
        if body.key not in {c["id"] for c in lang.COURSES} or body.value not in ("todo", "doing", "done"):
            raise HTTPException(400, "Unknown course or status")
        st["courses"][body.key] = body.value
    else:
        if body.key not in _step_ids(lang):
            raise HTTPException(400, "Unknown playbook step")
        steps = set(st["steps"])
        steps.add(body.key) if body.value else steps.discard(body.key)
        st["steps"] = sorted(steps)
    _save_state(db, lang, st)
    db.commit()
    return {"ok": True}


@router.post("/{code}/path")
def create_path(code: str, db: Session = Depends(get_db)):
    """Turn the technical modules into a study path: one module per technical module, one lesson per topic."""
    lang = _lang(code)
    existing = _path(db, lang)
    if existing:
        return {"path_id": existing.id, "created": False}
    top = db.scalar(select(func.max(LearningPath.position))) or 0
    lessons = sum(m["lessons"] for m in lang.MODULES)
    path = LearningPath(slug=lang.PATH_SLUG, title=lang.PATH_TITLE, summary=lang.PATH_SUMMARY, level="intermediate",
                        hours_per_week=5, weeks=max(1, math.ceil(lessons * 0.75 / 5)), status="ready",
                        position=top + 1, sources=["youtube", "arxiv", "semantic_scholar"])
    for mi, m in enumerate(lang.MODULES):
        mod = Module(idx=mi, title=m["title"], summary=m["summary"], keywords=[m["title"], f"{lang.NAME} speech"],
                     paper_keywords=[m["title"]], objectives=[m["summary"]])
        topics = [t for _, ls in m["outline"] for t in ls]
        mod.lessons = [Lesson(idx=li, title=t, keywords=[t, lang.NAME], est_minutes=45,
                              objectives=[f"Explain and apply: {t}"]) for li, t in enumerate(topics)]
        path.modules.append(mod)
    db.add(path)
    db.flush()
    by_url = {c["url"]: c for c in lang.COURSES}
    for mod, m in zip(path.modules, lang.MODULES):
        for rank, url in enumerate([m["url"], *m["refs"]][:3]):
            c = by_url.get(url)
            is_paper = url.startswith(lang.ARXIV)
            paper = next((p for p in lang.PAPERS if p["url"] == url), None)
            res = upsert_resource(db, Candidate(
                kind="paper" if is_paper else "course" if c else "article",
                source="arxiv" if is_paper else "web",
                external_id=url.removeprefix(lang.ARXIV) if is_paper else url,
                title=(paper or c or {}).get("title") or url.split("//", 1)[-1].rstrip("/"), url=url,
                author=(c or {}).get("provider", ""), summary=(paper or {}).get("why") or (c or {}).get("covers", ""),
                year=(paper or {}).get("year"), meta={"voice": lang.CODE}))
            for lesson in mod.lessons:
                attach(db, lesson.id, res.id, rank=rank, why="Key reference for this module.", added_by="seed")
    db.commit()
    return {"path_id": path.id, "created": True}


# ---------------------------------------------------------------- research refresh


class ResearchIn(BaseModel):
    months: int = Field(12, ge=1, le=36)


def _research_out(db: Session, lang: ModuleType) -> dict:
    st = bgjobs.read(db.get(User, USER_ID), f"{lang.JOB_PREFIX}-research")
    out = bgjobs.public(st)
    return {"status": out["status"], "error": out["error"], "started_at": out["started_at"],
            "fetched_at": out["fetched_at"], "summary": st.get("summary", ""), "items": st.get("items", []),
            "dropped": st.get("dropped", 0), "months": (st.get("params") or {}).get("months", 12)}


@router.get("/{code}/research")
def get_research(code: str, db: Session = Depends(get_db)):
    return _research_out(db, _lang(code))


@router.post("/{code}/research/refresh")
async def refresh_research(code: str, body: ResearchIn | None = None, db: Session = Depends(get_db)):
    lang = _lang(code)
    body = body or ResearchIn()
    known = [m["name"] for m in lang.MODELS] + [d["name"] for d in lang.DATASETS] + [p["title"] for p in lang.PAPERS]
    previous = {i["url"] for i in _research_out(db, lang)["items"]}

    async def work(_prev: dict) -> dict:
        res = await find_research(get_llm(), lang, known, months=body.months)
        res["items"] = [i | {"is_new": bool(previous) and i["url"] not in previous} for i in res["items"]]
        return res

    bgjobs.start(db, f"{lang.JOB_PREFIX}-research", work, months=body.months)
    return _research_out(db, lang)


# ---------------------------------------------------------------- utterance generator


class UtterIn(BaseModel):
    intent: str = Field(min_length=2, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_.]*$")
    description: str = Field("", max_length=400)
    slots: list[SlotSpec] = Field(default_factory=list, max_length=8)
    count: int = Field(30, ge=5, le=80)
    styles: list[str] = Field(min_length=1, max_length=6)


def _utter_out(db: Session, lang: ModuleType) -> dict:
    st = bgjobs.read(db.get(User, USER_ID), f"{lang.JOB_PREFIX}-utterances")
    out = bgjobs.public(st)
    return {"status": out["status"], "error": out["error"], "started_at": out["started_at"],
            "fetched_at": out["fetched_at"], "items": st.get("items", []),
            "dropped_slots": st.get("dropped_slots", 0), "params": st.get("params")}


@router.get("/{code}/utterances")
def get_utterances(code: str, db: Session = Depends(get_db)):
    return _utter_out(db, _lang(code))


@router.post("/{code}/utterances/generate")
async def make_utterances(code: str, body: UtterIn, db: Session = Depends(get_db)):
    lang = _lang(code)
    styles = list(dict.fromkeys(body.styles))
    if bad := [s for s in styles if s not in lang.UTTER_STYLES]:
        raise HTTPException(422, f"Unknown style(s) for {lang.NAME}: {', '.join(bad)}")

    async def work(_prev: dict) -> dict:
        return await generate_utterances(get_llm(), lang, body.intent, body.description, body.slots, body.count,
                                         styles)

    bgjobs.start(db, f"{lang.JOB_PREFIX}-utterances", work, **(body.model_dump() | {"styles": styles}))
    return _utter_out(db, lang)
