"""Study Companion API.

    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from . import config
from .api import bgjobs, router
from .api.common import spawn
from .auth import AuthMiddleware
from .db import init_db, session_scope
from .models import AgentRun, InterviewPrep, LearningPath, Lesson, Module, utcnow
from .seed import attach_seed_papers, seed_papers_missing, seed_structure

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("study")


def _recover_interrupted_work() -> None:
    """Work that was running when the server stopped can't continue; mark it so the UI can retry."""
    with session_scope() as db:
        for run in db.scalars(select(AgentRun).where(AgentRun.status == "running")):
            run.status, run.error, run.finished_at = "failed", "Interrupted by a server restart.", utcnow()
            for s in run.steps:
                if s.status in ("queued", "running"):
                    s.status = "skipped"
        for m in db.scalars(select(Module).where(Module.resources_status == "searching")):
            m.resources_status = "failed"
        for l in db.scalars(select(Lesson).where(Lesson.notes_status == "writing")):
            l.notes_status = "failed"
        for p in db.scalars(select(InterviewPrep).where(InterviewPrep.status == "building")):
            p.status = "ready" if p.skills else "failed"
        for path in db.scalars(select(LearningPath).where(LearningPath.status == "building")):
            path.status = "ready" if path.modules else "failed"
        bgjobs.recover_interrupted(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _recover_interrupted_work()
    with session_scope() as db:
        created = seed_structure(db)
        missing = seed_papers_missing(db)
    if created or missing:
        log.info("Cold boot: created %d seed paths; fetching their papers from arXiv in the background", len(created))
        spawn(attach_seed_papers())
    yield


app = FastAPI(title="Study Companion", version="0.1.0", lifespan=lifespan)
app.add_middleware(AuthMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
app.include_router(router)

# Serve the built frontend (npm run build) from the same server.
if config.FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        candidate = config.FRONTEND_DIST / full_path
        if full_path and candidate.is_file() and config.FRONTEND_DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(config.FRONTEND_DIST / "index.html")
