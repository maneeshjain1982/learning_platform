"""Interview companion pipeline: runs the interview agents in order and stores what they produce."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import date

from sqlalchemy import select

from ..db import session_scope
from ..llm import LLMClient, get_llm
from ..models import (InterviewPrep, InterviewQuestion, InterviewSkill, LearningPath, Lesson, Module, PracticeAttempt,
                      Progress)
from .base import StepRecorder
from .interview import (Coach, JDAnalyst, PrepPlanner, QuestionWriter, RoleResearcher, SkillMapper, group_by_area,
                        verify_references, verify_sources)
from .orchestrator import _fail_running, _find_resources

log = logging.getLogger("study.interview")

ALL_QTYPES = ["concept", "design", "scenario", "hands_on", "behavioral"]
RESOURCE_STEPS = ["videos", "papers", "curator", "home"]
LEVEL = {"senior": "advanced", "staff": "advanced", "principal": "advanced", "lead": "advanced"}


def build_steps(replace_plan: bool, replace_questions: bool) -> list[str]:
    steps = ["jd", "research", "skills"]
    if replace_plan:
        steps += ["plan", *RESOURCE_STEPS]
    if replace_questions:
        steps.append("questions")
    return steps + ["coach"]


def start_build(prep_id: int, *, replace_plan: bool = True, replace_questions: bool = True) -> int:
    return StepRecorder.create_run("interview_build", build_steps(replace_plan, replace_questions),
                                   interview_id=prep_id).run_id


def start_generate(prep_id: int) -> int:
    return StepRecorder.create_run("interview_questions", ["questions"], interview_id=prep_id).run_id


def days_left(prep) -> int | None:
    return (prep.interview_date - date.today()).days if prep.interview_date else None


def plan_weeks(prep) -> int:
    d = days_left(prep)
    return 4 if d is None else max(1, min(12, math.ceil(max(d, 1) / 7)))


class _Snap:
    """Plain copy of a skill row, safe to use after its DB session closes."""

    def __init__(self, s: InterviewSkill):
        self.id, self.area, self.name, self.importance = s.id, s.area, s.name, s.importance
        self.how_tested, self.self_rating = s.how_tested, s.self_rating


def _skills(prep_id: int) -> list[_Snap]:
    with session_scope() as db:
        return [_Snap(s) for s in db.scalars(select(InterviewSkill).where(InterviewSkill.prep_id == prep_id)
                                             .order_by(InterviewSkill.idx))]


# ---------------------------------------------------------------- full build

async def run_build(run_id: int, prep_id: int, llm: LLMClient | None = None, *, replace_plan: bool = True,
                    replace_questions: bool = True) -> None:
    llm = llm or get_llm()
    rec = StepRecorder(run_id)
    try:
        with session_scope() as db:
            prep = db.get(InterviewPrep, prep_id)
            prep.status = "building"

        # 1. JD Analyst
        jd = None
        if prep.jd_text.strip():
            rec.start("jd", "Reading the job description…")
            jd = (await JDAnalyst(llm).run(prep)).model_dump()
            rec.done("jd", f"{len(jd['required_skills'])} required skills, {len(jd['responsibilities'])} "
                           "responsibilities.", jd["required_skills"])
        else:
            rec.done("jd", "No job description given; using role research.", status="skipped")
        with session_scope() as db:
            db.get(InterviewPrep, prep_id).jd_analysis = jd or {}

        # 2. Role Researcher (web)
        research = None
        rec.start("research", "Searching job postings and interview reports…" if prep.web_research
                  else "Summarising what the role needs (web search is off)…")
        try:
            out = await RoleResearcher(llm).run(prep, web=prep.web_research)
            research = out.model_dump()
            rec.update("research", f"Checking {len(research['sources'])} source links…")
            research["sources"] = await verify_sources(research["sources"])
            rec.done("research", f"{len(research['common_skills'])} common skills; "
                                 f"{len(research['sources'])} sources kept after link checks.",
                     [s["name"] for s in research["common_skills"]])
        except Exception as exc:  # research is helpful but not essential
            log.warning("Role research failed: %s", exc)
            rec.fail("research", f"Research failed ({exc}); continuing with the job description and model knowledge.")
        with session_scope() as db:
            db.get(InterviewPrep, prep_id).research = research or {}

        # 3. Skill Mapper (keeps your self-ratings for skills with the same name)
        rec.start("skills", "Building the skill and technology map…")
        smap = await SkillMapper(llm).run(prep, jd, research)
        with session_scope() as db:
            old = {s.name.lower(): s.self_rating
                   for s in db.scalars(select(InterviewSkill).where(InterviewSkill.prep_id == prep_id))}
            for s in db.scalars(select(InterviewSkill).where(InterviewSkill.prep_id == prep_id)):
                db.delete(s)  # questions keep working: their skill_id is set to NULL, area stays
            db.flush()
            for i, s in enumerate(smap.skills):
                db.add(InterviewSkill(prep_id=prep_id, idx=i, area=s.area.strip(), name=s.name.strip(),
                                      importance=s.importance, evidence=s.evidence, in_jd=s.in_jd,
                                      how_tested=s.how_tested, self_rating=old.get(s.name.strip().lower())))
        skills = _skills(prep_id)
        areas = group_by_area(skills)
        rec.done("skills", f"{len(skills)} skills in {len(areas)} areas "
                           f"({sum(s.importance == 'must' for s in skills)} must-have).", list(areas))

        # 4. Prep Planner + resources, while the Question Writer works in parallel
        tasks = []
        if replace_plan:
            rec.start("plan", "Designing the preparation course…")
            weeks = plan_weeks(prep)
            plan = await PrepPlanner(llm).run(prep, skills, weeks=weeks)
            with session_scope() as db:
                p = db.get(InterviewPrep, prep_id)
                if p.path_id and (old_path := db.get(LearningPath, p.path_id)):
                    db.delete(old_path)
                path = LearningPath(user_id=p.user_id, title=f"Upskill Prep: {prep.role_title}", summary=plan.summary,
                                    level=LEVEL.get(prep.seniority, "advanced"), hours_per_week=prep.hours_per_week,
                                    weeks=weeks, sources=["youtube", "coursera", "udemy", "arxiv"], status="building",
                                    kind="interview")
                for mi, m in enumerate(plan.modules):
                    mod = Module(idx=mi, title=m.title, summary=m.summary, objectives=m.objectives,
                                 keywords=m.keywords, paper_keywords=m.paper_keywords)
                    mod.lessons = [Lesson(idx=li, title=l.title, objectives=l.objectives, keywords=l.keywords,
                                          est_minutes=max(5, min(90, l.est_minutes)))
                                   for li, l in enumerate(m.lessons)]
                    path.modules.append(mod)
                db.add(path)
                db.flush()
                p.path_id = path_id = path.id
            rec.set_path(path_id)
            rec.done("plan", f"{len(plan.modules)} modules over {weeks} week(s).",
                     [f"{i + 1}. {m.title}" for i, m in enumerate(plan.modules)])

            async def resources():
                await _find_resources(rec, path_id, llm)
                with session_scope() as db:
                    db.get(LearningPath, path_id).status = "ready"
            tasks.append(resources())

        if replace_questions:
            with session_scope() as db:  # replace agent questions you haven't practised; keep your own
                for q in db.scalars(select(InterviewQuestion).where(InterviewQuestion.prep_id == prep_id,
                                                                    InterviewQuestion.source == "agent")):
                    if not q.attempts:
                        db.delete(q)
            tasks.append(write_questions(rec, prep_id, llm, count_per_area=prep.questions_per_area,
                                         qtypes=prep.question_types or ALL_QTYPES))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [str(r) for r in results if isinstance(r, Exception)]

        # 7. Coach
        rec.start("coach", "Writing today's plan…")
        try:
            await refresh_coach_note(prep_id, llm)
            rec.done("coach", "Today's plan is on the Overview tab.")
        except Exception as exc:
            rec.fail("coach", str(exc))

        with session_scope() as db:
            db.get(InterviewPrep, prep_id).status = "ready"
        rec.finish("; ".join(errors)[:800] if errors else None)
    except Exception as exc:
        log.exception("Interview build %s failed", run_id)
        with session_scope() as db:
            p = db.get(InterviewPrep, prep_id)
            if p:
                p.status = "ready" if p.skills else "failed"
        _fail_running(rec, str(exc))
        rec.finish(str(exc))


# ---------------------------------------------------------------- Question Writer

async def write_questions(rec: StepRecorder, prep_id: int, llm: LLMClient, *, count_per_area: int,
                          qtypes: list[str], areas: list[str] | None = None, difficulty: str | None = None,
                          total: int | None = None) -> int:
    with session_scope() as db:
        prep = db.get(InterviewPrep, prep_id)
        existing = [(q.area, q.question) for q in prep.questions]
    skills = _skills(prep_id)
    by_area = group_by_area(skills)
    if not by_area:
        raise RuntimeError("There are no skills yet, so there is nothing to write questions about.")
    chosen = [a for a in (areas or by_area) if a in by_area]
    if total is not None and not areas:  # "generate N more" across areas: favour areas with fewest questions
        counts = {a: sum(1 for qa, _ in existing if qa == a) for a in by_area}
        chosen = sorted(by_area, key=lambda a: counts[a])[:max(1, min(len(by_area), total))]
        count_per_area = math.ceil(total / len(chosen))
    elif total is not None:
        count_per_area = total

    rec.start("questions", f"Writing {count_per_area} questions for each of {len(chosen)} areas…")
    writer = QuestionWriter(llm)
    done: dict[str, int] = {}
    failures: list[str] = []

    async def one(area: str):
        try:
            qs = await writer.for_area(prep, area, by_area[area], count=count_per_area, qtypes=qtypes,
                                       difficulty=difficulty, avoid=[q for a, q in existing if a == area])
            refs = await verify_references(qs)
        except Exception as exc:
            log.warning("Questions for %s failed: %s", area, exc)
            failures.append(area)
            return
        names = {s.name.lower(): s.id for s in by_area[area]}
        with session_scope() as db:
            for q, r in zip(qs, refs):
                db.add(InterviewQuestion(
                    prep_id=prep_id, skill_id=names.get(q.skill_name.strip().lower(), by_area[area][0].id),
                    area=area, qtype=q.qtype, difficulty=q.difficulty, question=q.question.strip(),
                    answer_md=q.answer_md, key_points=q.key_points, follow_ups=q.follow_ups, red_flags=q.red_flags,
                    references=r, source="agent"))
        done[area] = len(qs)
        rec.update("questions", f"Finished {len(done)} of {len(chosen)} areas.",
                   [f"{a}: {n}" for a, n in done.items()])

    await asyncio.gather(*(one(a) for a in chosen))
    total_written = sum(done.values())
    if not done:
        rec.fail("questions", f"Question writing failed for every area ({', '.join(failures)}).")
        raise RuntimeError("Question writing failed.")
    rec.done("questions", f"{total_written} questions with checked references"
             + (f"; {len(failures)} areas failed." if failures else "."), [f"{a}: {n}" for a, n in done.items()])
    return total_written


async def run_generate(run_id: int, prep_id: int, llm: LLMClient | None = None, *, area: str | None, qtype: str | None,
                       difficulty: str | None, count: int) -> None:
    llm = llm or get_llm()
    rec = StepRecorder(run_id)
    try:
        with session_scope() as db:
            prep = db.get(InterviewPrep, prep_id)
            qtypes = [qtype] if qtype else (prep.question_types or ALL_QTYPES)
        await write_questions(rec, prep_id, llm, count_per_area=count, qtypes=qtypes,
                              areas=[area] if area else None, difficulty=difficulty, total=count)
        rec.finish()
    except Exception as exc:
        log.exception("Question generation %s failed", run_id)
        _fail_running(rec, str(exc))
        rec.finish(str(exc))


# ---------------------------------------------------------------- stats + coach

def stats(db, prep: InterviewPrep) -> dict:
    skills = prep.skills
    weights = {"must": 2, "important": 1}
    rated = [(weights[s.importance], (s.self_rating or 0) / 5) for s in skills if s.importance in weights]
    skill_part = sum(w * r for w, r in rated) / sum(w for w, _ in rated) if rated else 0.0

    area_scores: dict[str, list[int]] = {a: [] for a in dict.fromkeys(s.area for s in skills)}
    attempts = 0
    for q in prep.questions:
        if q.attempts:
            attempts += len(q.attempts)
            area_scores.setdefault(q.area, []).append(q.attempts[-1].score)
    practice_part = (sum((sum(v) / len(v)) / 5 if v else 0 for v in area_scores.values()) / len(area_scores)
                     if area_scores else 0.0)

    plan_part, next_lesson = 0.0, None
    path = db.get(LearningPath, prep.path_id) if prep.path_id else None
    if path:
        lessons = [l for m in path.modules for l in m.lessons]
        done_ids = set(db.scalars(select(Progress.lesson_id).where(
            Progress.lesson_id.in_([l.id for l in lessons]), Progress.status == "done")))
        plan_part = len(done_ids) / len(lessons) if lessons else 0.0
        nxt = next((l for l in lessons if l.id not in done_ids), None)
        next_lesson = {"id": nxt.id, "title": nxt.title} if nxt else None

    status_counts = {"new": 0, "needs_work": 0, "confident": 0}
    for q in prep.questions:
        status_counts[q.status] = status_counts.get(q.status, 0) + 1
    weak = sorted((s for s in skills if s.importance == "must"), key=lambda s: (s.self_rating or 0))[:4]
    return {
        "readiness": round(100 * (0.5 * skill_part + 0.3 * practice_part + 0.2 * plan_part)),
        "parts": {"skills": round(100 * skill_part), "practice": round(100 * practice_part),
                  "plan": round(100 * plan_part)},
        "days_left": days_left(prep),
        "questions": len(prep.questions), "question_status": status_counts, "attempts": attempts,
        "area_scores": {a: round(sum(v) / len(v), 1) if v else None for a, v in area_scores.items()},
        "rated_skills": sum(1 for s in skills if s.self_rating), "skills": len(skills),
        "weak_skills": [s.name for s in weak if (s.self_rating or 0) <= 3],
        "next_lesson": next_lesson,
    }


async def refresh_coach_note(prep_id: int, llm: LLMClient | None = None) -> str:
    llm = llm or get_llm()
    with session_scope() as db:
        prep = db.get(InterviewPrep, prep_id)
        st = stats(db, prep)
    text = await Coach(llm).today(prep, days_left=st["days_left"], readiness=st["readiness"],
                                  weak_skills=st["weak_skills"], needs_work=st["question_status"]["needs_work"],
                                  next_lesson=st["next_lesson"]["title"] if st["next_lesson"] else None)
    with session_scope() as db:
        db.get(InterviewPrep, prep_id).coach_note = text
    return text


def latest_attempt(q: InterviewQuestion) -> PracticeAttempt | None:
    return q.attempts[-1] if q.attempts else None
