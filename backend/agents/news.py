"""Tech News: live Hacker News headlines (public API, no key) and an LLM web-search digest by topic.

Every link in the digest is checked: dead links are dropped, links whose site blocks automated checks are kept
but marked unverified.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timezone

import httpx
from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from ..providers import HEADERS
from .career import _check

log = logging.getLogger("study.news")

# id -> (label, what to look for)
TOPICS: dict[str, tuple[str, str]] = {
    "ai": ("AI & LLMs", "new models, model releases, AI research results, AI products and policy"),
    "agents": ("Agents & tools", "agent frameworks, MCP, coding agents, agent products"),
    "speech": ("Speech & NLP", "speech recognition, TTS, voice assistants, multilingual and Indic NLP"),
    "dev": ("Developer tools", "programming languages, frameworks, IDEs, open-source releases"),
    "cloud": ("Cloud & infra", "cloud platforms, GPUs in the cloud, databases, DevOps"),
    "mobile": ("Mobile & devices", "smartphones, on-device AI, wearables, Android and iOS"),
    "security": ("Security", "major vulnerabilities, breaches, security tools"),
    "chips": ("Chips & hardware", "GPUs, AI accelerators, semiconductors"),
}
DEFAULT_TOPICS = ["ai", "agents", "speech", "dev"]


class NewsItem(BaseModel):
    topic: str = Field(description="One of the topic ids you were given")
    title: str = Field(description="Short headline in your own words")
    source: str = Field(description="Publisher or site name")
    date: str = Field(description="Publication date YYYY-MM-DD, or empty if the page shows none")
    summary: str = Field(description="1-2 sentences with the concrete facts")
    why_it_matters: str = Field(description="One short sentence on why it matters to an AI/speech engineer")
    url: str = Field(description="Full https URL of the article or announcement you read")


class NewsOut(BaseModel):
    headline: str = Field(description="One sentence: the biggest tech story of the period")
    items: list[NewsItem] = Field(description="3-5 items per topic, newest first")


SYSTEM = (
    "You are a tech news editor for an engineer who works on AI, speech recognition and NLP. Use web search. "
    "Report only stories you found on real pages; prefer primary sources (company blogs, release notes, papers) "
    "and reputable outlets. Never invent a URL, date or number. Keep every item short."
)


async def fetch_digest(llm: LLMClient, topics: list[str], days: int, today: date | None = None) -> dict:
    lines = "\n".join(f"- {t}: {TOPICS[t][0]} ({TOPICS[t][1]})" for t in topics)
    prompt = (f"Today is {(today or date.today()).isoformat()}. Find the most important tech news from the last "
              f"{days} days for each of these topics (use the id as `topic`):\n{lines}\n\n"
              "Give 3-5 items per topic, newest first. Skip rumours and minor updates. One item per story.")
    out = await llm.ask_json(prompt, NewsOut, system=SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=max(config.LLM_TIMEOUT, 600))
    items = [i.model_dump() for i in out.items if i.topic in topics]
    kept, dropped = await _check(items)
    kept.sort(key=lambda i: i["date"] or "", reverse=True)
    return {"headline": out.headline, "items": kept, "dropped": dropped}


# ---------------------------------------------------------------- live headlines (Hacker News)

_HN_CACHE: dict[str, tuple[float, list[dict]]] = {}
HN_TTL = 600  # seconds


async def hacker_news(limit: int = 20) -> list[dict]:
    """Current Hacker News front page via the public Algolia API (cached for 10 minutes)."""
    hit = _HN_CACHE.get("front")
    if hit and time.time() - hit[0] < HN_TTL:
        return hit[1][:limit]
    async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
        r = await client.get("https://hn.algolia.com/api/v1/search", params={"tags": "front_page", "hitsPerPage": 40})
        r.raise_for_status()
        hits = r.json().get("hits", [])
    items = []
    for h in sorted(hits, key=lambda h: h.get("points") or 0, reverse=True):
        disc = f"https://news.ycombinator.com/item?id={h['objectID']}"
        url = h.get("url") or disc
        items.append({"id": h["objectID"], "title": h.get("title") or "", "url": url, "discussion": disc,
                      "site": httpx.URL(url).host.removeprefix("www."), "points": h.get("points") or 0,
                      "comments": h.get("num_comments") or 0,
                      "at": datetime.fromtimestamp(h.get("created_at_i") or 0, timezone.utc).isoformat()})
    _HN_CACHE["front"] = (time.time(), items)
    return items[:limit]
