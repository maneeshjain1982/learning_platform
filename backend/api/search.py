from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.base import upsert_resource
from ..agents.search import VideoSearchAgent
from ..db import get_db
from ..llm import LLMUnavailable, get_llm
from ..models import CacheEntry, Resource, SavedResource, utcnow
from ..providers import paper_search, search_links
from .common import uid, get_or_404, resource_out, saved_ids

router = APIRouter(prefix="/api", tags=["search"])
CACHE_TTL = timedelta(days=1)


def _cached(db: Session, key: str):
    entry = db.get(CacheEntry, key)
    if entry and utcnow() - entry.fetched_at < CACHE_TTL:
        return entry.value
    return None


def _store(db: Session, key: str, value) -> None:
    entry = db.get(CacheEntry, key)
    if entry is None:
        db.add(CacheEntry(key=key, value=value))
    else:
        entry.value, entry.fetched_at = value, utcnow()


def _resources(db: Session, ids_why: list[list]) -> list[dict]:
    saved = saved_ids(db)
    out = []
    for rid, why in ids_why:
        r = db.get(Resource, rid)
        if r:
            out.append(resource_out(r, why=why, saved=saved))
    return out


@router.get("/search/papers")
async def search_papers(q: str = Query(min_length=2, max_length=200), db: Session = Depends(get_db)):
    key = f"papers:{q.strip().lower()}"
    hit = _cached(db, key)
    if hit is None:
        cands = await paper_search(q, limit=12)
        hit = [[upsert_resource(db, c).id, ""] for c in cands]
        _store(db, key, hit)
        db.commit()
    return _resources(db, hit)


class VideoSearchIn(BaseModel):
    q: str = Field(min_length=2, max_length=200)
    level: str = "intermediate"


@router.post("/search/videos")
async def search_videos(body: VideoSearchIn, db: Session = Depends(get_db)):
    key = f"videos:{body.level}:{body.q.strip().lower()}"
    hit = _cached(db, key)
    if hit is None:
        try:
            found = await VideoSearchAgent(get_llm()).free_search(body.q, body.level)
        except LLMUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        hit = [[upsert_resource(db, c).id, why] for c, why in found]
        _store(db, key, hit)
        db.commit()
    return _resources(db, hit)


@router.get("/search/links")
def links(q: str = Query(min_length=1, max_length=200)):
    return search_links(q)


@router.get("/saved")
def saved(db: Session = Depends(get_db)):
    rows = db.scalars(select(SavedResource).where(SavedResource.user_id == uid())
                      .order_by(SavedResource.saved_at.desc()))
    return [resource_out(s.resource, saved={s.resource_id}) for s in rows]


@router.post("/resources/{resource_id}/save")
def save(resource_id: int, db: Session = Depends(get_db)):
    get_or_404(db, Resource, resource_id)
    if not db.get(SavedResource, (uid(), resource_id)):
        db.add(SavedResource(user_id=uid(), resource_id=resource_id))
        db.commit()
    return {"saved": True}


@router.delete("/resources/{resource_id}/save")
def unsave(resource_id: int, db: Session = Depends(get_db)):
    s = db.get(SavedResource, (uid(), resource_id))
    if s:
        db.delete(s)
        db.commit()
    return {"saved": False}
