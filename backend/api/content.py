"""Edit, delete (admin, for everyone) or hide (any account, just for you) built-in catalog items."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete as sql_delete
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ContentEdit, User
from ..overlay import KINDS, kind_of
from .common import uid

router = APIRouter(prefix="/api/content", tags=["content"])


class Target(BaseModel):
    scope: str = Field(max_length=60)
    key: str = Field("", max_length=300)


class EditIn(Target):
    fields: dict[str, str]


def _kind(scope: str) -> str:
    k = kind_of(scope)
    if k is None:
        raise HTTPException(404, f"Unknown content '{scope}'")
    return k


def _user(db: Session) -> User:
    return db.get(User, uid())


def _row(db: Session, t: Target) -> ContentEdit:
    row = db.get(ContentEdit, (t.scope, t.key))
    if row is None:
        row = ContentEdit(scope=t.scope, key=t.key, fields={}, hidden=False)
        db.add(row)
    return row


@router.post("/edit")
def edit(body: EditIn, db: Session = Depends(get_db)):
    kind = _kind(body.scope)
    if _user(db).role != "admin":
        raise HTTPException(403, "Only the admin account can edit shared content.")
    allowed = KINDS[kind][1]
    if bad := [f for f in body.fields if f not in allowed]:
        raise HTTPException(422, f"Can't edit: {', '.join(bad)}")
    row = _row(db, body)
    row.fields = {**(row.fields or {}), **{k: v.strip() for k, v in body.fields.items()}}
    db.commit()
    return {"ok": True}


@router.post("/delete")
def delete(body: Target, db: Session = Depends(get_db)):
    """Admin: delete for every account. Other accounts: hide just for themselves."""
    _kind(body.scope)
    user = _user(db)
    if user.role == "admin":
        _row(db, body).hidden = True
    else:
        hidden = dict((user.settings or {}).get("hidden_items") or {})
        hidden[body.scope] = sorted(set(hidden.get(body.scope) or []) | {body.key})
        user.settings = {**(user.settings or {}), "hidden_items": hidden}
    db.commit()
    return {"ok": True, "for_everyone": user.role == "admin"}


@router.post("/reset")
def reset(body: Target, db: Session = Depends(get_db)):
    """Bring back the original list: your hidden items, and for the admin also every edit and deletion."""
    _kind(body.scope)
    user = _user(db)
    hidden = dict((user.settings or {}).get("hidden_items") or {})
    hidden.pop(body.scope, None)
    user.settings = {**(user.settings or {}), "hidden_items": hidden}
    if user.role == "admin":
        db.execute(sql_delete(ContentEdit).where(ContentEdit.scope == body.scope))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- items found by the LLM research jobs

# job key -> list field holding the items (each item has a url). Results are per account.
JOB_LISTS = {"updates": "items", "certs": "items", "jobs": "jobs", "hv-research": "items", "ev-research": "items"}
ADMIN_JOBS = {"certs", "jobs"}


class JobItemIn(BaseModel):
    job: str = Field(max_length=40)
    url: str = Field(max_length=1000)


@router.post("/job-item/remove")
def remove_job_item(body: JobItemIn, db: Session = Depends(get_db)):
    """Delete one found item (a news update, certification change, job posting, research find) from your list."""
    from . import bgjobs
    field = JOB_LISTS.get(body.job)
    if field is None:
        raise HTTPException(404, "Unknown list")
    user = _user(db)
    if body.job in ADMIN_JOBS and user.role != "admin":
        raise HTTPException(403, "This area is for the admin account.")
    st = bgjobs.read(user, body.job)
    items = st.get(field) or []
    kept = [i for i in items if i.get("url") != body.url]
    if len(kept) == len(items):
        raise HTTPException(404, "Item not found")
    bgjobs.write(db, body.job, **{field: kept})
    db.commit()
    return {"ok": True}
