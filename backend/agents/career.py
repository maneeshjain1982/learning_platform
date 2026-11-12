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


async def find_jobs(llm: LLMClient, roles: str, location: str, count: int, today: date | None = None) -> dict:
    where = location.strip() or "any location; include remote roles"
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
