"""Sign-in for the two local accounts (admin and user), sessions and the current user.

Every /api request (except /api/auth/*) needs a session cookie. The signed-in user's id is kept in a context
variable, so request handlers and the background tasks they start read it with `uid()`.
Admin-only areas (Career, hot jobs, Upskill Prep) answer 403 for other accounts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from contextvars import ContextVar
from datetime import timedelta
from http.cookies import SimpleCookie

from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import AuthSession, User, utcnow

COOKIE = "sc_session"
SESSION_DAYS = 30
ADMIN_ID, USER_ID = 1, 2
# (id, username, default password, role, display name)
ACCOUNTS = [(ADMIN_ID, "admin", "admin", "admin", "Admin"), (USER_ID, "user", "user", "user", "User")]
ADMIN_PREFIXES = ("/api/career", "/api/interviews", "/api/interview-")

_current: ContextVar[int] = ContextVar("current_user_id", default=ADMIN_ID)


def uid() -> int:
    """Id of the signed-in user (the admin account for scripts and startup work)."""
    return _current.get()


def user_slug(base: str, user_id: int | None = None) -> str:
    """Path slugs are unique; the admin keeps the plain slug, other accounts get a suffix."""
    user_id = user_id or uid()
    return base if user_id == ADMIN_ID else f"{base}@u{user_id}"


def base_slug(slug: str) -> str:
    return slug.split("@u", 1)[0]


def set_uid(user_id: int):
    return _current.set(user_id)


# ---------------------------------------------------------------- passwords

def hash_password(password: str, *, salt: str | None = None, iterations: int = 200_000) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def check_password(password: str, stored: str | None) -> bool:
    try:
        _, iterations, salt, _digest = (stored or "").split("$")
        return hmac.compare_digest(hash_password(password, salt=salt, iterations=int(iterations)), stored)
    except ValueError:
        return False


def is_default_password(user: User) -> bool:
    default = next((pw for i, _, pw, _, _ in ACCOUNTS if i == user.id), None)
    return default is not None and check_password(default, user.password_hash)


def ensure_accounts(db: Session) -> list[User]:
    """Create the admin and user accounts if missing. The existing single user (id 1) becomes admin."""
    out = []
    for id_, username, password, role, name in ACCOUNTS:
        u = db.get(User, id_)
        if u is None:
            u = User(id=id_, name=name, settings={})
            db.add(u)
        if not u.username:
            u.username = username
        if not u.password_hash:
            u.password_hash = hash_password(password)
        u.role = role
        out.append(u)
    db.flush()
    return out


# ---------------------------------------------------------------- sessions

def new_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token=token, user_id=user.id, expires_at=utcnow() + timedelta(days=SESSION_DAYS)))
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    s = db.get(AuthSession, token)
    if s is None or s.expires_at < utcnow():
        return None
    return db.get(User, s.user_id)


class AuthMiddleware:
    """Plain ASGI middleware: resolves the session cookie, sets the current user, guards /api."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/") or scope["path"].startswith("/api/auth/") \
                or scope["path"] == "/api/health":
            return await self.app(scope, receive, send)
        token = None
        for k, v in scope.get("headers") or []:
            if k == b"cookie":
                c = SimpleCookie()
                c.load(v.decode("latin-1"))
                if COOKIE in c:
                    token = c[COOKIE].value
        with SessionLocal() as db:
            user = user_for_token(db, token)
            role = user.role if user else None
            user_id = user.id if user else None
        if user_id is None:
            return await _deny(send, 401, "Please sign in.")
        if role != "admin" and scope["path"].startswith(ADMIN_PREFIXES):
            return await _deny(send, 403, "This area is for the admin account.")
        reset = set_uid(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _current.reset(reset)


async def _deny(send, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}).encode()
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
    await send({"type": "http.response.body", "body": body})
