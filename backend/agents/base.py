"""Shared helpers for agents: step logging (for the progress UI) and resource storage."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import session_scope
from ..models import AgentRun, AgentStep, LessonResource, Resource, utcnow
from ..providers import Candidate

log = logging.getLogger("study.agents")

AGENT_NAMES = {
    "topic": "Topic Identifier",
    "curriculum": "Curriculum Planner",
    "videos": "Video Search",
    "papers": "Paper Search",
    "curator": "Curator",
    "home": "Home Composer",
    "notes": "Lesson Writer",
    # interview companion
    "jd": "JD Analyst",
    "research": "Role Researcher",
    "skills": "Skill Mapper",
    "plan": "Prep Planner",
    "questions": "Question Writer",
    "coach": "Coach",
}


class StepRecorder:
    """Writes each agent step to the DB in its own transaction, so polling clients see live progress."""

    def __init__(self, run_id: int):
        self.run_id = run_id

    @classmethod
    def create_run(cls, kind: str, steps: list[str], *, requirement_id: int | None = None,
                   path_id: int | None = None, interview_id: int | None = None) -> "StepRecorder":
        with session_scope() as db:
            run = AgentRun(kind=kind, requirement_id=requirement_id, path_id=path_id, interview_id=interview_id,
                           status="running")
            run.steps = [AgentStep(agent=AGENT_NAMES[s], status="queued") for s in steps]
            db.add(run)
            db.flush()
            return cls(run.id)

    def _step(self, db: Session, key: str) -> AgentStep:
        return db.scalars(select(AgentStep).where(AgentStep.run_id == self.run_id,
                                                  AgentStep.agent == AGENT_NAMES[key])).one()

    def start(self, key: str, summary: str = "") -> None:
        with session_scope() as db:
            s = self._step(db, key)
            s.status, s.summary, s.started_at = "running", summary, utcnow()

    def update(self, key: str, summary: str | None = None, chips: list[str] | None = None) -> None:
        with session_scope() as db:
            s = self._step(db, key)
            if summary is not None:
                s.summary = summary
            if chips is not None:
                s.chips = chips[:12]

    def done(self, key: str, summary: str, chips: list[str] | None = None, status: str = "done") -> None:
        with session_scope() as db:
            s = self._step(db, key)
            s.status, s.summary, s.finished_at = status, summary, utcnow()
            if chips is not None:
                s.chips = chips[:12]

    def fail(self, key: str, error: str) -> None:
        self.done(key, error[:500], status="failed")

    def set_path(self, path_id: int) -> None:
        with session_scope() as db:
            db.get(AgentRun, self.run_id).path_id = path_id

    def finish(self, error: str | None = None) -> None:
        with session_scope() as db:
            run = db.get(AgentRun, self.run_id)
            run.status = "failed" if error else "done"
            run.error = error
            run.finished_at = utcnow()
            for s in run.steps:
                if s.status in ("queued", "running"):
                    s.status = "skipped" if error else "done"


def upsert_resource(db: Session, c: Candidate) -> Resource:
    res = db.scalars(select(Resource).where(Resource.source == c.source,
                                            Resource.external_id == c.external_id)).first()
    if res is None:
        res = Resource(kind=c.kind, source=c.source, external_id=c.external_id, title=c.title, url=c.url)
        db.add(res)
    res.title = c.title or res.title
    res.url = c.url or res.url
    res.author = c.author or res.author or ""
    res.year = c.year or res.year
    res.summary = c.summary or res.summary or ""
    res.thumbnail = c.thumbnail or res.thumbnail
    res.duration_min = c.duration_min or res.duration_min
    res.meta = {**(res.meta or {}), **{k: v for k, v in c.meta.items() if v is not None}}
    res.fetched_at = utcnow()
    db.flush()
    return res


def attach(db: Session, lesson_id: int, resource_id: int, *, rank: int = 0, why: str = "",
           added_by: str = "agent") -> None:
    link = db.get(LessonResource, (lesson_id, resource_id))
    if link is None:
        db.add(LessonResource(lesson_id=lesson_id, resource_id=resource_id, rank=rank, why=why, added_by=added_by))
    else:
        link.rank, link.why = rank, why or link.why
    db.flush()
