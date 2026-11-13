"""Career tab: certifications (curated + LLM refresh) and hot jobs with JD breakdowns (LLM + web search)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import career
from ..agents.career import find_certifications, find_jobs
from ..db import get_db
from ..llm import get_llm
from ..models import User
from . import bgjobs
from .. import overlay
from ..auth import uid

router = APIRouter(prefix="/api/career", tags=["career"])

CERTS_KEY, JOBS_KEY = "certs", "jobs"
DEFAULT_ROLES = "Agentic AI Architect, AI Agent Engineer, Generative AI Architect, LLM / Applied AI Engineer"


def _state(db: Session, key: str) -> dict:
    return bgjobs.read(db.get(User, uid()), key)


# ---------------------------------------------------------------- certifications

def _certs_out(db: Session, st: dict) -> dict:
    pub = bgjobs.public(st)
    return {"checked_on": career.CHECKED_ON, "tiers": career.TIERS,
            "certs": overlay.apply(db, "career.certs", career.CERTS),
            "removed": overlay.hidden_count(db, "career.certs", career.CERTS),
            "refresh": {"status": pub["status"], "error": pub["error"], "started_at": pub["started_at"],
                        "fetched_at": pub["fetched_at"], "summary": st.get("summary", ""),
                        "items": st.get("items", []), "dropped": st.get("dropped", 0)}}


@router.get("/certifications")
def certifications(db: Session = Depends(get_db)):
    return _certs_out(db, _state(db, CERTS_KEY))


@router.post("/certifications/refresh")
async def refresh_certifications(db: Session = Depends(get_db)):
    known = [f"{c['name']} ({c['issuer']}{', ' + c['code'] if c['code'] else ''}; {c['price'] or 'price n/a'})"
             for c in career.CERTS]

    async def work(_prev: dict) -> dict:
        return await find_certifications(get_llm(), known)

    bgjobs.start(db, CERTS_KEY, work)
    return _certs_out(db, _state(db, CERTS_KEY))


# ---------------------------------------------------------------- jobs

class JobsIn(BaseModel):
    roles: str = Field(DEFAULT_ROLES, min_length=3, max_length=300)
    location: str = Field("", max_length=120)
    count: int = Field(10, ge=3, le=20)


def _jobs_out(st: dict) -> dict:
    pub = bgjobs.public(st)
    params = st.get("params") or {}
    return {"status": pub["status"], "error": pub["error"], "started_at": pub["started_at"],
            "fetched_at": pub["fetched_at"], "market_summary": st.get("market_summary", ""),
            "trends": st.get("trends", []), "jobs": st.get("jobs", []), "top_skills": st.get("top_skills", []),
            "dropped": st.get("dropped", 0),
            "params": {"roles": params.get("roles", DEFAULT_ROLES), "location": params.get("location", ""),
                       "count": params.get("count", 10)}}


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    return _jobs_out(_state(db, JOBS_KEY))


@router.post("/jobs/refresh")
async def refresh_jobs(body: JobsIn | None = None, db: Session = Depends(get_db)):
    body = body or JobsIn()

    async def work(_prev: dict) -> dict:
        return await find_jobs(get_llm(), body.roles, body.location, body.count)

    bgjobs.start(db, JOBS_KEY, work, roles=body.roles, location=body.location, count=body.count)
    return _jobs_out(_state(db, JOBS_KEY))
