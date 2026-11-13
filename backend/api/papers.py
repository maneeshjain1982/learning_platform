"""Paper summaries. One summary per paper, shared by all accounts and stored on the paper's resource row
(meta["ai_summary"]). Any account can write a missing summary; regenerating, editing and deleting change shared
content, so they are for the admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..agents.base import upsert_resource
from ..agents.papers import PaperSummary, arxiv_id, summarize
from ..db import get_db, session_scope
from ..llm import get_llm
from ..models import Resource, User, utcnow
from ..providers import Candidate, arxiv_by_ids
from . import bgjobs
from .common import iso, require_admin, uid

router = APIRouter(prefix="/api/papers", tags=["papers"])


class PaperRef(BaseModel):
    resource_id: int | None = None
    url: str | None = Field(None, max_length=1000)
    title: str | None = Field(None, max_length=500)


def _resolve(db: Session, ref: PaperRef) -> Resource:
    """The paper's resource row: by id, or by arXiv URL/id (created if new)."""
    if ref.resource_id:
        r = db.get(Resource, ref.resource_id)
        if r is None or r.kind != "paper":
            raise HTTPException(404, "Paper not found")
        return r
    aid = arxiv_id(ref.url or "")
    if not aid:
        raise HTTPException(422, "Summaries work for saved papers and arXiv links.")
    return upsert_resource(db, Candidate(kind="paper", source="arxiv", external_id=aid,
                                         title=(ref.title or "").strip() or f"arXiv:{aid}",
                                         url=f"https://arxiv.org/abs/{aid}"))


def _out(db: Session, r: Resource) -> dict:
    st = bgjobs.public(bgjobs.read(db.get(User, uid()), f"paper:{r.id}"))
    s = (r.meta or {}).get("ai_summary")
    return {"resource_id": r.id, "title": r.title, "url": r.url, "summary": s,
            "job": {k: st.get(k) for k in ("status", "error", "started_at", "fetched_at")}}


@router.post("/summary/lookup")
def get_summary(ref: PaperRef, db: Session = Depends(get_db)):
    """Read a summary (POST because the paper is given by id or URL)."""
    r = _resolve(db, ref)
    db.commit()
    return _out(db, r)


class GenerateIn(PaperRef):
    context: str = Field("", max_length=300, description="What the reader is studying, e.g. the lesson title")


@router.post("/summary")
async def generate(body: GenerateIn, db: Session = Depends(get_db)):
    r = _resolve(db, body)
    if (r.meta or {}).get("ai_summary"):
        require_admin(db)  # replacing a shared summary
    db.commit()
    rid, title, url, abstract = r.id, r.title, r.url, r.summary
    aid = r.external_id if r.source == "arxiv" else arxiv_id(r.url)

    async def work(_prev: dict) -> dict:
        nonlocal title, abstract
        if aid and (not abstract or title.startswith("arXiv:")):
            found = await arxiv_by_ids([aid])  # fill in the real title and abstract
            if found:
                title, abstract = found[0].title, found[0].summary
        s = await summarize(get_llm(), title=title, url=url, abstract=abstract, context=body.context, aid=aid)
        with session_scope() as db2:
            res = db2.get(Resource, rid)
            if title != res.title and res.title.startswith("arXiv:"):
                res.title = title
            if abstract and not res.summary:
                res.summary = abstract
            res.meta = {**(res.meta or {}), "ai_summary": {**s, "written_at": iso(utcnow()), "edited": False}}
        return {}

    bgjobs.start(db, f"paper:{rid}", work)
    return _out(db, r)


class EditIn(PaperSummary):
    resource_id: int
    read_full_text: bool = False


@router.put("/summary")
def edit(body: EditIn, db: Session = Depends(get_db)):
    require_admin(db)
    r = _resolve(db, PaperRef(resource_id=body.resource_id))
    old = (r.meta or {}).get("ai_summary") or {}
    data = body.model_dump(exclude={"resource_id"})
    data["results"] = [x.strip() for x in data["results"] if x.strip()]
    data["limitations"] = [x.strip() for x in data["limitations"] if x.strip()]
    r.meta = {**(r.meta or {}), "ai_summary": {**old, **data, "edited": True}}
    db.commit()
    return _out(db, r)


@router.delete("/summary/{resource_id}")
def delete(resource_id: int, db: Session = Depends(get_db)):
    require_admin(db)
    r = _resolve(db, PaperRef(resource_id=resource_id))
    r.meta = {k: v for k, v in (r.meta or {}).items() if k != "ai_summary"}
    db.commit()
    return {"ok": True}
