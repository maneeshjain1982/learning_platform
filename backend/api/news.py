"""Tech News: live Hacker News headlines and a per-account LLM digest by topic (topics, hidden items)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..agents.news import DEFAULT_TOPICS, TOPICS, fetch_digest, hacker_news
from ..db import get_db
from ..llm import get_llm
from ..models import User
from . import bgjobs
from .common import uid

log = logging.getLogger("study.news")
router = APIRouter(prefix="/api/news", tags=["news"])
KEY = "tech-news"


def _prefs(user: User) -> dict:
    p = dict((user.settings or {}).get("news") or {})
    return {"topics": [t for t in p.get("topics") or DEFAULT_TOPICS if t in TOPICS], "hidden": list(p.get("hidden") or [])}


def _save_prefs(user: User, prefs: dict) -> None:
    user.settings = {**(user.settings or {}), "news": prefs}


def _out(db: Session) -> dict:
    user = db.get(User, uid())
    prefs = _prefs(user)
    st = bgjobs.read(user, KEY)
    pub = bgjobs.public(st)
    hidden = set(prefs["hidden"])
    return {"status": pub["status"], "error": pub["error"], "started_at": pub["started_at"],
            "fetched_at": pub["fetched_at"], "headline": st.get("headline", ""),
            "items": [i for i in st.get("items", []) if i["url"] not in hidden], "dropped": st.get("dropped", 0),
            "days": (st.get("params") or {}).get("days", 7), "topics": prefs["topics"],
            "all_topics": [{"id": k, "label": v[0]} for k, v in TOPICS.items()]}


@router.get("")
def get_news(db: Session = Depends(get_db)):
    return _out(db)


class RefreshIn(BaseModel):
    days: int = Field(7, ge=1, le=30)
    topics: list[str] | None = Field(None, max_length=len(TOPICS))


@router.post("/refresh")
async def refresh(body: RefreshIn | None = None, db: Session = Depends(get_db)):
    body = body or RefreshIn()
    user = db.get(User, uid())
    prefs = _prefs(user)
    if body.topics is not None:
        if not body.topics or any(t not in TOPICS for t in body.topics):
            raise HTTPException(422, "Pick at least one known topic.")
        prefs["topics"] = list(dict.fromkeys(body.topics))
        _save_prefs(user, prefs)
    topics = prefs["topics"]

    async def work(_prev: dict) -> dict:
        return await fetch_digest(get_llm(), topics, body.days)

    bgjobs.start(db, KEY, work, days=body.days, topics=topics)
    return _out(db)


class HideIn(BaseModel):
    url: str = Field(min_length=8, max_length=1000)
    hidden: bool = True


@router.post("/hide")
def hide(body: HideIn, db: Session = Depends(get_db)):
    """Remove an item from your digest (or bring it back)."""
    user = db.get(User, uid())
    prefs = _prefs(user)
    s = set(prefs["hidden"])
    s.add(body.url) if body.hidden else s.discard(body.url)
    prefs["hidden"] = sorted(s)[-500:]
    _save_prefs(user, prefs)
    db.commit()
    return {"ok": True}


@router.get("/live")
async def live(limit: int = 20):
    try:
        return {"items": await hacker_news(min(max(limit, 1), 40)), "error": None}
    except Exception as exc:  # network down, API change
        log.warning("Hacker News fetch failed: %s", exc)
        return {"items": [], "error": "Couldn't load live headlines right now."}
