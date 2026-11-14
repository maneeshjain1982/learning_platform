"""First start of the Domains design: build the four starting domains from the content the app already has.

- Gen AI      : the admin's own learning paths (e.g. the RAG app path)
- LLM         : LLM Fundamentals path + Claude Academy courses outside the agent track
- Agentic AI  : Agentic AI and Agentic Harness paths + the Claude Academy agent builder track
- Voice AI    : the Hindi and English voice content (modules, models, datasets, papers, courses, playbook)

Runs once (marker in the admin's settings), so domains the admin deletes don't come back. No network.
Topics built from outlines start as 'draft': their executive summary is written the first time someone opens them.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import claude_academy as ca
from .agents.domains import source_row
from .models import Domain, DomainSection, LearningPath, LessonResource, Topic, TopicSource, User
from .voice_langs import LANGS

MARKER = "domains_seeded"

DOMAINS = [
    ("gen-ai", "Gen AI", "Generative AI applications: RAG, prompting, multimodal generation and shipping GenAI "
                         "features."),
    ("llm", "LLM", "How large language models work, are trained, evaluated and served."),
    ("agentic-ai", "Agentic AI", "AI agents: tool use, planning, memory, multi-agent systems, harnesses and "
                                 "protocols like MCP."),
    ("voice-ai", "Voice AI", "Speech recognition (ASR), language understanding (NLU) and launching voice "
                             "assistants in new languages."),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70] or "domain"


def _section(d: Domain, title: str) -> DomainSection:
    s = DomainSection(idx=len(d.sections), title=title)
    d.sections.append(s)
    return s


def _topic(s: DomainSection, title: str, *, blurb="", overview="", key_points=(), why="", details="",
           sources=(), ready=False) -> Topic:
    t = Topic(idx=len(s.topics), title=title[:200], blurb=blurb, overview=overview, key_points=list(key_points),
              why=why, details_md=details, status="ready" if ready else "draft")
    t.sources = [TopicSource(idx=i, **src) for i, src in enumerate(_dedupe(sources))]
    s.topics.append(t)
    return t


def _dedupe(sources) -> list[dict]:
    seen, out = set(), []
    for s in sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            out.append(s)
    return out


# ---------------------------------------------------------------- from learning paths

def _from_path(db: Session, d: Domain, path: LearningPath, prefix: str = "") -> None:
    for m in path.modules:
        sec = _section(d, f"{prefix}{m.title}")
        for l in m.lessons:
            srcs = []
            for lr in db.scalars(select(LessonResource).where(LessonResource.lesson_id == l.id)
                                 .order_by(LessonResource.rank)):
                r = lr.resource
                row = source_row(r.title, r.url, r.summary[:300] if r.kind == "paper" else (lr.why or r.summary)[:300],
                                 kind=r.kind if r.kind in ("video", "paper", "course") else None, author=r.author[:300],
                                 year=r.year, duration_min=r.duration_min, resource_id=r.id,
                                 ai_summary=(r.meta or {}).get("ai_summary"))
                srcs.append(row)
            t = _topic(sec, l.title, blurb="; ".join(l.objectives[:2]), key_points=l.objectives[:5],
                       details=l.content_md or "", sources=srcs)
            for s in t.sources:
                if (s.meta or {}).get("ai_summary"):
                    s.summary_status = "ready"


# ---------------------------------------------------------------- Claude Academy

def _course_source(c: dict) -> dict:
    hours = f"{c['hours']} hr" if c.get("hours") else ""
    return source_row(c["title"], c["url"], c["summary"], kind="course", access="login", site="Claude Academy",
                      author="Anthropic", duration=hours, badge=c.get("badge"))


def _agent_track(d: Domain) -> None:
    sec = _section(d, "Claude agent builder track")
    for c in ca.AGENT_TRACK:
        points = ([t for t, _ in c["outline"]] if len(c["outline"]) > 1
                  else (c["outline"][0][1] if c["outline"] else []))[:6]
        _topic(sec, f"{c['order']}. {c['title']}", blurb=c["summary"], overview=c["summary"], key_points=points,
               why=c.get("why", ""), sources=[_course_source(c)], ready=True)


def _academy_groups(d: Domain) -> None:
    sec = _section(d, "Claude Academy courses")
    for g in ca.GROUPS:
        if g["id"] == ca.AGENTS:
            continue
        courses = [c for c in ca.COURSES if c["group"] == g["id"]]
        _topic(sec, g["title"], blurb=g["summary"], overview=g["summary"],
               key_points=[f"{c['title']}: {c['summary'].split('. ')[0].rstrip('.')}" for c in courses][:6],
               why="Free official courses from Anthropic; sign in with an email to take them and earn a badge.",
               sources=[_course_source(c) for c in courses], ready=True)


# ---------------------------------------------------------------- voice

def _voice(d: Domain) -> None:
    for lang in LANGS.values():
        name = lang.NAME
        by_url: dict[str, str] = {}
        for c in lang.COURSES:
            by_url[c["url"]] = c["title"]
        for p in lang.PAPERS:
            by_url[p["url"]] = p["title"]
        for m in lang.MODELS:
            by_url[m["url"]] = m["name"]

        sec = _section(d, f"{name}: ASR and NLU")
        side = {s["id"]: s["title"] for s in lang.SIDES}
        for m in lang.MODULES:
            urls = [m["url"], *m["refs"]]
            _topic(sec, m["title"], blurb=m["summary"],
                   key_points=[f"{t}: {', '.join(ls[:3])}" for t, ls in m["outline"]][:6],
                   details="\n".join(f"**{t}**\n" + "\n".join(f"- {x}" for x in ls) + "\n" for t, ls in m["outline"]),
                   sources=[source_row(by_url.get(u) or u.split("//")[-1].split("/")[0], u) for u in urls])
            _ = side

        sec = _section(d, f"{name}: models and datasets")
        for k in lang.MODEL_KINDS:
            items = [m for m in lang.MODELS if m["kind"] == k["id"]]
            if items:
                _topic(sec, k["title"], blurb=f"Open models to start from ({len(items)}).", sources=[
                    source_row(f"{m['name']} ({m['org']})", m["url"], m["notes"], kind="model" if "huggingface" in
                               m["url"] else None, result=m["result"], licence=m["licence"], size=m["size"])
                    for m in sorted(items, key=lambda m: not m["top_pick"])])
        for k in lang.DATASET_KINDS:
            items = [x for x in lang.DATASETS if x["kind"] == k["id"]]
            if items:
                _topic(sec, k["title"], blurb=f"Datasets ({len(items)}).", sources=[
                    source_row(x["name"], x["url"], " ".join(filter(None, [x["what"], x["use"]])), kind="dataset",
                               licence=x["licence"], size=x["size"]) for x in items])

        sec = _section(d, f"{name}: research papers")
        for k in lang.PAPER_TOPICS:
            items = [p for p in lang.PAPERS if p["topic"] == k["id"]]
            if items:
                _topic(sec, k["title"], blurb=f"Key papers ({len(items)}).", sources=[
                    source_row(p["title"], p["url"], p["why"], kind="paper", access="free", site="arXiv",
                               year=p["year"]) for p in sorted(items, key=lambda p: not p["top_pick"])])

        sec = _section(d, f"{name}: courses")
        for ph in lang.PHASES:
            items = [c for c in lang.COURSES if c["phase"] == ph["id"]]
            if items:
                _topic(sec, re.sub(r"^\d+\.\s*", "", ph["title"]), blurb=ph["summary"], sources=[
                    source_row(c["title"], c["url"], c["covers"], author=c["provider"],
                               access="paid" if "paid" in c["cost"].lower() else None, cost=c["cost"],
                               level=c["level"]) for c in sorted(items, key=lambda c: not c["top_pick"])])

        sec = _section(d, f"{name}: launch playbook")
        for p in lang.PLAYBOOK:
            details = (f"**Outputs:** {', '.join(p['outputs'])}\n\n**Owners:** {p['owners']}\n\n**Pitfalls**\n"
                       + "\n".join(f"- {x}" for x in p["pitfalls"]))
            _topic(sec, p["title"], blurb=p["goal"], overview=p["goal"], key_points=p["steps"][:6],
                   why=p["pitfalls"][0] if p["pitfalls"] else "", details=details, ready=True)


# ---------------------------------------------------------------- entry point

def seed_domains(db: Session) -> bool:
    """Create the starting domains once. Returns True if it created them."""
    admin = db.scalars(select(User).where(User.role == "admin").order_by(User.id)).first()
    if admin is None or (admin.settings or {}).get(MARKER) or db.scalars(select(Domain).limit(1)).first():
        return False
    paths = {p.slug: p for p in db.scalars(select(LearningPath).where(LearningPath.user_id == admin.id,
                                                                      LearningPath.kind == "learning"))}
    for pos, (slug, name, desc) in enumerate(DOMAINS):
        d = Domain(slug=slug, name=name, description=desc, position=pos)
        if slug == "gen-ai":
            for p in paths.values():
                if not p.is_seed and p.slug is None and p.status == "ready":
                    _from_path(db, d, p)
        elif slug == "llm":
            if p := paths.get("llm-fundamentals"):
                _from_path(db, d, p)
            _academy_groups(d)
        elif slug == "agentic-ai":
            for s in ("agentic-ai", "agentic-harness"):
                if p := paths.get(s):
                    _from_path(db, d, p, "Harness: " if s == "agentic-harness" else "")
            _agent_track(d)
        else:
            _voice(d)
        db.add(d)
    admin.settings = {**(admin.settings or {}), MARKER: True}
    db.flush()
    return True
