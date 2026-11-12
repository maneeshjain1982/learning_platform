from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import orchestrator
from ..db import get_db
from ..models import AgentRun, LearningPath, LearningRequirement
from .common import USER_ID, get_or_404, lesson_resources, path_summary, progress_map, run_out, saved_ids, spawn

router = APIRouter(prefix="/api", tags=["paths"])


class RequirementIn(BaseModel):
    raw_text: str = Field(min_length=10, max_length=4000)
    goal: Literal["understand", "build", "interview", "research"] = "understand"
    level: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    hours_per_week: int = Field(5, ge=1, le=60)
    weeks: int = Field(6, ge=1, le=52)
    formats: list[str] = []
    sources: list[str] = ["youtube", "coursera", "udemy", "arxiv", "semantic_scholar"]


@router.post("/requirements")
async def create_requirement(body: RequirementIn, db: Session = Depends(get_db)):
    req = LearningRequirement(user_id=USER_ID, **body.model_dump())
    db.add(req)
    db.commit()
    run_id = orchestrator.start_build(req.id)
    spawn(orchestrator.run_build(run_id, req.id))
    return {"requirement_id": req.id, "run_id": run_id}


@router.get("/agent-runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db)):
    return run_out(get_or_404(db, AgentRun, run_id))


@router.get("/agent-runs")
def list_runs(active: bool = False, db: Session = Depends(get_db)):
    q = select(AgentRun).order_by(AgentRun.id.desc()).limit(20)
    if active:
        q = q.where(AgentRun.status == "running")
    return [run_out(r) for r in db.scalars(q)]


@router.get("/paths")
def list_paths(db: Session = Depends(get_db)):
    paths = db.scalars(select(LearningPath).order_by(LearningPath.position, LearningPath.id)).all()
    return [path_summary(db, p) for p in paths]


@router.get("/paths/{path_id}")
def get_path(path_id: int, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    lessons = [l for m in path.modules for l in m.lessons]
    prog = progress_map(db, [l.id for l in lessons])
    res = lesson_resources(db, [l.id for l in lessons], saved_ids(db))
    out = path_summary(db, path)
    out["module_list"] = [{
        "id": m.id, "idx": m.idx, "title": m.title, "summary": m.summary, "objectives": m.objectives,
        "keywords": m.keywords, "resources_status": m.resources_status,
        "lessons": [{
            "id": l.id, "idx": l.idx, "title": l.title, "est_minutes": l.est_minutes, "objectives": l.objectives,
            "status": prog[l.id].status if l.id in prog else "todo",
            "videos": sum(1 for r in res[l.id] if r["kind"] == "video"),
            "papers": sum(1 for r in res[l.id] if r["kind"] == "paper"),
        } for l in m.lessons],
    } for m in path.modules]
    return out


class FindResourcesIn(BaseModel):
    module_ids: list[int] | None = None


@router.post("/paths/{path_id}/find-resources")
async def find_resources(path_id: int, body: FindResourcesIn | None = None, db: Session = Depends(get_db)):
    path = get_or_404(db, LearningPath, path_id)
    running = db.scalars(select(AgentRun).where(AgentRun.path_id == path_id, AgentRun.status == "running")).first()
    if running:
        raise HTTPException(409, "Agents are already working on this path.")
    module_ids = body.module_ids if body else None
    run_id = orchestrator.start_find_resources(path.id)
    spawn(orchestrator.run_find_resources(run_id, path.id, module_ids=module_ids))
    return {"run_id": run_id}
