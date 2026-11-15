"""Account management for the admin: create accounts, reset passwords, change roles, delete accounts."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import hash_password, is_default_password, uid
from ..db import Base, get_db
from ..models import AuthSession, LearningPath, User
from .common import iso, require_admin, spawn

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
Role = Literal["admin", "user"]


def _admin(db: Session = Depends(get_db)) -> Session:
    require_admin(db)
    return db


def account_out(db: Session, u: User) -> dict:
    last = db.scalar(select(func.max(AuthSession.created_at)).where(AuthSession.user_id == u.id))
    return {"id": u.id, "username": u.username, "name": u.name, "role": u.role, "is_you": u.id == uid(),
            "default_password": is_default_password(u), "created_at": iso(u.created_at), "last_sign_in": iso(last)}


def _admins(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0


@router.get("")
def list_accounts(db: Session = Depends(_admin)):
    return [account_out(db, u) for u in db.scalars(select(User).order_by(User.id))]


class AccountIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    name: str = Field("", max_length=120)
    password: str = Field(min_length=4, max_length=200)
    role: Role = "user"


@router.post("")
async def create_account(body: AccountIn, db: Session = Depends(_admin)):
    username = body.username.strip().lower()
    if not USERNAME.match(username):
        raise HTTPException(422, "Username: 3–40 characters, letters, numbers, dot, dash or underscore, "
                                 "starting with a letter or number.")
    if db.scalars(select(User).where(func.lower(User.username) == username)).first():
        raise HTTPException(409, f"The username “{username}” is already taken.")
    u = User(username=username, name=body.name.strip() or username, role=body.role,
             password_hash=hash_password(body.password), settings={})
    db.add(u)
    db.flush()
    # Same starting point as the built-in accounts: the starter learning paths (papers attach in the background).
    from ..seed import attach_seed_papers, seed_structure
    created = seed_structure(db, [u.id])
    db.commit()
    if created:
        spawn(attach_seed_papers())
    return account_out(db, u)


class AccountPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    role: Role | None = None
    password: str | None = Field(None, min_length=4, max_length=200)


@router.patch("/{account_id}")
def update_account(account_id: int, body: AccountPatch, db: Session = Depends(_admin)):
    u = db.get(User, account_id)
    if u is None:
        raise HTTPException(404, "Account not found.")
    if body.role and body.role != u.role and u.role == "admin" and _admins(db) <= 1:
        raise HTTPException(409, "This is the only admin account, so it must stay admin.")
    if body.name is not None:
        u.name = body.name.strip()
    if body.role is not None:
        u.role = body.role
    if body.password is not None:
        u.password_hash = hash_password(body.password)
        if u.id != uid():  # sign the account out everywhere so the new password takes effect
            for s in db.scalars(select(AuthSession).where(AuthSession.user_id == u.id)):
                db.delete(s)
    db.commit()
    return account_out(db, u)


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(_admin)):
    u = db.get(User, account_id)
    if u is None:
        raise HTTPException(404, "Account not found.")
    if u.id == uid():
        raise HTTPException(409, "You can't delete the account you're signed in with.")
    if u.role == "admin" and _admins(db) <= 1:
        raise HTTPException(409, "You can't delete the only admin account.")
    try:
        for path in db.scalars(select(LearningPath).where(LearningPath.user_id == u.id)):
            db.delete(path)  # modules, lessons and progress go with it
        db.flush()
        # Every other row owned by this account, dependents first.
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == "users":
                continue
            for col in table.columns:
                if any(fk.column.table.name == "users" for fk in col.foreign_keys):
                    db.execute(table.delete().where(col == u.id))
        db.delete(u)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, f"Couldn't delete this account: {exc}") from exc
    return {"ok": True}
