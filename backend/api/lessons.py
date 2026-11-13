from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..agents import orchestrator
from ..agents.base import attach
from ..db import get_db
from ..models import Lesson, LessonResource, Progress, Resource, utcnow
from .common import uid, get_or_404, lesson_resources, module_links, progress_map, saved_ids, spawn

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


def lesson_out(db: Session, lesson: Lesson) -> dict:
    module, path = lesson.module, lesson.module.path
    all_lessons = [l for m in path.modules for l in m.lessons]
    i = all_lessons.index(lesson)
    prog = progress_map(db, [l.id for l in all_lessons])
    p = prog.get(lesson.id)
    nav = lambda l: {"id": l.id, "title": l.title} if l else None  # noqa: E731
    return {
        "id": lesson.id, "idx": lesson.idx, "title": lesson.title, "objectives": lesson.objectives,
        "keywords": lesson.keywords, "est_minutes": lesson.est_minutes, "content_md": lesson.content_md,
        "notes_status": lesson.notes_status, "user_notes": lesson.user_notes,
        "status": p.status if p else "todo",
        "module": {"id": module.id, "idx": module.idx, "title": module.title, "lessons": len(module.lessons),
                   "resources_status": module.resources_status},
        "path": {"id": path.id, "title": path.title, "level": path.level},
        "prev": nav(all_lessons[i - 1] if i > 0 else None),
        "next": nav(all_lessons[i + 1] if i + 1 < len(all_lessons) else None),
        "resources": lesson_resources(db, [lesson.id], saved_ids(db))[lesson.id],
        "links": module_links(lesson.keywords or module.keywords, lesson.title),
    }


@router.get("/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    return lesson_out(db, get_or_404(db, Lesson, lesson_id))


@router.post("/{lesson_id}/notes")
async def generate_notes(lesson_id: int, force: bool = False, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    if lesson.notes_status == "writing":
        return {"notes_status": "writing"}
    if lesson.content_md and not force:
        return {"notes_status": "ready"}
    lesson.notes_status = "writing"
    db.commit()
    spawn(orchestrator.write_lesson_notes(lesson_id))
    return {"notes_status": "writing"}


class ContentIn(BaseModel):
    content_md: str = Field(min_length=1, max_length=200_000)


@router.put("/{lesson_id}/content")
def edit_notes(lesson_id: int, body: ContentIn, db: Session = Depends(get_db)):
    """Replace the lesson notes with your own edited version."""
    lesson = get_or_404(db, Lesson, lesson_id)
    if lesson.notes_status == "writing":
        raise HTTPException(409, "The notes are being written; try again when they're ready.")
    lesson.content_md, lesson.notes_status = body.content_md, "ready"
    db.commit()
    return lesson_out(db, lesson)


@router.delete("/{lesson_id}/content")
def delete_notes(lesson_id: int, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    lesson.content_md, lesson.notes_status = None, "deleted"  # not "none": that would auto-write new notes
    db.commit()
    return lesson_out(db, lesson)


class UserNotesIn(BaseModel):
    text: str = Field(max_length=100_000)


@router.put("/{lesson_id}/user-notes")
def save_user_notes(lesson_id: int, body: UserNotesIn, db: Session = Depends(get_db)):
    lesson = get_or_404(db, Lesson, lesson_id)
    lesson.user_notes = body.text
    db.commit()
    return {"ok": True}


class ProgressIn(BaseModel):
    status: Literal["todo", "doing", "done"]
    minutes: int = Field(0, ge=0, le=600)


@router.post("/{lesson_id}/progress")
def set_progress(lesson_id: int, body: ProgressIn, db: Session = Depends(get_db)):
    get_or_404(db, Lesson, lesson_id)
    p = db.get(Progress, (uid(), lesson_id))
    if body.status == "todo":
        if p:
            db.delete(p)
    else:
        if p is None:
            p = Progress(user_id=uid(), lesson_id=lesson_id, status="doing", minutes_spent=0)
            db.add(p)
        if body.status == "done" and p.status != "done":
            p.completed_at = utcnow()
        if body.status == "doing" and p.status == "done":
            return {"status": "done"}  # opening a finished lesson doesn't un-finish it
        p.status = body.status
        p.minutes_spent += body.minutes
    db.commit()
    return {"status": body.status}


class AttachIn(BaseModel):
    resource_id: int
    why: str = "Added by you."


@router.post("/{lesson_id}/resources")
def add_resource(lesson_id: int, body: AttachIn, db: Session = Depends(get_db)):
    get_or_404(db, Lesson, lesson_id)
    get_or_404(db, Resource, body.resource_id)
    attach(db, lesson_id, body.resource_id, rank=-1, why=body.why, added_by="user")
    db.commit()
    return {"ok": True}


@router.delete("/{lesson_id}/resources/{resource_id}")
def remove_resource(lesson_id: int, resource_id: int, db: Session = Depends(get_db)):
    link = db.get(LessonResource, (lesson_id, resource_id))
    if link is None:
        raise HTTPException(404, "Not attached")
    db.delete(link)
    db.commit()
    return {"ok": True}
