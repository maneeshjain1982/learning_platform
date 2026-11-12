from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents.tutor import Tutor
from ..db import get_db
from ..llm import LLMUnavailable, get_llm
from ..models import ChatMessage, ChatSession, Lesson
from .common import USER_ID, get_or_404, iso

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ContextFlags(BaseModel):
    lesson: bool = True
    level: bool = True
    path: bool = True


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: int | None = None
    lesson_id: int | None = None
    context: ContextFlags = ContextFlags()


def msg_out(m: ChatMessage) -> dict:
    return {"id": m.id, "role": m.role, "content": m.content, "meta": m.meta or {}, "created_at": iso(m.created_at)}


def session_out(s: ChatSession, with_messages: bool = True) -> dict:
    out = {"id": s.id, "title": s.title, "lesson_id": s.lesson_id, "created_at": iso(s.created_at)}
    if with_messages:
        out["messages"] = [msg_out(m) for m in s.messages]
    return out


@router.post("")
async def ask(body: ChatIn, db: Session = Depends(get_db)):
    if body.session_id:
        session = get_or_404(db, ChatSession, body.session_id)
    else:
        session = ChatSession(user_id=USER_ID, lesson_id=body.lesson_id, title=body.message[:80])
        db.add(session)
        db.flush()

    history = [(m.role, m.content) for m in session.messages if m.role in ("user", "assistant")]
    user_msg = ChatMessage(session_id=session.id, role="user", content=body.message)
    db.add(user_msg)
    db.commit()

    context: dict = {}
    lesson_id = body.lesson_id or session.lesson_id
    if lesson_id:
        lesson = db.get(Lesson, lesson_id)
        if lesson:
            path = lesson.module.path
            if body.context.path:
                context["path"] = path.title
            if body.context.level:
                context["level"] = path.level
            if body.context.lesson:
                context["lesson"] = f"{lesson.module.title} › {lesson.title}"
                context["objectives"] = lesson.objectives
                context["notes"] = lesson.content_md or ""

    try:
        ans = await Tutor(get_llm()).answer(question=body.message, history=history, context=context)
        reply = ChatMessage(session_id=session.id, role="assistant", content=ans.text,
                            meta={"model": ans.model, "provider": ans.provider, "duration_ms": ans.duration_ms,
                                  "context": [k for k in ("lesson", "level", "path") if k in context]})
    except LLMUnavailable as exc:
        reply = ChatMessage(session_id=session.id, role="error", content=str(exc))
    db.add(reply)
    db.commit()
    return {"session_id": session.id, "user": msg_out(user_msg), "reply": msg_out(reply)}


@router.get("/sessions")
def sessions(lesson_id: int | None = None, db: Session = Depends(get_db)):
    q = select(ChatSession).where(ChatSession.user_id == USER_ID).order_by(ChatSession.id.desc()).limit(30)
    if lesson_id:
        q = q.where(ChatSession.lesson_id == lesson_id)
    return [session_out(s, with_messages=False) for s in db.scalars(q)]


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    return session_out(get_or_404(db, ChatSession, session_id))


@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, ChatSession, session_id))
    db.commit()
    return {"ok": True}


@router.post("/messages/{message_id}/save-to-notes")
def save_to_notes(message_id: int, db: Session = Depends(get_db)):
    msg = get_or_404(db, ChatMessage, message_id)
    session = db.get(ChatSession, msg.session_id)
    if not session.lesson_id:
        raise HTTPException(400, "This chat is not linked to a lesson.")
    lesson = db.get(Lesson, session.lesson_id)
    lesson.user_notes = (lesson.user_notes + "\n\n" if lesson.user_notes else "") + \
        f"**Q: {session.messages[max(0, session.messages.index(msg) - 1)].content}**\n\n{msg.content}"
    db.commit()
    return {"ok": True, "user_notes": lesson.user_notes}
