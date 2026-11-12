"""Interview companion agents: JD Analyst, Role Researcher, Skill Mapper, Prep Planner, Question Writer,
Mock Interviewer and Coach. Every source link they return is checked before it is stored."""

from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict

from .. import config
from ..llm import LLMClient
from ..providers import arxiv_by_ids, check_url
from .schemas import (JDAnalysisOut, MockGradeOut, PrepPlanOut, QuestionBatchOut, RoleResearchOut, SkillMapOut,
                      WrittenQuestion)
from .search import titles_match

log = logging.getLogger("study.interview")

QTYPE_LABEL = {
    "concept": "concept / deep-dive",
    "design": "system design",
    "scenario": "scenario / trade-off",
    "hands_on": "hands-on / coding",
    "behavioral": "behavioral / leadership",
}

BARS = {
    "top_ai": (
        "the hiring bar of top AI companies (frontier AI labs and AI-first big tech) for a {seniority}-level hire. "
        "Questions go beyond definitions: they probe first principles, real production trade-offs, failure modes, "
        "evaluation, safety, latency and cost, and ask for numbers and concrete designs. System design prompts are "
        "open-ended with ambiguous requirements the candidate must clarify. No trivia, no textbook one-liners."
    ),
    "big_tech": (
        "the bar of a large tech company hiring a {seniority}-level engineer/architect: solid depth, practical "
        "trade-offs and system design with clear requirements."
    ),
    "standard": (
        "a typical industry interview for a {seniority}-level role: clear fundamentals, practical experience and "
        "straightforward design questions."
    ),
}

SYSTEM = (
    "You are a principal AI architect who has interviewed hundreds of candidates for agentic AI roles. "
    "You are precise and current, and you never invent facts, products, papers or URLs."
)


def role_context(prep) -> str:
    lines = [f"Role: {prep.role_title}" + (f" at {prep.company}" if prep.company else ""),
             f"Level: {prep.seniority}"]
    if prep.background.strip():
        lines.append(f"Candidate background: {prep.background.strip()[:3000]}")
    if prep.focus_notes.strip():
        lines.append(f"Candidate's notes / focus areas: {prep.focus_notes.strip()[:1500]}")
    return "\n".join(lines)


def bar_text(prep) -> str:
    return BARS.get(prep.question_bar, BARS["top_ai"]).format(seniority=prep.seniority)


# ---------------------------------------------------------------- 1. JD Analyst

class JDAnalyst:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, prep) -> JDAnalysisOut:
        prompt = (f"{role_context(prep)}\n\nJob description:\n\"\"\"\n{prep.jd_text.strip()[:12000]}\n\"\"\"\n\n"
                  "Analyse this job description. Extract only what it actually says or clearly implies.")
        return await self.llm.ask_json(prompt, JDAnalysisOut, system=SYSTEM, model=config.LLM_MODEL)


# ---------------------------------------------------------------- 2. Role Researcher (web)

class RoleResearcher:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, prep, *, web: bool) -> RoleResearchOut:
        how = ("Search the web now: recent job postings for this title (2025-2026), interview guides and candidate "
               "reports, and engineering blogs about what the role does. Use only pages you actually opened, and list "
               "them as sources with their exact URLs." if web else
               "Web search is off: answer from your own knowledge and return an empty sources list.")
        prompt = (f"{role_context(prep)}\n\n{how}\n\nFind out what companies expect from a '{prep.role_title}' "
                  f"at {prep.seniority} level: responsibilities, the skills and technologies that keep appearing "
                  "(with how common they are), how the interviews are structured, and current trends interviewers "
                  "expect candidates to know.")
        return await self.llm.ask_json(prompt, RoleResearchOut, system=SYSTEM, model=config.LLM_MODEL, web=web,
                                       timeout=max(config.LLM_TIMEOUT, 600))


async def verify_sources(sources: list[dict]) -> list[dict]:
    """Keep sources whose page loads (or exists but blocks bots); drop dead links and duplicates."""
    seen, uniq = set(), []
    for s in sources:
        url = (s.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            uniq.append({"title": (s.get("title") or url).strip(), "url": url})
    states = await asyncio.gather(*(check_url(s["url"]) for s in uniq))
    return [{**s, "verified": st == "ok"} for s, st in zip(uniq, states) if st != "dead"]


# ---------------------------------------------------------------- 3. Skill Mapper

class SkillMapper:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, prep, jd: dict | None, research: dict | None) -> SkillMapOut:
        parts = [role_context(prep)]
        if jd:
            parts.append("Job description analysis (highest priority, this is the actual job):\n"
                         f"- Required: {', '.join(jd.get('required_skills', []))}\n"
                         f"- Nice to have: {', '.join(jd.get('nice_to_have', []))}\n"
                         f"- Responsibilities: {'; '.join(jd.get('responsibilities', []))}")
        if research:
            skills = "; ".join(f"{s['name']} ({s['note']})" for s in research.get("common_skills", []))
            parts.append("Market research for this role:\n"
                         f"- Summary: {research.get('role_summary', '')}\n- Common skills: {skills}\n"
                         f"- Interview format: {'; '.join(research.get('interview_format', []))}\n"
                         f"- Trends: {'; '.join(research.get('trends', []))}")
        parts.append(
            "Build the complete skill map a candidate must prepare for this interview: every skill and technology, "
            "grouped into 8-12 competency areas (e.g. agent architecture patterns, tools & protocols, frameworks, "
            "memory & retrieval, evaluation & observability, safety & governance, platform & LLMOps, system design, "
            "leadership). Name concrete technologies where interviewers expect them. Mark importance honestly: "
            "'must' only for things the interview will almost certainly test. Order areas and skills by importance.")
        return await self.llm.ask_json("\n\n".join(parts), SkillMapOut, system=SYSTEM, model=config.LLM_MODEL)


def group_by_area(skills: list) -> "OrderedDict[str, list]":
    areas: OrderedDict[str, list] = OrderedDict()
    for s in skills:
        areas.setdefault(s.area, []).append(s)
    return areas


# ---------------------------------------------------------------- 4. Prep Planner

class PrepPlanner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, prep, skills: list, *, weeks: int) -> PrepPlanOut:
        lines = []
        for area, items in group_by_area(skills).items():
            desc = ", ".join(f"{s.name} [{s.importance}{f', self-rating {s.self_rating}/5' if s.self_rating else ''}]"
                             for s in items)
            lines.append(f"- {area}: {desc}")
        total_min = prep.hours_per_week * weeks * 60
        prompt = (
            f"{role_context(prep)}\n\nInterview in about {weeks} week(s); {prep.hours_per_week} h/week to study.\n"
            f"Skill map:\n" + "\n".join(lines) + "\n\n"
            "Design the interview preparation course: 5-9 modules in study order, each with 3-5 lessons. Cover every "
            "'must' skill, most 'important' ones, and skip 'nice' ones if time is short. Spend more time where the "
            "candidate rated themselves low. End with a module on system design practice for this role. "
            f"Lesson study time should add up to roughly {int(total_min * 0.5)} minutes (the rest goes to videos, "
            "papers and mock interviews). Keywords must be short, searchable phrases.")
        return await self.llm.ask_json(prompt, PrepPlanOut, system=SYSTEM, model=config.LLM_MODEL)


# ---------------------------------------------------------------- 5. Question Writer

class QuestionWriter:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def for_area(self, prep, area: str, skills: list, *, count: int, qtypes: list[str],
                       difficulty: str | None = None, avoid: list[str] | None = None) -> list[WrittenQuestion]:
        skill_lines = "\n".join(f"- {s.name} [{s.importance}] — tested by: {s.how_tested}" for s in skills)
        types = ", ".join(f"{t} ({QTYPE_LABEL[t]})" for t in qtypes)
        diff = (f"All questions must be '{difficulty}' difficulty." if difficulty else
                "Mix difficulties to match the bar (mostly hard and expert for a top-company bar).")
        avoid_txt = ("\n\nDo not repeat or rephrase these existing questions:\n" + "\n".join(f"- {q}" for q in avoid[:60])
                     if avoid else "")
        prompt = (
            f"{role_context(prep)}\n\nWrite {count} interview questions for the competency area '{area}'.\n"
            f"Skills in this area:\n{skill_lines}\n\n"
            f"Bar: {bar_text(prep)}\n"
            f"Allowed question types: {types}. Spread across types and skills; weight 'must' skills more. {diff}\n\n"
            "For each question write a model answer a strong candidate would give (Markdown, structured, concrete, "
            "with trade-offs; cite sources inline as [1], [2] matching the references list), the key points used to "
            "grade, probing follow-ups and red flags.\n"
            "References: 1-4 real sources per question that back the answer — seminal arXiv papers (give the arXiv id "
            "and exact title), official documentation or specs (e.g. modelcontextprotocol.io, docs.anthropic.com, "
            "platform.openai.com/docs, langchain-ai.github.io/langgraph), or well-known engineering blog posts. Only "
            "include sources you are sure exist with that exact title and URL; every link is checked and wrong ones "
            "are removed." + avoid_txt)
        out = await self.llm.ask_json(prompt, QuestionBatchOut, system=SYSTEM, model=config.LLM_MODEL,
                                      timeout=max(config.LLM_TIMEOUT, 600))
        allowed = set(qtypes)
        return [q for q in out.questions if q.qtype in allowed and q.question.strip()]


async def verify_references(questions: list[WrittenQuestion]) -> list[list[dict]]:
    """Check every reference: arXiv papers by id + title match (title/url taken from arXiv), other links by loading
    them. Dead or mismatched references are dropped. Returns the kept references per question."""
    ids = sorted({r.arxiv_id.strip() for q in questions for r in q.references if r.arxiv_id.strip()})
    found = {}
    for i in range(0, len(ids), 20):
        for c in await arxiv_by_ids(ids[i:i + 20]):
            found[c.external_id] = c
    urls = sorted({r.url.strip() for q in questions for r in q.references if not r.arxiv_id.strip()})
    states = dict(zip(urls, await asyncio.gather(*(check_url(u) for u in urls))))

    out = []
    for q in questions:
        kept, seen = [], set()
        for r in q.references:
            aid = r.arxiv_id.strip()
            if aid:
                c = found.get(aid)
                if not c or not titles_match(r.title, c.title):
                    log.info("Dropped reference %s (%r): not on arXiv or title mismatch", aid, r.title)
                    continue
                ref = {"title": c.title, "url": f"https://arxiv.org/abs/{aid}", "kind": "paper", "verified": True,
                       "year": c.year, "authors": c.author}
            else:
                st = states.get(r.url.strip(), "dead")
                if st == "dead":
                    log.info("Dropped reference %s: dead link", r.url)
                    continue
                ref = {"title": r.title, "url": r.url.strip(), "kind": "web", "verified": st == "ok"}
            if ref["url"] not in seen:
                seen.add(ref["url"])
                kept.append(ref)
        out.append(kept)
    return out


# ---------------------------------------------------------------- 6. Mock Interviewer

class MockInterviewer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def grade(self, prep, q, answer: str) -> MockGradeOut:
        prompt = (
            f"{role_context(prep)}\nBar: {bar_text(prep)}\n\n"
            f"Interview question ({QTYPE_LABEL.get(q.qtype, q.qtype)}, {q.difficulty}):\n{q.question}\n\n"
            "Key points a strong answer covers:\n" + "\n".join(f"- {k}" for k in q.key_points) + "\n\n"
            f"Reference answer:\n{q.answer_md[:6000]}\n\n"
            f"Candidate's answer:\n\"\"\"\n{answer.strip()[:8000]}\n\"\"\"\n\n"
            "Grade the candidate as a demanding but fair interviewer at that bar. Credit correct ideas that differ "
            "from the reference. Be specific about what was missing or wrong. Write the stronger answer in the "
            "candidate's own voice, keeping what they did well.")
        out = await self.llm.ask_json(prompt, MockGradeOut, system=SYSTEM, model=config.LLM_MODEL)
        out.score = max(1, min(5, out.score))
        return out


# ---------------------------------------------------------------- 7. Coach

class Coach:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def today(self, prep, *, days_left: int | None, readiness: int, weak_skills: list[str],
                    needs_work: int, next_lesson: str | None) -> str:
        prompt = (
            f"{role_context(prep)}\n"
            f"Days until the interview: {days_left if days_left is not None else 'not set'}. "
            f"Readiness score: {readiness}%. Weakest must-have skills: {', '.join(weak_skills) or 'not rated yet'}. "
            f"Questions marked 'needs work': {needs_work}. Next lesson in the prep plan: {next_lesson or 'none'}.\n\n"
            "Write today's plan as 3 short Markdown bullets (what to study, what to practise, one tip), "
            "then one encouraging sentence. Under 90 words. No heading.")
        ans = await self.llm.ask(prompt, system=SYSTEM, model=config.LLM_FAST_MODEL)
        return ans.text.strip()
