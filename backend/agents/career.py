"""Career research agents: new certifications, and live job postings with JD breakdowns.

Both use web search. Every link is checked: dead links are dropped, links whose site blocks automated checks
(LinkedIn and most job boards do) are kept but marked unverified.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from ..providers import check_url

log = logging.getLogger("study.career")
TIMEOUT = max(config.LLM_TIMEOUT, 600)


async def _check(items: list[dict]) -> tuple[list[dict], int]:
    seen, uniq = set(), []
    for it in items:
        url = (it.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            uniq.append(it | {"url": url})
    states = await asyncio.gather(*(check_url(i["url"]) for i in uniq))
    kept = [i | {"verified": st == "ok"} for i, st in zip(uniq, states) if st != "dead"]
    return kept, len(uniq) - len(kept)


# ---------------------------------------------------------------- certifications

class CertFind(BaseModel):
    name: str
    issuer: str
    code: str = Field("", description="Exam code if any")
    tier: Literal["architect", "developer", "courses", "foundational"]
    change: Literal["new", "updated"] = Field(description="'new' if not in the known list, 'updated' if it is "
                                                          "but price, format, status or syllabus changed")
    what_changed: str = Field(description="For 'updated': what changed. For 'new': when it launched")
    price: str = ""
    format: str = ""
    focus: str = Field(description="What it tests, 1-2 sentences")
    fit: str = Field(description="One sentence on its value for an Agentic AI Architect")
    url: str = Field(description="Official page URL you opened")


class CertFindOut(BaseModel):
    summary: str = Field(description="One or two sentences on how the certification landscape changed")
    items: list[CertFind] = Field(description="0-12 new or updated certifications")


CERT_SYSTEM = (
    "You track professional certifications for Agentic AI and Generative AI engineers and architects. Use web "
    "search, open official issuer pages, and report only what you verified there. Never invent prices, codes, "
    "dates or URLs."
)


async def find_certifications(llm: LLMClient, known: list[str], today: date | None = None) -> dict:
    listing = "\n".join(f"- {k}" for k in known)
    prompt = (
        f"Today is {(today or date.today()).isoformat()}. Below are certifications I already track. Find:\n"
        "1. NEW Agentic AI or Generative AI certifications or certificate programs worth considering "
        "(cloud vendors, model labs, NVIDIA, Databricks, Salesforce, LangChain, IBM, universities...), and\n"
        "2. UPDATES to the ones below: price change, retirement, new exam version, opened to the public, "
        "general availability.\n"
        "Skip anything unchanged. Quality over quantity.\n\nKnown list:\n" + listing
    )
    out = await llm.ask_json(prompt, CertFindOut, system=CERT_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    kept, dropped = await _check([i.model_dump() for i in out.items])
    return {"summary": out.summary, "items": kept, "dropped": dropped}


# ---------------------------------------------------------------- jobs

class JobPosting(BaseModel):
    title: str
    company: str
    location: str = Field(description="City and country, or 'Remote (region)'")
    work_mode: Literal["remote", "hybrid", "onsite", "unknown"] = "unknown"
    seniority: str = Field("", description="e.g. Senior, Staff, Principal, Lead, Director")
    posted: str = Field("", description="Posting date as YYYY-MM-DD if shown, else empty")
    salary: str = Field("", description="Salary range exactly as posted, else empty")
    url: str = Field(description="URL of the job posting itself (company careers page preferred)")
    summary: str = Field(description="2-3 sentences: what the person will build and own")
    responsibilities: list[str] = Field(description="3-6 key responsibilities from the JD")
    must_have: list[str] = Field(description="Required skills and technologies from the JD")
    nice_to_have: list[str] = Field(default_factory=list)
    skill_tags: list[str] = Field(description="4-10 short canonical tags for the skills this JD asks for, e.g. "
                                              "'Python', 'MCP', 'RAG', 'LangGraph', 'Evals', 'Multi-agent', "
                                              "'Kubernetes', 'AWS'. Reuse the same spelling across jobs")
    why_hot: str = Field("", description="One short phrase on why this role stands out")


class JobSearchOut(BaseModel):
    market_summary: str = Field(description="3-4 sentences on what employers are hiring for right now")
    trends: list[str] = Field(description="3-6 hiring trends seen across these postings")
    jobs: list[JobPosting]


JOB_SYSTEM = (
    "You are a technical recruiter researching live job postings for Agentic AI and Generative AI roles. Use web "
    "search. Only include postings you actually opened and that are still open; never invent a company, posting "
    "or URL. Prefer the company's own careers page or its ATS (Greenhouse, Lever, Ashby, Workday) over "
    "aggregators. Summarise each JD faithfully: do not add skills it doesn't mention."
)


def job_location(country: str, city: str = "") -> str:
    """Where to search, in words for the prompt."""
    country, city = country.strip(), city.strip()
    if not country or country.lower() in ("any", "anywhere"):
        return city or "any location; include remote roles"
    if country.lower().startswith("remote"):
        return "remote roles only (any country)"
    where = f"{city}, {country}" if city else country
    return (f"{where}. Only include postings based in {country} or remote roles open to candidates living in "
            f"{country}")


async def find_jobs(llm: LLMClient, roles: str, location: str, count: int, today: date | None = None,
                    country: str = "") -> dict:
    where = job_location(country, location)
    prompt = (
        f"Today is {(today or date.today()).isoformat()}. Find {count} of the most attractive OPEN job postings "
        f"from the last 30 days for these roles: {roles}.\nLocation: {where}.\n"
        "Favour senior/staff/principal/architect level roles at AI labs, big tech, well-funded startups and "
        "enterprises building agent platforms. Break down each JD. Then summarise the market across them."
    )
    out = await llm.ask_json(prompt, JobSearchOut, system=JOB_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    kept, dropped = await _check([j.model_dump() for j in out.jobs])
    kept.sort(key=lambda j: j["posted"] or "", reverse=True)
    skills = Counter(t for j in kept for t in {s.strip() for s in j["skill_tags"] if s.strip()})
    return {"market_summary": out.market_summary, "trends": out.trends, "jobs": kept, "dropped": dropped,
            "top_skills": [{"skill": s, "count": n} for s, n in skills.most_common(15)]}


def domain_roles(domain: str, query: str = "") -> str:
    """Roles to search for: the typed query, or the usual roles for a domain."""
    query, domain = query.strip(), domain.strip()
    if query and domain:
        return f"{query} (in the {domain} field)"
    if query:
        return query
    return (f"{domain} roles: {domain} Engineer, {domain} Architect, Senior/Staff {domain} Engineer, {domain} "
            "Research Engineer or Scientist, Applied AI Engineer working on {domain}").replace("{domain}", domain)



# ---------------------------------------------------------------- your profile (from a CV) and matched search

class CVProfile(BaseModel):
    headline: str = Field(description="Current or most recent title, e.g. 'Senior ML Engineer, speech'")
    years: int = Field(description="Total years of professional experience")
    level: Literal["junior", "mid", "senior", "staff", "principal", "lead", "manager", "director"] = "senior"
    domains: list[str] = Field(description="2-5 fields of work, e.g. 'Voice AI', 'LLM', 'Agentic AI'")
    skills: list[str] = Field(description="10-25 skills and technologies, most used first, short canonical names")
    roles: list[str] = Field(description="3-5 job titles this person should search for next")
    summary: str = Field(description="2-3 sentences: what this person has built and is strongest at")
    highlights: list[str] = Field(default_factory=list, description="2-5 notable achievements, with numbers")


PROFILE_SYSTEM = (
    "You read a CV and write a short structured profile for job search. Work only from the CV; don't guess "
    "skills it doesn't show. Contact details have been removed; never try to restore them."
)


async def extract_profile(llm: LLMClient, cv_text: str) -> dict:
    out = await llm.ask_json(f"CV:\n{cv_text}\n\nWrite the profile.", CVProfile, system=PROFILE_SYSTEM,
                             model=config.LLM_MODEL, web=False, timeout=TIMEOUT)
    return out.model_dump()


class MatchedJob(JobPosting):
    match: int = Field(0, ge=0, le=100, description="How well the candidate fits this JD, 0-100")
    fits: list[str] = Field(default_factory=list, description="1-3 reasons the candidate fits")
    gaps: list[str] = Field(default_factory=list, description="0-3 things the JD asks for that the candidate lacks")


class MatchedSearchOut(BaseModel):
    market_summary: str = Field(description="3-4 sentences on what employers are hiring for right now")
    trends: list[str] = Field(description="3-6 hiring trends seen across these postings")
    jobs: list[MatchedJob]


def profile_brief(p: dict) -> str:
    """The profile as prompt text. Holds no contact details."""
    return "\n".join(x for x in [
        f"Candidate: {p.get('headline', '')}, {p.get('years', '?')} years, {p.get('level', '')} level",
        f"Fields: {', '.join(p.get('domains') or [])}" if p.get("domains") else "",
        f"Skills: {', '.join(p.get('skills') or [])}" if p.get("skills") else "",
        f"Strengths: {p.get('summary', '')}" if p.get("summary") else "",
        f"Highlights: {'; '.join(p.get('highlights') or [])}" if p.get("highlights") else "",
    ] if x)


COMPANY_TYPES = {"big_tech": "big tech and large AI labs", "startup": "startups and scale-ups",
                 "enterprise": "enterprises and consultancies"}


def search_filters(f: dict) -> str:
    """Filters as prompt lines."""
    out = []
    if f.get("years"):
        out.append(f"Experience: roles suited to about {f['years']} years of experience")
    if f.get("level"):
        out.append(f"Level: {f['level']}")
    if f.get("work_mode") and f["work_mode"] != "any":
        out.append(f"Work mode: {f['work_mode']} only")
    if f.get("company_type") in COMPANY_TYPES:
        out.append(f"Companies: {COMPANY_TYPES[f['company_type']]}")
    if f.get("min_salary"):
        out.append(f"Salary: at least {f['min_salary']} where the posting shows pay (keep postings without pay)")
    if f.get("visa"):
        out.append("Only roles that offer visa sponsorship or relocation")
    if f.get("extra"):
        out.append(f"Also: {f['extra']}")
    return "\n".join(f"- {x}" for x in out)


async def search_jobs(llm: LLMClient, *, roles: str, country: str, location: str, count: int,
                      filters: dict, profile: dict | None, today: date | None = None) -> dict:
    """Job search with filters; with a profile, every job gets a match score, fits and gaps, best match first."""
    where = job_location(country, location)
    days = filters.get("posted_days") or 30
    flines = search_filters(filters)
    prompt = (f"Today is {(today or date.today()).isoformat()}. Find {count} OPEN job postings from the last {days} "
              f"days for: {roles}.\nLocation: {where}.\n" + (f"Filters:\n{flines}\n" if flines else ""))
    if profile:
        prompt += ("\nThe candidate (search with these skills and level; never put personal details in a "
                   f"search):\n{profile_brief(profile)}\n\nFind the postings this candidate fits best. Search "
                   "each of the candidate's target roles and close variants across company career pages and job "
                   f"boards, and aim to return all {count}: include good partial fits with a lower score rather than "
                   "returning only a few. Score each honestly against its JD, say why it fits and what's missing. Break down each JD, then "
                   "summarise the market across them.")
        schema = MatchedSearchOut
    else:
        prompt += "Break down each JD. Then summarise the market across them."
        schema = JobSearchOut
    out = await llm.ask_json(prompt, schema, system=JOB_SYSTEM, model=config.LLM_MODEL, web=True, timeout=TIMEOUT)
    kept, dropped = await _check([j.model_dump() for j in out.jobs])
    if profile:
        kept.sort(key=lambda j: -(j.get("match") or 0))
    else:
        kept.sort(key=lambda j: j["posted"] or "", reverse=True)
    skills = Counter(t for j in kept for t in {s.strip() for s in j["skill_tags"] if s.strip()})
    return {"market_summary": out.market_summary, "trends": out.trends, "jobs": kept, "dropped": dropped,
            "top_skills": [{"skill": s, "count": n} for s, n in skills.most_common(15)], "matched": bool(profile)}


# ---------------------------------------------------------------- FAANG sample questions

FAANG = ["Google", "Meta", "Amazon", "Apple", "Netflix", "Microsoft"]


class ReportedQuestion(BaseModel):
    question: str
    round: Literal["coding", "system_design", "ml_design", "ml_concepts", "behavioral", "domain"] = "domain"
    role: str = Field("", description="Role it was asked for, e.g. 'ML Engineer, L5'")
    difficulty: Literal["medium", "hard", "very_hard"] = "hard"
    answer_outline: list[str] = Field(description="3-6 bullets: what a strong answer covers")
    source_name: str = Field(description="Where it was reported, e.g. 'Glassdoor', 'Blind', 'company prep guide'")
    url: str = Field(description="URL of the page where you found it")
    year: int | None = Field(None, description="Year reported, if shown")


class ReportedOut(BaseModel):
    process: str = Field(description="2-3 sentences: how this company's interview loop for these roles works now")
    questions: list[ReportedQuestion]


FAANG_SYSTEM = (
    "You research publicly reported interview questions for senior AI/ML roles. Use web search. Include only "
    "questions you found on a page you opened (company interview-prep pages, Glassdoor, Blind, Levels.fyi, "
    "LeetCode discuss, engineering blogs, candidate write-ups). Never invent a question, a source or a URL; never "
    "include confidential or leaked material. Rewrite each question in one clear sentence."
)


async def find_reported_questions(llm: LLMClient, company: str, role: str, domain: str, count: int) -> dict:
    prompt = (f"Find {count} interview questions reported for {company} for {role or 'senior AI/ML engineer'} roles"
              + (f" related to {domain}" if domain else "")
              + ", from the last 3 years. Cover several rounds (ML/system design, concepts, coding, behavioral). "
                "For each, outline what a strong answer covers.")
    out = await llm.ask_json(prompt, ReportedOut, system=FAANG_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    kept, dropped = await _check([q.model_dump() for q in out.questions])
    return {"process": out.process, "questions": kept, "dropped": dropped}
