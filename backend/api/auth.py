"""Sign in, sign out, who am I, change password."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import COOKIE, SESSION_DAYS, check_password, hash_password, is_default_password, new_session, \
    user_for_token
from ..db import get_db
from ..models import AuthSession, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=200)


class PasswordIn(BaseModel):
    current: str = Field(min_length=1, max_length=200)
    new: str = Field(min_length=4, max_length=200)


def me_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "name": u.name, "role": u.role, "is_admin": u.role == "admin",
            "default_password": is_default_password(u)}


def _signed_in(request: Request, db: Session) -> User:
    user = user_for_token(db, request.cookies.get(COOKIE))
    if user is None:
        raise HTTPException(401, "Please sign in.")
    return user


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == body.username.strip().lower())).first()
    if user is None or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password.")
    token = new_session(db, user)
    db.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", path="/")
    return me_out(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    if (token := request.cookies.get(COOKIE)) and (s := db.get(AuthSession, token)):
        db.delete(s)
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    return me_out(_signed_in(request, db))


@router.post("/password")
def change_password(body: PasswordIn, request: Request, db: Session = Depends(get_db)):
    user = _signed_in(request, db)
    if not check_password(body.current, user.password_hash):
        raise HTTPException(400, "Your current password is wrong.")
    user.password_hash = hash_password(body.new)
    db.commit()
    return me_out(user)
