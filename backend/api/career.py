"""Career tab: certifications (curated + LLM refresh) and hot jobs with JD breakdowns (LLM + web search)."""

from __future__ import annotations

import base64
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import career
from ..agents.career import (FAANG, domain_roles, extract_profile, find_certifications, find_jobs,
                             find_reported_questions, search_jobs)
from .. import cv
from ..db import get_db
from ..llm import get_llm
from ..models import User, utcnow
from .common import iso
from ..domains_seed import slugify
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
    country: str = Field("", max_length=60, description="Country name, 'Remote' or empty for anywhere")
    location: str = Field("", max_length=120, description="Optional city or region")
    count: int = Field(10, ge=3, le=20)


def _jobs_out(st: dict) -> dict:
    pub = bgjobs.public(st)
    params = st.get("params") or {}
    return {"status": pub["status"], "error": pub["error"], "started_at": pub["started_at"],
            "fetched_at": pub["fetched_at"], "market_summary": st.get("market_summary", ""),
            "trends": st.get("trends", []), "jobs": st.get("jobs", []), "top_skills": st.get("top_skills", []),
            "dropped": st.get("dropped", 0),
            "params": {"roles": params.get("roles", DEFAULT_ROLES), "country": params.get("country", ""),
                       "location": params.get("location", ""), "count": params.get("count", 10)}}


@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    return _jobs_out(_state(db, JOBS_KEY))


@router.post("/jobs/refresh")
async def refresh_jobs(body: JobsIn | None = None, db: Session = Depends(get_db)):
    body = body or JobsIn()

    async def work(_prev: dict) -> dict:
        return await find_jobs(get_llm(), body.roles, body.location, body.count, country=body.country)

    bgjobs.start(db, JOBS_KEY, work, roles=body.roles, country=body.country, location=body.location,
                 count=body.count)
    return _jobs_out(_state(db, JOBS_KEY))


# ---------------------------------------------------------------- your profile (from a CV)

PROFILE = "career_profile"


def get_profile(db: Session) -> dict | None:
    return (db.get(User, uid()).settings or {}).get(PROFILE)


def _save_profile(db: Session, profile: dict | None) -> None:
    user = db.get(User, uid())
    settings = dict(user.settings or {})
    if profile is None:
        settings.pop(PROFILE, None)
    else:
        settings[PROFILE] = profile
    user.settings = settings
    db.commit()


class CVIn(BaseModel):
    filename: str = Field("cv.txt", max_length=200)
    content_b64: str = Field("", max_length=8_000_000, description="The file, base64-encoded")
    text: str = Field("", max_length=30_000, description="Or the CV pasted as text")


@router.get("/profile")
def profile(db: Session = Depends(get_db)):
    return {"profile": get_profile(db)}


@router.post("/profile/cv")
async def upload_cv(body: CVIn, db: Session = Depends(get_db)):
    """Read the CV here, remove contact details, then let the LLM write the profile. The file isn't kept."""
    try:
        if body.text.strip():
            text = cv.extract_text("cv.txt", body.text.encode("utf-8"))
        else:
            text = cv.extract_text(body.filename, base64.b64decode(body.content_b64 or "", validate=False))
    except (cv.CVError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    clean = cv.strip_contacts(text)
    try:
        prof = await extract_profile(get_llm(), clean)
    except Exception as exc:
        raise HTTPException(502, f"Couldn't read the CV: {exc}") from exc
    prof |= {"cv_name": body.filename if not body.text.strip() else "Pasted text",
             "cv_text": clean, "updated_at": iso(utcnow())}
    _save_profile(db, prof)
    return {"profile": prof}


class ProfilePatch(BaseModel):
    headline: str | None = Field(None, max_length=200)
    years: int | None = Field(None, ge=0, le=60)
    level: str | None = Field(None, max_length=20)
    domains: list[str] | None = Field(None, max_length=10)
    skills: list[str] | None = Field(None, max_length=60)
    roles: list[str] | None = Field(None, max_length=10)
    summary: str | None = Field(None, max_length=2000)


@router.put("/profile")
def edit_profile(body: ProfilePatch, db: Session = Depends(get_db)):
    prof = dict(get_profile(db) or {"headline": "", "years": 0, "level": "senior", "domains": [], "skills": [],
                                     "roles": [], "summary": "", "highlights": []})
    for k, v in body.model_dump(exclude_none=True).items():
        prof[k] = [x.strip() for x in v if x.strip()] if isinstance(v, list) else (v.strip() if isinstance(v, str) else v)
    _save_profile(db, prof)
    return {"profile": prof}


@router.delete("/profile")
def delete_profile(db: Session = Depends(get_db)):
    _save_profile(db, None)
    return {"profile": None}


# ---------------------------------------------------------------- job search (your CV, a query or a domain)

SEARCH_KEY = "job-search"
PARAMS = ("use_profile", "query", "domain", "country", "location", "count", "years", "level", "work_mode",
          "company_type", "posted_days", "min_salary", "visa", "extra")


class SearchIn(BaseModel):
    use_profile: bool = Field(False, description="Search for jobs that match my CV")
    query: str = Field("", max_length=300, description="Role, company or keywords")
    domain: str = Field("", max_length=120, description="Domain name, e.g. 'Voice AI'")
    country: str = Field("", max_length=60)
    location: str = Field("", max_length=120)
    count: int = Field(8, ge=3, le=20)
    years: int | None = Field(None, ge=0, le=60)
    level: str = Field("", max_length=20)
    work_mode: Literal["any", "remote", "hybrid", "onsite"] = "any"
    company_type: Literal["any", "big_tech", "startup", "enterprise"] = "any"
    posted_days: Literal[7, 14, 30] = 30
    min_salary: str = Field("", max_length=60)
    visa: bool = False
    extra: str = Field("", max_length=300, description="Anything else, e.g. 'speech products', 'no defence'")


@router.get("/search")
def job_search(db: Session = Depends(get_db)):
    st = _state(db, SEARCH_KEY)
    out = _jobs_out(st)
    params = st.get("params") or {}
    defaults = SearchIn().model_dump()
    out["params"] = {k: params.get(k, defaults[k]) for k in PARAMS}
    out["matched"] = st.get("matched", False)
    return out


@router.post("/search")
async def run_job_search(body: SearchIn, db: Session = Depends(get_db)):
    prof = get_profile(db) if body.use_profile else None
    if body.use_profile and not prof:
        raise HTTPException(422, "Add your CV first.")
    if not prof and not body.query.strip() and not body.domain.strip():
        raise HTTPException(422, "Type what to search for, pick a domain, or search with your CV.")
    if prof and not body.query.strip() and not body.domain.strip():
        roles = ", ".join(prof.get("roles") or [prof.get("headline", "")])
    else:
        roles = domain_roles(body.domain, body.query)
    filters = body.model_dump(include={"years", "level", "work_mode", "company_type", "posted_days", "min_salary",
                                       "visa", "extra"})
    if prof:
        filters["years"] = filters["years"] or prof.get("years")
        filters["level"] = filters["level"] or prof.get("level", "")
    profile_for_llm = {k: v for k, v in (prof or {}).items() if k not in ("cv_text", "cv_name", "updated_at")} or None

    async def work(_prev: dict) -> dict:
        return await search_jobs(get_llm(), roles=roles, country=body.country, location=body.location,
                                 count=body.count, filters=filters, profile=profile_for_llm)

    bgjobs.start(db, SEARCH_KEY, work, **body.model_dump())
    return job_search(db)


# ---------------------------------------------------------------- FAANG sample questions (publicly reported)

class FaangIn(BaseModel):
    company: str = Field(min_length=2, max_length=60)
    role: str = Field("", max_length=120)
    domain: str = Field("", max_length=120)
    count: int = Field(10, ge=3, le=20)


def _faang_out(st: dict, company: str) -> dict:
    pub = bgjobs.public(st)
    return {"company": company, "status": pub["status"], "error": pub["error"], "started_at": pub["started_at"],
            "fetched_at": pub["fetched_at"], "process": st.get("process", ""), "questions": st.get("questions", []),
            "dropped": st.get("dropped", 0), "params": st.get("params") or {}}


@router.get("/faang")
def faang(company: str = "", db: Session = Depends(get_db)):
    user = db.get(User, uid())
    if not company:
        loaded = {c: bgjobs.read(user, f"faang-{slugify(c)}").get("fetched_at") for c in FAANG}
        return {"companies": FAANG, "loaded": {c: bgjobs.public({"fetched_at": t}).get("fetched_at")
                                                for c, t in loaded.items()}}
    return _faang_out(bgjobs.read(user, f"faang-{slugify(company)}"), company)


@router.post("/faang/refresh")
async def refresh_faang(body: FaangIn, db: Session = Depends(get_db)):
    company = body.company.strip()

    async def work(_prev: dict) -> dict:
        return await find_reported_questions(get_llm(), company, body.role, body.domain, body.count)

    bgjobs.start(db, f"faang-{slugify(company)}", work, **body.model_dump())
    return faang(company, db)
