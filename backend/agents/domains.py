"""Domain agents: plan a new domain, write a topic's executive summary and find its sources, summarize a source.

Every source link is checked: dead links are dropped; links whose site blocks automated checks are kept.
"""

from __future__ import annotations

import asyncio
import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from ..providers import check_url

TIMEOUT = max(config.LLM_TIMEOUT, 600)
Kind = Literal["video", "course", "paper", "article", "docs", "repo", "model", "dataset", "book"]
Access = Literal["free", "login", "paid", "limited"]

# ---------------------------------------------------------------- what a link is

# (host suffix, site name, kind, access). First match wins.
SITES: list[tuple[str, str, str, str]] = [
    ("lilianweng.github.io", "Lil'Log", "article", "free"), ("jalammar.github.io", "Jay Alammar", "article", "free"),
    ("youtube.com", "YouTube", "video", "free"), ("youtu.be", "YouTube", "video", "free"),
    ("coursera.org", "Coursera", "course", "login"), ("udemy.com", "Udemy", "course", "paid"),
    ("edx.org", "edX", "course", "login"), ("deeplearning.ai", "DeepLearning.AI", "course", "login"),
    ("academy.claude.com", "Claude Academy", "course", "login"), ("nptel.ac.in", "NPTEL", "course", "free"),
    ("linkedin.com", "LinkedIn", "course", "paid"), ("udacity.com", "Udacity", "course", "paid"),
    ("pluralsight.com", "Pluralsight", "course", "paid"), ("oreilly.com", "O'Reilly", "book", "paid"),
    ("kaggle.com", "Kaggle", "course", "free"), ("fast.ai", "fast.ai", "course", "free"),
    ("arxiv.org", "arXiv", "paper", "free"), ("aclanthology.org", "ACL Anthology", "paper", "free"),
    ("openreview.net", "OpenReview", "paper", "free"), ("semanticscholar.org", "Semantic Scholar", "paper", "free"),
    ("isca-archive.org", "ISCA", "paper", "free"), ("ieee.org", "IEEE", "paper", "paid"),
    ("acm.org", "ACM", "paper", "paid"), ("springer.com", "Springer", "paper", "paid"),
    ("github.com", "GitHub", "repo", "free"), ("medium.com", "Medium", "article", "limited"),
    ("towardsdatascience.com", "Towards Data Science", "article", "free"), ("substack.com", "Substack", "article", "free"),
    ("dev.to", "DEV", "article", "free"), ("distill.pub", "Distill", "article", "free"),
    ("magazine.sebastianraschka.com", "Ahead of AI", "article", "free"), ("huyenchip.com", "Chip Huyen", "article", "free"),
    ("thegradient.pub", "The Gradient", "article", "free"), ("analyticsvidhya.com", "Analytics Vidhya", "article", "free"),
    ("machinelearningmastery.com", "ML Mastery", "article", "free"), ("pinecone.io", "Pinecone", "article", "free"),
    ("docs.anthropic.com", "Anthropic docs", "docs", "free"), ("anthropic.com", "Anthropic", "article", "free"),
    ("platform.openai.com", "OpenAI docs", "docs", "free"), ("openai.com", "OpenAI", "article", "free"),
    ("ai.google.dev", "Google AI docs", "docs", "free"), ("cloud.google.com", "Google Cloud", "docs", "free"),
    ("learn.microsoft.com", "Microsoft Learn", "docs", "free"), ("aws.amazon.com", "AWS", "docs", "free"),
    ("langchain.com", "LangChain", "docs", "free"), ("python.langchain.com", "LangChain docs", "docs", "free"),
    ("modelcontextprotocol.io", "MCP docs", "docs", "free"), ("nvidia.com", "NVIDIA", "docs", "free"),
]
HF = ("huggingface.co", "Hugging Face")


def classify(url: str, title: str = "") -> dict:
    """Site name, kind and access for a link, from its address."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    path = urlparse(url).path.lower()
    if host == HF[0] or host.endswith("." + HF[0]):
        kind = "dataset" if path.startswith("/datasets") else "course" if path.startswith("/learn") else \
            "docs" if path.startswith("/docs") else "paper" if path.startswith("/papers") else \
            "article" if path.startswith(("/blog", "/posts", "/spaces")) else "model"
        return {"site": HF[1], "kind": kind, "access": "free"}
    for suffix, site, kind, access in SITES:
        if host == suffix or host.endswith("." + suffix):
            if site == "Medium" or "medium" in host:
                return {"site": "Medium", "kind": "article", "access": "limited"}
            if site == "LinkedIn" and "/learning" not in path:
                kind, access = "article", "login"
            if site == "Kaggle" and not path.startswith("/learn"):
                kind = "article"  # notebooks, write-ups and discussions explain a topic
            return {"site": site, "kind": kind, "access": access}
    if host.endswith(".edu") or ".ac." in host or host.endswith(".edu.in") or "university" in host:
        return {"site": "University", "kind": "course", "access": "free"}
    if path.endswith(".pdf"):
        return {"site": _site_name(host), "kind": "paper", "access": "free"}
    if host.startswith("docs.") or "/docs" in path:
        return {"site": _site_name(host), "kind": "docs", "access": "free"}
    if re.search(r"\bblog\b", host + path):
        return {"site": _site_name(host), "kind": "article", "access": "free"}
    return {"site": _site_name(host), "kind": "article", "access": "free"}


def _site_name(host: str) -> str:
    parts = [p for p in host.split(".") if p not in ("www", "docs", "blog", "com", "org", "io", "ai", "net", "dev")]
    return (parts[0] if parts else host).capitalize()[:80]


def source_row(title: str, url: str, summary: str = "", *, kind: str | None = None, access: str | None = None,
               site: str | None = None, author: str = "", **meta) -> dict:
    c = classify(url, title)
    return {"title": title.strip()[:500], "url": url.strip(), "summary": summary.strip(), "author": author[:300],
            "kind": kind or c["kind"], "access": access or c["access"], "site": site or c["site"],
            "meta": {k: v for k, v in meta.items() if v not in (None, "", [])}}


async def check_sources(items: list[dict]) -> list[dict]:
    """Drop duplicates and dead links."""
    seen, uniq = set(), []
    for it in items:
        url = (it.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            uniq.append(it)
    states = await asyncio.gather(*(check_url(i["url"]) for i in uniq))
    return [i for i, st in zip(uniq, states) if st != "dead"]


# ---------------------------------------------------------------- topic: summary + sources

class FoundSource(BaseModel):
    title: str
    url: str = Field(description="Exact URL you opened")
    kind: Kind
    access: Access = Field(description="free; login (free account needed, e.g. Coursera audit); paid; limited "
                                       "(partly paywalled, e.g. Medium)")
    summary: str = Field(description="One sentence: what you get from this source")
    author: str = Field("", description="Author, channel, university or company")


class TopicWrite(BaseModel):
    overview: str = Field(description="Executive summary: 2-3 short plain sentences on what it is, at most 60 words")
    key_points: list[str] = Field(description="3-5 bullets, each under 25 words: the ideas a senior engineer must know")
    why: str = Field(description="One sentence, under 30 words: why it matters in practice")
    sources: list[FoundSource] = Field(default_factory=list,
                                       description="Best sources to go deeper, most useful first")


class SummaryOnly(BaseModel):
    overview: str = Field(description="Executive summary: 2-3 short plain sentences on what it is, at most 60 words")
    key_points: list[str] = Field(description="3-5 bullets, each under 25 words: the ideas a senior engineer must know")
    why: str = Field(description="One sentence, under 30 words: why it matters in practice")


SYSTEM = (
    "You write an executive-level learning brief for senior engineers: short, concrete, no hype, no filler. Keep it "
    "scannable: the reader should get the gist in 30 seconds and use the links for depth. "
    "When asked for sources, use web search and include only pages you opened. Mix formats: a video "
    "(YouTube), a course (Coursera, edX, DeepLearning.AI, university), official docs, a key paper (arXiv), and a "
    "good blog post (company engineering blog or Medium). Never invent a URL."
)


def _context(domain: str, section: str, topic: str, blurb: str = "") -> str:
    return f"Domain: {domain}\nSection: {section}\nTopic: {topic}" + (f"\nScope: {blurb}" if blurb else "")


async def write_topic(llm: LLMClient, *, domain: str, section: str, topic: str, blurb: str = "",
                      known_sources: list[dict] | None = None, find_sources: int = 6) -> dict:
    """Executive summary, plus new sources when find_sources > 0. Returns {overview, key_points, why, sources}."""
    known = "\n".join(f"- {s['title']} ({s['url']})" for s in (known_sources or [])[:15])
    ctx = _context(domain, section, topic, blurb)
    if find_sources:
        prompt = (f"{ctx}\n\nWrite the executive summary for this topic, then find {find_sources} of the best "
                  "sources to learn it in depth." + (f"\nAlready listed (don't repeat):\n{known}" if known else ""))
        out = await llm.ask_json(prompt, TopicWrite, system=SYSTEM, model=config.LLM_MODEL, web=True,
                                 timeout=TIMEOUT)
        found = [source_row(s.title, s.url, s.summary, kind=s.kind, access=s.access, author=s.author)
                 for s in out.sources]
        return {**out.model_dump(exclude={"sources"}), "sources": await check_sources(found)}
    prompt = (f"{ctx}\n\nWrite the executive summary for this topic."
              + (f"\nThe sources the reader will use:\n{known}" if known else ""))
    out = await llm.ask_json(prompt, SummaryOnly, system=SYSTEM, model=config.LLM_MODEL, web=False,
                             timeout=TIMEOUT)
    return {**out.model_dump(), "sources": []}


# ---------------------------------------------------------------- new domain: the outline

class PlanTopic(BaseModel):
    title: str
    blurb: str = Field(description="One line on what the topic covers")


class PlanSection(BaseModel):
    title: str
    topics: list[PlanTopic] = Field(description="2-6 topics")


class DomainPlan(BaseModel):
    description: str = Field(description="One sentence describing the domain")
    sections: list[PlanSection] = Field(description="4-7 sections from foundations to advanced and practice")


async def plan_domain(llm: LLMClient, name: str, description: str = "", max_topics: int = 24) -> DomainPlan:
    prompt = (f"Design the outline of a knowledge base for the domain '{name}'."
              + (f"\nScope: {description}" if description else "")
              + f"\nAudience: senior engineers and architects. At most {max_topics} topics in total, current as of "
                "today, ordered from foundations to advanced topics and real-world practice.")
    out = await llm.ask_json(prompt, DomainPlan, system=SYSTEM, model=config.LLM_MODEL, web=False, timeout=TIMEOUT)
    left, sections = max_topics, []
    for s in out.sections:
        topics = s.topics[:left]
        left -= len(topics)
        if topics:
            sections.append(PlanSection(title=s.title, topics=topics))
    out.sections = sections
    return out


# ---------------------------------------------------------------- summarize one source

class SourceSummary(BaseModel):
    tldr: str = Field(description="One or two plain sentences: what this source teaches")
    key_points: list[str] = Field(description="3-6 key takeaways, with numbers exactly as the source gives them")
    best_for: str = Field(description="Who should use it and when, one sentence")
    time_needed: str = Field("", description="Length or time to complete, if stated, e.g. '18 min' or '4 weeks'")
    access_note: str = Field("", description="Login, paywall or cost notes, if any")
    read_source: bool = Field(description="True if you opened and read the source itself")


SOURCE_SYSTEM = (
    "You summarize a learning resource (video, course, article, docs or repo) for a busy engineer. Open the link "
    "with web search/fetch and work from what it actually says; if you can't open it, say so via read_source and "
    "keep to what the search results show. No hype."
)


async def summarize_source(llm: LLMClient, *, title: str, url: str, kind: str, context: str = "") -> dict:
    prompt = (f"Summarize this {kind}.\nTitle: {title}\nLink: {url}\n"
              + (f"The reader is studying: {context}\n" if context else ""))
    out = await llm.ask_json(prompt, SourceSummary, system=SOURCE_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    return out.model_dump()


# ---------------------------------------------------------------- Blog Scout: plain-language explainers

BLOG_SITES = ("Medium and Towards Data Science, the Hugging Face blog, Kaggle notebooks and write-ups, Substack, "
              "Lilian Weng (Lil'Log), Jay Alammar, Sebastian Raschka (Ahead of AI), Chip Huyen, Distill, "
              "The Gradient, Analytics Vidhya, and company engineering blogs (Google, Meta, OpenAI, Anthropic, "
              "NVIDIA, Pinecone, Databricks...)")


class BlogPost(BaseModel):
    title: str
    url: str = Field(description="Exact URL of the post you opened")
    author: str = Field("", description="Author or blog name")
    why: str = Field(description="One sentence: what makes this explanation good")
    level: Literal["beginner", "intermediate", "advanced"]
    read_minutes: int | None = Field(None, description="Reading time in minutes, if shown or easy to estimate")
    published: str = Field("", description="Publication date as YYYY-MM or YYYY, if shown")
    access: Access = Field(description="free; limited (partly paywalled, e.g. Medium member-only); login; paid")


class BlogFind(BaseModel):
    posts: list[BlogPost]


BLOG_SYSTEM = (
    "You are Blog Scout. You find blog posts that explain a technical topic clearly: plain language, good "
    "diagrams or worked examples, written by people who know the subject. Use web search and include only posts "
    "you opened. Prefer posts from the last 3 years unless an older one is the classic explanation. Prefer a "
    "free post over a paywalled one of similar quality. Skip SEO filler, listicles and vendor marketing. Never "
    "invent a URL."
)


async def find_blogs(llm: LLMClient, *, domain: str, section: str, topic: str, blurb: str = "",
                     known: list[dict] | None = None, trusted: list[dict] | None = None, count: int = 5) -> list[dict]:
    """Source rows for the best explainer posts on a topic, beginner-friendly first. Dead links dropped."""
    have = "\n".join(f"- {s['title']} ({s['url']})" for s in (known or [])[:20])
    fav = "\n".join(f"- {b['name']}: {b['url']}" for b in (trusted or []) if b.get("url"))
    prompt = (f"{_context(domain, section, topic, blurb)}\n\nFind {count} blog posts that explain this topic well. "
              "Include at least one for a beginner and one deeper post. "
              f"Good places to look: {BLOG_SITES}."
              + (f"\nCheck these trusted blogs first:\n{fav}" if fav else "")
              + (f"\nAlready listed (don't repeat):\n{have}" if have else ""))
    out = await llm.ask_json(prompt, BlogFind, system=BLOG_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    rows = [source_row(b.title, b.url, b.why, kind="article", access=b.access, author=b.author, blog=True,
                       level=b.level, read_minutes=b.read_minutes, published=b.published)
            for b in sorted(out.posts, key=lambda b: order[b.level])]
    return await check_sources(rows)
