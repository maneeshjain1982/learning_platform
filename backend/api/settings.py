from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..llm import provider_status
from ..models import User
from .common import USER_ID

router = APIRouter(prefix="/api", tags=["settings"])


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(None, max_length=200)


@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    u = db.get(User, USER_ID)
    return {"name": u.name, "email": u.email}


@router.put("/profile")
def put_profile(body: ProfileIn, db: Session = Depends(get_db)):
    u = db.get(User, USER_ID)
    u.name, u.email = body.name.strip(), body.email
    db.commit()
    return {"name": u.name, "email": u.email}


@router.get("/providers")
async def providers():
    return {
        "active": {"provider": config.LLM_PROVIDER, "model": config.LLM_MODEL, "fast_model": config.LLM_FAST_MODEL},
        "providers": await asyncio.to_thread(provider_status),
    }


@router.get("/health")
def health():
    return {"ok": True}
