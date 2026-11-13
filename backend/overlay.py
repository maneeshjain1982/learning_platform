"""Edits on top of the built-in catalogs.

The admin can edit an item's text fields or delete it for every account (rows in content_edits); any account can
hide an item just for itself (user.settings["hidden_items"]). The original researched content stays in code, so a
reset brings it back.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import uid
from .models import ContentEdit, User

# kind -> (key field, editable text fields)
KINDS: dict[str, tuple[str, list[str]]] = {
    "models": ("name", ["org", "licence", "size", "result", "notes"]),
    "datasets": ("name", ["licence", "size", "what", "use"]),
    "papers": ("id", ["title", "why"]),
    "courses": ("id", ["title", "provider", "cost", "level", "covers"]),
    "certs": ("name", ["price", "duration", "format", "validity", "focus", "fit", "notes"]),
    "claude": ("slug", ["title", "summary", "why"]),
}


def kind_of(scope: str) -> str | None:
    """voice.<lang>.<models|datasets|papers|courses>, career.certs, claude.courses"""
    parts = scope.split(".")
    if len(parts) == 3 and parts[0] == "voice" and parts[2] in ("models", "datasets", "papers", "courses"):
        from .voice_langs import LANGS
        return parts[2] if parts[1] in LANGS else None
    return {"career.certs": "certs", "claude.courses": "claude"}.get(scope)


def personal_hidden(user: User, scope: str) -> set[str]:
    return set(((user.settings or {}).get("hidden_items") or {}).get(scope) or [])


def apply(db: Session, scope: str, items: list[dict]) -> list[dict]:
    """The catalog as this account sees it: admin edits merged in, deleted and hidden items left out.
    Each item gets `_key` (for edit/hide calls) and `_edited`."""
    key_field, fields = KINDS[kind_of(scope)]
    edits = {e.key: e for e in db.scalars(select(ContentEdit).where(ContentEdit.scope == scope))}
    mine = personal_hidden(db.get(User, uid()), scope)
    out = []
    for it in items:
        k = str(it[key_field])
        e = edits.get(k)
        if k in mine or (e and e.hidden):
            continue
        changed = {f: v for f, v in ((e.fields if e else None) or {}).items() if f in fields}
        out.append({**it, **changed, "_key": k, "_edited": bool(changed)})
    return out


def hidden_count(db: Session, scope: str, items: list[dict]) -> int:
    return len(items) - len(apply(db, scope, items))
