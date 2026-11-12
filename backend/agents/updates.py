"""News agent: searches the web for the latest Claude, agent-building and Claude Academy updates.

Every link the model returns is checked: dead links are dropped, and links whose site refuses automated checks
are kept but marked unverified.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from ..providers import check_url

log = logging.getLogger("study.updates")

Category = Literal["Claude Academy", "Models & API", "Claude Code & agents", "MCP & tools", "Agentic AI"]
CATEGORIES: list[str] = list(Category.__args__)  # type: ignore[attr-defined]


class UpdateItem(BaseModel):
    title: str = Field(description="Short headline in your own words")
    date: str = Field(description="Publication or release date as YYYY-MM-DD, or empty if the page shows none")
    category: Category
    summary: str = Field(description="2-3 sentences: what changed, with concrete names and numbers")
    why_it_matters: str = Field(description="One sentence on why this matters to someone learning to build agents")
    url: str = Field(description="Full https URL of the page you read for this item (the primary source)")
    new_course: bool = Field(False, description="True only for a Claude Academy course missing from the known list")


class UpdatesOut(BaseModel):
    headline: str = Field(description="One sentence: the single most important change in this period")
    items: list[UpdateItem] = Field(description="8-15 updates, newest first")


SYSTEM = (
    "You are a research assistant tracking news for an engineer who is learning to build AI agents with Claude "
    "and preparing for Agentic AI Architect roles. Use web search. Report only things you found on real pages, "
    "and prefer primary sources: anthropic.com, claude.com, docs.claude.com, academy.claude.com, "
    "modelcontextprotocol.io, github.com/anthropics, and papers on arxiv.org. Never invent a URL, date or version."
)


def build_prompt(today: date, known_courses: list[str], days: int) -> str:
    courses = "\n".join(f"- {t}" for t in known_courses)
    return (
        f"Today is {today.isoformat()}. Find the most important updates from the last {days} days in these areas:\n"
        "1. Claude Academy (academy.claude.com): new or reworked courses. Known courses:\n"
        f"{courses}\n"
        "   Flag any course not on that list with new_course=true.\n"
        "2. Models & API: new Claude models, API features, pricing or deprecations.\n"
        "3. Claude Code & agents: Claude Code, the Claude Agent SDK, managed agents, subagents, skills, hooks.\n"
        "4. MCP & tools: Model Context Protocol spec and SDK changes, notable servers, tool-use features.\n"
        "5. Agentic AI: one to three important agent papers, benchmarks or industry patterns from any lab.\n"
        "Cover every area: aim for 2-3 items per area and 8-15 in total, newest first. Search each area "
        "separately (release notes, blogs, GitHub releases, changelogs). If an area had nothing new in this window, "
        "include its most recent important change even if older. Skip rumours and anything you could not open."
    )


async def fetch_updates(llm: LLMClient, known_courses: list[str], *, days: int = 45,
                        today: date | None = None) -> dict:
    out = await llm.ask_json(build_prompt(today or date.today(), known_courses, days), UpdatesOut, system=SYSTEM,
                             model=config.LLM_MODEL, web=True, timeout=max(config.LLM_TIMEOUT, 600))
    seen, items = set(), []
    for it in out.items:
        url = it.url.strip()
        if url and url not in seen:
            seen.add(url)
            items.append(it.model_dump() | {"url": url})
    states = await asyncio.gather(*(check_url(i["url"]) for i in items))
    kept = []
    for item, state in zip(items, states):
        if state == "dead":
            log.info("Dropped update with dead link: %s", item["url"])
            continue
        kept.append(item | {"verified": state == "ok"})
    kept.sort(key=lambda i: i["date"] or "", reverse=True)
    return {"headline": out.headline, "items": kept, "dropped": len(items) - len(kept)}
