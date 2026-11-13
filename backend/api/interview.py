"""Interview companion API: configure, build, skills, question bank and mock interviews."""

from __future__ import annotations

import random
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agents import interview_runs as runs
from ..agents.interview import MockInterviewer
from ..db import get_db
from ..llm import LLMUnavailable, get_llm
from ..models import (AgentRun, InterviewPrep, InterviewQuestion, InterviewSkill, LearningPath, PracticeAttempt)
from .common import uid, get_or_404, iso, path_summary, run_out, spawn

router = APIRouter(prefix="/api", tags=["interview"])

QType = Literal["concept", "design", "scenario", "hands_on", "behavioral"]
Difficulty = Literal["medium", "hard", "expert"]
Status = Literal["new", "needs_work", "confident"]


# ---------------------------------------------------------------- serializers

def _last_run(db: Session, prep_id: int) -> AgentRun | None:
    return db.scalars(select(AgentRun).where(AgentRun.interview_id == prep_id).order_by(AgentRun.id.desc())).first()


def _busy(db: Session, prep_id: int) -> None:
    run = _last_run(db, prep_id)
    if run and run.status == "running":
        raise HTTPException(409, "The agents are still working on this companion. Try again when they finish.")


def config_out(p: InterviewPrep) -> dict:
    return {
        "id": p.id, "role_title": p.role_title, "company": p.company, "jd_text": p.jd_text, "seniority": p.seniority,
        "interview_date": p.interview_date.isoformat() if p.interview_date else None,
        "hours_per_week": p.hours_per_week, "background": p.background, "focus_notes": p.focus_notes,
        "question_types": p.question_types or runs.ALL_QTYPES, "questions_per_area": p.questions_per_area,
        "question_bar": p.question_bar, "web_research": p.web_research, "status": p.status, "path_id": p.path_id,
        "created_at": iso(p.created_at),
    }


def question_out(q: InterviewQuestion, skill_names: dict[int, str], *, with_answer: bool = True) -> dict:
    last = q.attempts[-1] if q.attempts else None
    out = {
        "id": q.id, "area": q.area, "skill_id": q.skill_id, "skill_name": skill_names.get(q.skill_id or -1),
        "qtype": q.qtype, "difficulty": q.difficulty, "question": q.question, "status": q.status,
        "source": q.source, "attempts": len(q.attempts), "last_score": last.score if last else None,
    }
    if with_answer:
        out.update(answer_md=q.answer_md, key_points=q.key_points, follow_ups=q.follow_ups, red_flags=q.red_flags,
                   references=q.references)
    return out


def attempt_out(a: PracticeAttempt) -> dict:
    return {"id": a.id, "question_id": a.question_id, "answer": a.answer, "score": a.score, "verdict": a.verdict,
            "strengths": a.strengths, "missing": a.missing, "better_answer_md": a.better_answer_md,
            "follow_up": a.follow_up, "created_at": iso(a.created_at)}


def summary_out(db: Session, p: InterviewPrep) -> dict:
    run = _last_run(db, p.id)
    st = runs.stats(db, p)
    return {**config_out(p), "readiness": st["readiness"], "days_left": st["days_left"],
            "questions": st["questions"], "skills": st["skills"],
            "last_run": {"id": run.id, "status": run.status, "kind": run.kind} if run else None}


# ---------------------------------------------------------------- configure + build

class PrepIn(BaseModel):
    role_title: str = Field(min_length=2, max_length=200)
    company: str = Field("", max_length=200)
    jd_text: str = Field("", max_length=30_000)
    seniority: Literal["senior", "staff", "principal", "lead"] = "senior"
    interview_date: date | None = None
    hours_per_week: int = Field(8, ge=1, le=60)
    background: str = Field("", max_length=10_000)
    focus_notes: str = Field("", max_length=4000)
    question_types: list[QType] = Field(default_factory=lambda: list(runs.ALL_QTYPES), min_length=1)
    questions_per_area: int = Field(6, ge=1, le=20)
    question_bar: Literal["top_ai", "big_tech", "standard"] = "top_ai"
    web_research: bool = True


@router.post("/interviews")
async def create_prep(body: PrepIn, db: Session = Depends(get_db)):
    prep = InterviewPrep(user_id=uid(), **{**body.model_dump(), "role_title": body.role_title.strip(),
                                            "company": body.company.strip()})
    db.add(prep)
    db.commit()
    run_id = runs.start_build(prep.id)
    spawn(runs.run_build(run_id, prep.id))
    return {"id": prep.id, "run_id": run_id}


@router.get("/interviews")
def list_preps(db: Session = Depends(get_db)):
    preps = db.scalars(select(InterviewPrep).where(InterviewPrep.user_id == uid()).order_by(InterviewPrep.id.desc()))
    return [summary_out(db, p) for p in preps]


@router.get("/interviews/{prep_id}")
def get_prep(prep_id: int, db: Session = Depends(get_db)):
    p = get_or_404(db, InterviewPrep, prep_id)
    counts: dict[int, int] = {}
    for q in p.questions:
        if q.skill_id:
            counts[q.skill_id] = counts.get(q.skill_id, 0) + 1
    path = db.get(LearningPath, p.path_id) if p.path_id else None
    run = _last_run(db, p.id)
    return {
        **config_out(p),
        "jd_analysis": p.jd_analysis or None, "research": p.research or None, "coach_note": p.coach_note,
        "skills": [{"id": s.id, "area": s.area, "name": s.name, "importance": s.importance, "evidence": s.evidence,
                    "in_jd": s.in_jd, "how_tested": s.how_tested, "self_rating": s.self_rating,
                    "questions": counts.get(s.id, 0)} for s in p.skills],
        "areas": list(dict.fromkeys([s.area for s in p.skills] + [q.area for q in p.questions if q.area])),
        "stats": runs.stats(db, p),
        "path": path_summary(db, path) if path else None,
        "last_run": run_out(run) if run else None,
    }


class PrepPatch(BaseModel):
    role_title: str | None = Field(None, min_length=2, max_length=200)
    company: str | None = Field(None, max_length=200)
    jd_text: str | None = Field(None, max_length=30_000)
    seniority: Literal["senior", "staff", "principal", "lead"] | None = None
    interview_date: date | None = None
    clear_date: bool = False
    hours_per_week: int | None = Field(None, ge=1, le=60)
    background: str | None = Field(None, max_length=10_000)
    focus_notes: str | None = Field(None, max_length=4000)
    question_types: list[QType] | None = Field(None, min_length=1)
    questions_per_area: int | None = Field(None, ge=1, le=20)
    question_bar: Literal["top_ai", "big_tech", "standard"] | None = None
    web_research: bool | None = None


@router.patch("/interviews/{prep_id}")
def update_prep(prep_id: int, body: PrepPatch, db: Session = Depends(get_db)):
    p = get_or_404(db, InterviewPrep, prep_id)
    for k, v in body.model_dump(exclude_none=True, exclude={"clear_date"}).items():
        setattr(p, k, v.strip() if isinstance(v, str) else v)
    if body.clear_date:
        p.interview_date = None
    if p.path_id and (path := db.get(LearningPath, p.path_id)):
        path.hours_per_week = p.hours_per_week
    db.commit()
    return config_out(p)


class RebuildIn(BaseModel):
    replace_plan: bool = True
    replace_questions: bool = False


@router.post("/interviews/{prep_id}/rebuild")
async def rebuild(prep_id: int, body: RebuildIn, db: Session = Depends(get_db)):
    get_or_404(db, InterviewPrep, prep_id)
    _busy(db, prep_id)
    run_id = runs.start_build(prep_id, replace_plan=body.replace_plan, replace_questions=body.replace_questions)
    spawn(runs.run_build(run_id, prep_id, replace_plan=body.replace_plan, replace_questions=body.replace_questions))
    return {"run_id": run_id}


@router.delete("/interviews/{prep_id}")
def delete_prep(prep_id: int, delete_plan: bool = True, db: Session = Depends(get_db)):
    p = get_or_404(db, InterviewPrep, prep_id)
    _busy(db, prep_id)
    if delete_plan and p.path_id and (path := db.get(LearningPath, p.path_id)):
        db.delete(path)
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/interviews/{prep_id}/coach")
async def coach(prep_id: int, db: Session = Depends(get_db)):
    get_or_404(db, InterviewPrep, prep_id)
    try:
        return {"text": await runs.refresh_coach_note(prep_id)}
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


# ---------------------------------------------------------------- skills

class SkillPatch(BaseModel):
    self_rating: int = Field(ge=0, le=5, description="0 clears the rating")


@router.patch("/interview-skills/{skill_id}")
def rate_skill(skill_id: int, body: SkillPatch, db: Session = Depends(get_db)):
    s = get_or_404(db, InterviewSkill, skill_id)
    s.self_rating = body.self_rating or None
    db.commit()
    return {"id": s.id, "self_rating": s.self_rating}


# ---------------------------------------------------------------- question bank

def _skill_names(db: Session, prep_id: int) -> dict[int, str]:
    return {s.id: s.name for s in db.scalars(select(InterviewSkill).where(InterviewSkill.prep_id == prep_id))}


@router.get("/interviews/{prep_id}/questions")
def list_questions(prep_id: int, area: str | None = None, qtype: QType | None = None,
                   difficulty: Difficulty | None = None, status: Status | None = None, q: str | None = None,
                   db: Session = Depends(get_db)):
    p = get_or_404(db, InterviewPrep, prep_id)
    names = _skill_names(db, prep_id)
    out = []
    for item in p.questions:
        if (area and item.area != area) or (qtype and item.qtype != qtype) or \
                (difficulty and item.difficulty != difficulty) or (status and item.status != status):
            continue
        if q and q.lower() not in (item.question + " " + (names.get(item.skill_id or -1) or "")).lower():
            continue
        out.append(question_out(item, names))
    return out


class GenerateIn(BaseModel):
    area: str | None = None
    qtype: QType | None = None
    difficulty: Difficulty | None = None
    count: int = Field(6, ge=1, le=30)


@router.post("/interviews/{prep_id}/questions/generate")
async def generate(prep_id: int, body: GenerateIn, db: Session = Depends(get_db)):
    p = get_or_404(db, InterviewPrep, prep_id)
    _busy(db, prep_id)
    if not p.skills:
        raise HTTPException(409, "Build the companion first: there are no skills to write questions about.")
    run_id = runs.start_generate(prep_id)
    spawn(runs.run_generate(run_id, prep_id, area=body.area, qtype=body.qtype, difficulty=body.difficulty,
                            count=body.count))
    return {"run_id": run_id}


class QuestionIn(BaseModel):
    question: str = Field(min_length=5, max_length=4000)
    area: str = Field("My questions", max_length=120)
    qtype: QType = "concept"
    difficulty: Difficulty = "hard"
    answer_md: str = Field("", max_length=20_000)
    key_points: list[str] = Field(default_factory=list, max_length=12)


@router.post("/interviews/{prep_id}/questions")
def add_question(prep_id: int, body: QuestionIn, db: Session = Depends(get_db)):
    get_or_404(db, InterviewPrep, prep_id)
    q = InterviewQuestion(prep_id=prep_id, source="user", **{**body.model_dump(), "question": body.question.strip(),
                                                              "area": body.area.strip() or "My questions"})
    db.add(q)
    db.commit()
    return question_out(q, _skill_names(db, prep_id))


class QuestionPatch(BaseModel):
    status: Status | None = None
    question: str | None = Field(None, min_length=5, max_length=4000)
    answer_md: str | None = Field(None, max_length=20_000)
    key_points: list[str] | None = Field(None, max_length=12)
    difficulty: Difficulty | None = None
    qtype: QType | None = None


@router.patch("/interview-questions/{qid}")
def update_question(qid: int, body: QuestionPatch, db: Session = Depends(get_db)):
    q = get_or_404(db, InterviewQuestion, qid)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(q, k, [x.strip() for x in v if x.strip()] if isinstance(v, list) else v)
    db.commit()
    return question_out(q, _skill_names(db, q.prep_id))


@router.delete("/interview-questions/{qid}")
def delete_question(qid: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, InterviewQuestion, qid))
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- mock interview

class NextIn(BaseModel):
    area: str | None = None
    qtype: QType | None = None
    exclude: list[int] = Field(default_factory=list, max_length=500)


STATUS_WEIGHT = {"needs_work": 3.0, "new": 2.0, "confident": 0.4}


@router.post("/interviews/{prep_id}/mock/next")
def next_question(prep_id: int, body: NextIn, db: Session = Depends(get_db)):
    """Pick the next mock question, favouring weak areas: 'needs work', low self-ratings, low last scores."""
    p = get_or_404(db, InterviewPrep, prep_id)
    ratings = {s.id: s.self_rating for s in p.skills}
    pool = [q for q in p.questions if (not body.area or q.area == body.area) and (not body.qtype or q.qtype == body.qtype)]
    fresh = [q for q in pool if q.id not in set(body.exclude)] or pool
    if not fresh:
        raise HTTPException(404, "No questions match. Generate some on the Questions tab first.")

    def weight(q: InterviewQuestion) -> float:
        w = STATUS_WEIGHT.get(q.status, 1.0)
        w *= 1 + (5 - (ratings.get(q.skill_id or -1) or 3)) / 4
        if q.attempts:
            w *= 1 + (5 - q.attempts[-1].score) / 4
        return w

    q = random.choices(fresh, weights=[weight(x) for x in fresh])[0]
    return question_out(q, _skill_names(db, prep_id), with_answer=False)


class AttemptIn(BaseModel):
    answer: str = Field(min_length=10, max_length=12_000)


@router.post("/interview-questions/{qid}/attempts")
async def submit_attempt(qid: int, body: AttemptIn, db: Session = Depends(get_db)):
    q = get_or_404(db, InterviewQuestion, qid)
    prep = db.get(InterviewPrep, q.prep_id)
    _ = list(q.key_points), prep.role_title  # load before the slow call
    try:
        grade = await MockInterviewer(get_llm()).grade(prep, q, body.answer)
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    a = PracticeAttempt(question_id=q.id, answer=body.answer, score=grade.score, verdict=grade.verdict,
                        strengths=grade.strengths, missing=grade.missing, better_answer_md=grade.better_answer_md,
                        follow_up=grade.follow_up)
    db.add(a)
    if grade.score >= 4:
        q.status = "confident"
    elif grade.score <= 2:
        q.status = "needs_work"
    db.commit()
    return {**attempt_out(a), "question": question_out(q, _skill_names(db, q.prep_id))}


@router.get("/interviews/{prep_id}/attempts")
def list_attempts(prep_id: int, limit: int = 30, db: Session = Depends(get_db)):
    get_or_404(db, InterviewPrep, prep_id)
    rows = db.execute(select(PracticeAttempt, InterviewQuestion)
                      .join(InterviewQuestion, InterviewQuestion.id == PracticeAttempt.question_id)
                      .where(InterviewQuestion.prep_id == prep_id)
                      .order_by(PracticeAttempt.id.desc()).limit(min(limit, 200))).all()
    return [{**attempt_out(a), "question_text": q.question, "area": q.area} for a, q in rows]
