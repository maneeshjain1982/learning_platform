"""Domains: the shared knowledge base. Domain > section > topic (executive summary) > sources (links).

Everyone can read, search and bookmark. Only the admin adds, edits, deletes or regenerates content. Writing a
missing summary is allowed for anyone: a 'draft' topic gets its executive summary the first time it's opened.
"""

from __future__ import annotations

import asyncio
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..agents import domains as agent
from ..agents.papers import arxiv_id, summarize as summarize_paper
from ..db import get_db, session_scope
from ..domains_seed import slugify
from ..llm import get_llm
from ..models import Domain, DomainSection, Topic, TopicSource, User, utcnow
from .common import iso, require_admin, spawn, uid

log = logging.getLogger("study.domains")
router = APIRouter(prefix="/api", tags=["domains"])
_llm_slots = asyncio.Semaphore(3)  # topic writers running at once
BOOKMARKS = "topic_bookmarks"


# ---------------------------------------------------------------- serializers

def domain_brief(db: Session, d: Domain) -> dict:
    topics = db.scalar(select(func.count(Topic.id)).join(DomainSection).where(DomainSection.domain_id == d.id)) or 0
    return {"id": d.id, "slug": d.slug, "name": d.name, "description": d.description, "status": d.status,
            "error": d.error, "sections": len(d.sections), "topics": topics, "trusted_blogs": d.trusted_blogs or []}


def source_out(s: TopicSource) -> dict:
    meta = s.meta or {}
    return {"id": s.id, "title": s.title, "url": s.url, "kind": s.kind, "site": s.site, "access": s.access,
            "summary": s.summary, "author": s.author, "year": meta.get("year"),
            "duration": meta.get("duration") or (f"{meta['duration_min']} min" if meta.get("duration_min") else ""),
            "facts": {k: meta[k] for k in ("result", "licence", "size", "cost", "level")
                      if meta.get(k) and not (k == "level" and meta.get("blog"))},
            "ai_summary": meta.get("ai_summary"), "summary_status": s.summary_status,
            "blog": bool(meta.get("blog")), "read_minutes": meta.get("read_minutes"),
            "published": meta.get("published", ""), "post_level": meta.get("level") if meta.get("blog") else None}


def topic_brief(t: Topic) -> dict:
    return {"id": t.id, "title": t.title, "blurb": t.blurb, "status": t.status, "sources": len(t.sources)}


def topic_out(db: Session, t: Topic) -> dict:
    sec, d = t.section, t.section.domain
    return {**topic_brief(t), "overview": t.overview, "key_points": t.key_points or [], "why": t.why,
            "details_md": t.details_md, "error": t.error, "updated_at": iso(t.updated_at),
            "section": {"id": sec.id, "title": sec.title}, "domain": {"id": d.id, "slug": d.slug, "name": d.name},
            "source_list": [source_out(s) for s in t.sources], "bookmarked": t.id in _bookmarks(db),
            "blog_status": t.blog_status or "none", "blog_error": t.blog_error}


def _bookmarks(db: Session) -> list[int]:
    return list((db.get(User, uid()).settings or {}).get(BOOKMARKS) or [])


def _domain(db: Session, key: str) -> Domain:
    d = db.scalars(select(Domain).where(Domain.slug == key)).first()
    if d is None and key.isdigit():
        d = db.get(Domain, int(key))
    if d is None:
        raise HTTPException(404, "Domain not found")
    return d


def _get(db: Session, model, id_: int):
    obj = db.get(model, id_)
    if obj is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


# ---------------------------------------------------------------- background writers

async def write_topic(topic_id: int, *, find_sources: bool) -> None:
    """Write a topic's executive summary (and find sources when asked or when it has none)."""
    with session_scope() as db:
        t = db.get(Topic, topic_id)
        if t is None:
            return
        t.status, t.error = "writing", None
        ctx = dict(domain=t.section.domain.name, section=t.section.title, topic=t.title, blurb=t.blurb)
        known = [{"title": s.title, "url": s.url} for s in t.sources]
    find = 6 if (find_sources or len(known) < 3) else 0  # thin topics get more links
    try:
        async with _llm_slots:
            out = await agent.write_topic(get_llm(), **ctx, known_sources=known, find_sources=find)
    except Exception as exc:
        log.warning("Topic %s failed: %s", topic_id, exc)
        with session_scope() as db:
            if t := db.get(Topic, topic_id):
                t.status, t.error = "failed", str(exc)[:500]
        return
    with session_scope() as db:
        t = db.get(Topic, topic_id)
        if t is None:
            return
        t.overview, t.key_points, t.why = out["overview"], out["key_points"][:6], out["why"]
        t.status, t.error, t.updated_at = "ready", None, utcnow()
        have = {s.url for s in t.sources}
        for row in out["sources"]:
            if row["url"] not in have:
                t.sources.append(TopicSource(idx=len(t.sources), **row))


BLOGS_WANTED = 2  # Blog Scout runs on first open when a topic has fewer explainer posts than this


def blog_count(t: Topic) -> int:
    return sum(1 for s in t.sources if s.kind == "article")


async def find_blogs(topic_id: int) -> None:
    """Blog Scout: add the best explainer posts to a topic."""
    with session_scope() as db:
        t = db.get(Topic, topic_id)
        if t is None:
            return
        d = t.section.domain
        ctx = dict(domain=d.name, section=t.section.title, topic=t.title, blurb=t.blurb)
        known = [{"title": s.title, "url": s.url} for s in t.sources]
        trusted = list(d.trusted_blogs or [])
    try:
        async with _llm_slots:
            rows = await agent.find_blogs(get_llm(), **ctx, known=known, trusted=trusted)
    except Exception as exc:
        log.warning("Blog Scout %s failed: %s", topic_id, exc)
        with session_scope() as db:
            if t := db.get(Topic, topic_id):
                t.blog_status, t.blog_error = "failed", str(exc)[:500]
        return
    with session_scope() as db:
        t = db.get(Topic, topic_id)
        if t is None:
            return
        have = {s.url for s in t.sources}
        for row in rows:
            if row["url"] not in have:
                t.sources.append(TopicSource(idx=len(t.sources), **row))
                have.add(row["url"])
        t.blog_status, t.blog_error = "done", None


def start_blogs(db: Session, t: Topic) -> None:
    if t.blog_status == "finding":
        return
    t.blog_status, t.blog_error = "finding", None
    db.commit()
    spawn(find_blogs(t.id))


def start_topic(db: Session, t: Topic, *, find_sources: bool = False) -> None:
    if t.status == "writing":
        return
    t.status, t.error = "writing", None
    db.commit()
    spawn(write_topic(t.id, find_sources=find_sources))


async def build_domain(domain_id: int, max_topics: int) -> None:
    """New domain: plan the outline, then write every topic with its sources."""
    with session_scope() as db:
        d = db.get(Domain, domain_id)
        name, desc = d.name, d.description
    try:
        plan = await agent.plan_domain(get_llm(), name, desc, max_topics=max_topics)
    except Exception as exc:
        with session_scope() as db:
            if d := db.get(Domain, domain_id):
                d.status, d.error = ("ready" if d.sections else "failed"), f"Outline failed: {exc}"[:500]
        return
    with session_scope() as db:
        d = db.get(Domain, domain_id)
        if d is None:
            return
        if not d.description:
            d.description = plan.description
        ids = []
        for s in plan.sections:
            sec = DomainSection(idx=len(d.sections), title=s.title[:200])
            sec.topics = [Topic(idx=i, title=t.title[:200], blurb=t.blurb, status="writing")
                          for i, t in enumerate(s.topics)]
            d.sections.append(sec)
        db.flush()
        ids = [t.id for s in d.sections for t in s.topics if t.status == "writing"]
    await asyncio.gather(*(write_topic(i, find_sources=True) for i in ids))
    with session_scope() as db:
        if d := db.get(Domain, domain_id):
            d.status, d.error = "ready", None


async def summarize_one(source_id: int) -> None:
    with session_scope() as db:
        s = db.get(TopicSource, source_id)
        if s is None:
            return
        ctx = f"{s.topic.section.domain.name} > {s.topic.title}"
        title, url, kind = s.title, s.url, s.kind
    try:
        async with _llm_slots:
            if aid := arxiv_id(url):
                out = await summarize_paper(get_llm(), title=title, url=url, aid=aid, context=ctx)
                out = {"type": "paper", **out}
            else:
                out = {"type": "source", **await agent.summarize_source(get_llm(), title=title, url=url, kind=kind,
                                                                         context=ctx)}
    except Exception as exc:
        log.warning("Source summary %s failed: %s", source_id, exc)
        with session_scope() as db:
            if s := db.get(TopicSource, source_id):
                s.summary_status = "failed"
                s.meta = {**(s.meta or {}), "summary_error": str(exc)[:300]}
        return
    with session_scope() as db:
        if s := db.get(TopicSource, source_id):
            s.meta = {**(s.meta or {}), "ai_summary": out, "summary_error": None}
            s.summary_status = "ready"


# ---------------------------------------------------------------- domains

@router.get("/domains")
def list_domains(db: Session = Depends(get_db)):
    return [domain_brief(db, d) for d in db.scalars(select(Domain).order_by(Domain.position, Domain.id))]


@router.get("/domains/{key}")
def get_domain(key: str, db: Session = Depends(get_db)):
    d = _domain(db, key)
    return {**domain_brief(db, d),
            "section_list": [{"id": s.id, "title": s.title, "topics": [topic_brief(t) for t in s.topics]}
                             for s in d.sections]}


class DomainIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field("", max_length=1000)
    build: bool = True
    max_topics: int = Field(18, ge=4, le=40)


@router.post("/domains")
async def create_domain(body: DomainIn, db: Session = Depends(get_db)):
    require_admin(db)
    base = slugify(body.name)
    slug, n = base, 2
    while db.scalars(select(Domain).where(Domain.slug == slug)).first():
        slug, n = f"{base}-{n}", n + 1
    pos = (db.scalar(select(func.max(Domain.position))) or 0) + 1
    d = Domain(slug=slug, name=body.name.strip(), description=body.description.strip(), position=pos,
               status="building" if body.build else "ready")
    db.add(d)
    db.commit()
    if body.build:
        spawn(build_domain(d.id, body.max_topics))
    return domain_brief(db, d)


class TrustedBlog(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=8, max_length=500, pattern=r"^https?://")


class DomainPatch(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=1000)
    trusted_blogs: list[TrustedBlog] | None = Field(None, max_length=30)


@router.patch("/domains/{domain_id}")
def update_domain(domain_id: int, body: DomainPatch, db: Session = Depends(get_db)):
    require_admin(db)
    d = _get(db, Domain, domain_id)
    if body.name is not None:
        d.name = body.name.strip()
    if body.description is not None:
        d.description = body.description.strip()
    if body.trusted_blogs is not None:
        d.trusted_blogs = [{"name": b.name.strip(), "url": b.url.strip()} for b in body.trusted_blogs]
    db.commit()
    return domain_brief(db, d)


@router.delete("/domains/{domain_id}")
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    db.delete(_get(db, Domain, domain_id))
    db.commit()
    return {"ok": True}


@router.put("/domains-order")
def reorder_domains(ids: list[int], db: Session = Depends(get_db)):
    require_admin(db)
    for pos, i in enumerate(ids):
        if d := db.get(Domain, i):
            d.position = pos
    db.commit()
    return list_domains(db)


class BuildIn(BaseModel):
    max_topics: int = Field(18, ge=4, le=40)


@router.post("/domains/{domain_id}/build")
async def build_outline(domain_id: int, body: BuildIn | None = None, db: Session = Depends(get_db)):
    """Add an AI-written outline (sections, topics, summaries, sources) to a domain."""
    require_admin(db)
    d = _get(db, Domain, domain_id)
    if d.status != "building":
        d.status, d.error = "building", None
        db.commit()
        spawn(build_domain(d.id, (body or BuildIn()).max_topics))
    return domain_brief(db, d)


@router.post("/domains/{domain_id}/fill")
async def fill_drafts(domain_id: int, db: Session = Depends(get_db)):
    """Write every draft topic in the domain now (three at a time) instead of on first open."""
    require_admin(db)
    d = _get(db, Domain, domain_id)
    ids = [t.id for s in d.sections for t in s.topics if t.status in ("draft", "failed")]
    for s in d.sections:
        for t in s.topics:
            if t.id in ids:
                t.status = "writing"
    db.commit()
    for i in ids:
        spawn(write_topic(i, find_sources=False))
    return {"started": len(ids)}


# ---------------------------------------------------------------- sections

class TitleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.post("/domains/{domain_id}/sections")
def add_section(domain_id: int, body: TitleIn, db: Session = Depends(get_db)):
    require_admin(db)
    d = _get(db, Domain, domain_id)
    s = DomainSection(idx=len(d.sections), title=body.title.strip())
    d.sections.append(s)
    db.commit()
    return {"id": s.id, "title": s.title, "topics": []}


@router.patch("/sections/{section_id}")
def rename_section(section_id: int, body: TitleIn, db: Session = Depends(get_db)):
    require_admin(db)
    s = _get(db, DomainSection, section_id)
    s.title = body.title.strip()
    db.commit()
    return {"id": s.id, "title": s.title}


@router.delete("/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    db.delete(_get(db, DomainSection, section_id))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- topics

class TopicIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    blurb: str = Field("", max_length=500)
    auto: bool = Field(True, description="Write the summary and find sources with the LLM")


@router.post("/sections/{section_id}/topics")
async def add_topic(section_id: int, body: TopicIn, db: Session = Depends(get_db)):
    require_admin(db)
    s = _get(db, DomainSection, section_id)
    t = Topic(idx=len(s.topics), title=body.title.strip(), blurb=body.blurb.strip(),
              status="draft" if body.auto else "ready")
    s.topics.append(t)
    db.commit()
    if body.auto:
        start_topic(db, t, find_sources=True)
    return topic_out(db, t)


@router.get("/topics/search")
def search_topics(q: str, limit: int = 20, db: Session = Depends(get_db)):
    return _search(db, q, limit)


def _terms(text: str) -> list[str]:
    stop = {"and", "the", "for", "with", "of", "to", "in", "on", "a", "an", "or", "using", "how", "what"}
    return [w for w in re.findall(r"[a-z0-9+#.]+", text.lower()) if len(w) > 1 and w not in stop]


def _search(db: Session, q: str, limit: int) -> list[dict]:
    words = _terms(q)
    if not words:
        return []
    scored = []
    for t in db.scalars(select(Topic)):
        title = t.title.lower()
        body = " ".join([t.blurb, t.overview, " ".join(t.key_points or [])]).lower()
        score = sum(3 * (w in title) + (w in body) for w in words)
        if q.lower().strip() in title:
            score += 5
        if score >= len(words):
            scored.append((score, t))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    return [{**topic_brief(t), "overview": t.overview or t.blurb, "section": t.section.title,
             "domain": {"slug": t.section.domain.slug, "name": t.section.domain.name}} for _, t in scored[:limit]]


class MatchIn(BaseModel):
    terms: list[str] = Field(max_length=60)


@router.post("/topics/match")
def match_topics(body: MatchIn, db: Session = Depends(get_db)):
    """For each skill name, the domain topics that cover it best (up to 3)."""
    return {term: _search(db, term, 3) for term in body.terms}


@router.get("/topics/recent")
def recent_topics(limit: int = 8, db: Session = Depends(get_db)):
    rows = db.scalars(select(Topic).where(Topic.status == "ready").order_by(Topic.updated_at.desc(), Topic.id.desc())
                      .limit(limit))
    return [{**topic_brief(t), "domain": {"slug": t.section.domain.slug, "name": t.section.domain.name},
             "updated_at": iso(t.updated_at)} for t in rows]


@router.get("/topics/bookmarks")
def bookmarked_topics(db: Session = Depends(get_db)):
    out = []
    for i in _bookmarks(db):
        if t := db.get(Topic, i):
            out.append({**topic_brief(t), "overview": t.overview or t.blurb,
                        "domain": {"slug": t.section.domain.slug, "name": t.section.domain.name}})
    return out


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: int, db: Session = Depends(get_db)):
    t = _get(db, Topic, topic_id)
    if t.status == "draft":  # first visit: write the executive summary from the outline and its sources
        start_topic(db, t)
    if (t.blog_status or "none") == "none" and blog_count(t) < BLOGS_WANTED:  # and find explainer posts
        start_blogs(db, t)
    return topic_out(db, t)


@router.post("/topics/{topic_id}/blogs")
async def topic_blogs(topic_id: int, db: Session = Depends(get_db)):
    """Run Blog Scout on a topic. Admin any time; anyone may retry a failed run."""
    t = _get(db, Topic, topic_id)
    if t.blog_status != "failed":
        require_admin(db)
    start_blogs(db, t)
    return topic_out(db, t)


@router.post("/domains/{domain_id}/blogs")
async def domain_blogs(domain_id: int, db: Session = Depends(get_db)):
    """Run Blog Scout on every topic in a domain that hasn't had it yet (three at a time)."""
    require_admin(db)
    d = _get(db, Domain, domain_id)
    todo = [t for s in d.sections for t in s.topics if (t.blog_status or "none") in ("none", "failed")]
    for t in todo:
        t.blog_status, t.blog_error = "finding", None
    db.commit()
    for t in todo:
        spawn(find_blogs(t.id))
    return {"started": len(todo)}


class TopicPatch(BaseModel):
    title: str | None = Field(None, min_length=2, max_length=200)
    blurb: str | None = Field(None, max_length=500)
    overview: str | None = Field(None, max_length=4000)
    key_points: list[str] | None = Field(None, max_length=12)
    why: str | None = Field(None, max_length=1000)
    details_md: str | None = Field(None, max_length=30_000)


@router.patch("/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicPatch, db: Session = Depends(get_db)):
    require_admin(db)
    t = _get(db, Topic, topic_id)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, [p.strip() for p in v if p.strip()] if k == "key_points" else v.strip())
    if t.status in ("draft", "failed") and t.overview:
        t.status = "ready"
    t.updated_at = utcnow()
    db.commit()
    return topic_out(db, t)


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    db.delete(_get(db, Topic, topic_id))
    db.commit()
    return {"ok": True}


class RewriteIn(BaseModel):
    find_sources: bool = False


@router.post("/topics/{topic_id}/rewrite")
async def rewrite_topic(topic_id: int, body: RewriteIn | None = None, db: Session = Depends(get_db)):
    t = _get(db, Topic, topic_id)
    if t.status != "failed":
        require_admin(db)  # anyone may retry a failed summary
    start_topic(db, t, find_sources=(body or RewriteIn()).find_sources)
    return topic_out(db, t)


class BookmarkIn(BaseModel):
    on: bool


@router.put("/topics/{topic_id}/bookmark")
def bookmark(topic_id: int, body: BookmarkIn, db: Session = Depends(get_db)):
    _get(db, Topic, topic_id)
    user = db.get(User, uid())
    ids = [i for i in _bookmarks(db) if i != topic_id]
    if body.on:
        ids.insert(0, topic_id)
    user.settings = {**(user.settings or {}), BOOKMARKS: ids}
    db.commit()
    return {"bookmarked": body.on}


# ---------------------------------------------------------------- sources

class SourceIn(BaseModel):
    url: str = Field(min_length=8, max_length=1000, pattern=r"^https?://")
    title: str = Field("", max_length=500)
    summary: str = Field("", max_length=1000)
    access: str | None = Field(None, pattern="^(free|login|paid|limited)$")


@router.post("/topics/{topic_id}/sources")
def add_source(topic_id: int, body: SourceIn, db: Session = Depends(get_db)):
    require_admin(db)
    t = _get(db, Topic, topic_id)
    row = agent.source_row(body.title.strip() or body.url.split("//")[-1][:120], body.url, body.summary,
                           access=body.access)
    s = TopicSource(idx=len(t.sources), **row)
    t.sources.append(s)
    t.updated_at = utcnow()
    db.commit()
    return source_out(s)


class SourcePatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    url: str | None = Field(None, max_length=1000, pattern=r"^https?://")
    summary: str | None = Field(None, max_length=1000)
    access: str | None = Field(None, pattern="^(free|login|paid|limited)$")
    kind: str | None = Field(None, pattern="^(video|course|paper|article|docs|repo|model|dataset|book)$")


@router.patch("/sources/{source_id}")
def update_source(source_id: int, body: SourcePatch, db: Session = Depends(get_db)):
    require_admin(db)
    s = _get(db, TopicSource, source_id)
    data = body.model_dump(exclude_none=True)
    if "url" in data and data["url"] != s.url:
        c = agent.classify(data["url"])
        s.site = c["site"]
        data.setdefault("kind", c["kind"])
        data.setdefault("access", c["access"])
    for k, v in data.items():
        setattr(s, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return source_out(s)


@router.delete("/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    db.delete(_get(db, TopicSource, source_id))
    db.commit()
    return {"ok": True}


@router.post("/sources/{source_id}/summary")
async def summarize(source_id: int, db: Session = Depends(get_db)):
    """Write the source's AI summary. Anyone can write a missing one; replacing it is for the admin."""
    s = _get(db, TopicSource, source_id)
    if (s.meta or {}).get("ai_summary"):
        require_admin(db)
    if s.summary_status != "writing":
        s.summary_status = "writing"
        db.commit()
        spawn(summarize_one(s.id))
    return source_out(s)


@router.delete("/sources/{source_id}/summary")
def delete_summary(source_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    s = _get(db, TopicSource, source_id)
    s.meta = {**(s.meta or {}), "ai_summary": None}
    s.summary_status = "none"
    db.commit()
    return source_out(s)


def recover(db: Session) -> None:
    """After a restart: work that was running can't continue."""
    for t in db.scalars(select(Topic).where(Topic.status == "writing")):
        t.status = "ready" if t.overview else "draft"
    for t in db.scalars(select(Topic).where(Topic.blog_status == "finding")):
        t.blog_status = "none"
    # Link labels fixed later: Hugging Face blog posts were 'model', Kaggle notebooks were 'course'.
    for s in db.scalars(select(TopicSource).where(TopicSource.site.in_(["Hugging Face", "Kaggle"]))):
        kind = agent.classify(s.url)["kind"]
        if kind == "article" and s.kind != "article":
            s.kind = kind
    for s in db.scalars(select(TopicSource).where(TopicSource.summary_status == "writing")):
        s.summary_status = "none"
    for d in db.scalars(select(Domain).where(Domain.status == "building")):
        d.status = "ready" if d.sections else "failed"
        d.error = None if d.sections else "Interrupted by a server restart. Try again."
