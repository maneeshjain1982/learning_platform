"""Companion Orchestrator: runs the sub-agents in order and stores their results."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from ..db import session_scope
from ..llm import LLMClient, get_llm
from ..models import FocusNote, LearningPath, LearningRequirement, Lesson, Module, TopicGraph
from .base import StepRecorder, attach, upsert_resource
from .planning import CurriculumPlanner, TopicIdentifier
from .search import Curator, PaperSearchAgent, VideoSearchAgent
from .tutor import HomeComposer, LessonWriter

log = logging.getLogger("study.orchestrator")

BUILD_STEPS = ["topic", "curriculum", "videos", "papers", "curator", "home"]
RESOURCE_STEPS = ["videos", "papers", "curator", "home"]
PAPER_SOURCES = {"arxiv", "semantic_scholar"}


def start_build(requirement_id: int) -> int:
    return StepRecorder.create_run("build_path", BUILD_STEPS, requirement_id=requirement_id).run_id


def start_find_resources(path_id: int) -> int:
    return StepRecorder.create_run("find_resources", RESOURCE_STEPS, path_id=path_id).run_id


async def run_build(run_id: int, requirement_id: int, llm: LLMClient | None = None) -> None:
    llm = llm or get_llm()
    rec = StepRecorder(run_id)
    try:
        with session_scope() as db:
            req = db.get(LearningRequirement, requirement_id)
            req.status = "building"

        # 1. Topic Identifier
        rec.start("topic", "Reading your goal…")
        topics = await TopicIdentifier(llm).run(req)
        with session_scope() as db:
            db.add(TopicGraph(requirement_id=requirement_id, graph=topics.model_dump()))
        rec.done("topic", f"Found {len(topics.core_topics)} core topics.", [t.name for t in topics.core_topics])

        # 2. Curriculum Planner
        rec.start("curriculum", f"Ordering modules for ~{req.hours_per_week} h/week over {req.weeks} weeks…")
        plan = await CurriculumPlanner(llm).run(req, topics)
        with session_scope() as db:
            path = LearningPath(
                requirement_id=requirement_id, user_id=req.user_id, title=topics.title, summary=topics.summary, level=req.level,
                hours_per_week=req.hours_per_week, weeks=req.weeks, sources=req.sources, status="building",
            )
            for mi, m in enumerate(plan.modules):
                mod = Module(idx=mi, title=m.title, summary=m.summary, objectives=m.objectives,
                             keywords=m.keywords, paper_keywords=m.paper_keywords)
                mod.lessons = [Lesson(idx=li, title=l.title, objectives=l.objectives, keywords=l.keywords,
                                      est_minutes=max(5, min(90, l.est_minutes))) for li, l in enumerate(m.lessons)]
                path.modules.append(mod)
            db.add(path)
            db.flush()
            path_id = path.id
        rec.set_path(path_id)
        n_lessons = sum(len(m.lessons) for m in plan.modules)
        rec.done("curriculum", f"{len(plan.modules)} modules, {n_lessons} lessons.",
                 [f"{i + 1}. {m.title}" for i, m in enumerate(plan.modules)])

        # 3-6. Resources + home
        await _find_resources(rec, path_id, llm)

        with session_scope() as db:
            db.get(LearningPath, path_id).status = "ready"
            db.get(LearningRequirement, requirement_id).status = "done"
        rec.finish()
    except Exception as exc:
        log.exception("Build run %s failed", run_id)
        with session_scope() as db:
            req = db.get(LearningRequirement, requirement_id)
            if req:
                req.status = "failed"
            for p in db.scalars(select(LearningPath).where(LearningPath.requirement_id == requirement_id)):
                p.status = "ready" if p.modules else "failed"
        _fail_running(rec, str(exc))
        rec.finish(str(exc))


async def run_find_resources(run_id: int, path_id: int, llm: LLMClient | None = None,
                             module_ids: list[int] | None = None) -> None:
    llm = llm or get_llm()
    rec = StepRecorder(run_id)
    try:
        await _find_resources(rec, path_id, llm, module_ids)
        rec.finish()
    except Exception as exc:
        log.exception("Resource run %s failed", run_id)
        _fail_running(rec, str(exc))
        rec.finish(str(exc))


def _fail_running(rec: StepRecorder, error: str) -> None:
    from ..models import AgentRun

    with session_scope() as db:
        for s in db.get(AgentRun, rec.run_id).steps:
            if s.status == "running":
                s.status, s.summary = "failed", error[:500]


async def _find_resources(rec: StepRecorder, path_id: int, llm: LLMClient,
                          module_ids: list[int] | None = None) -> None:
    with session_scope() as db:
        path = db.get(LearningPath, path_id)
        mods = [m for m in path.modules if not module_ids or m.id in module_ids]
        for m in mods:
            m.resources_status = "searching"
            _ = list(m.lessons)  # load before the session closes
        path_title, level, sources = path.title, path.level, set(path.sources or [])

    want_videos = not sources or "youtube" in sources
    want_papers = not sources or bool(sources & PAPER_SOURCES)

    video_agent, paper_agent, curator = VideoSearchAgent(llm), PaperSearchAgent(llm), Curator(llm)
    video_counts: dict[int, int] = {}
    papers_by_module: dict[int, list] = {}
    errors: list[str] = []

    async def videos_for(m: Module):
        try:
            found = await video_agent.for_module(path_title=path_title, level=level, module=m, lessons=m.lessons)
        except Exception as exc:
            errors.append(f"Videos for '{m.title}': {exc}")
            return
        with session_scope() as db:
            for rank, (li, cand, why) in enumerate(found):
                res = upsert_resource(db, cand)
                attach(db, m.lessons[li].id, res.id, rank=rank, why=why)
        video_counts[m.id] = len(found)
        rec.update("videos", f"Searched {len(video_counts)} of {len(mods)} modules.",
                   [f"{mm.title}: {video_counts[mm.id]}" for mm in mods if mm.id in video_counts])

    async def videos_all():
        if not want_videos:
            rec.done("videos", "YouTube is not among your sources.", status="skipped")
            return
        rec.start("videos", "Searching YouTube and checking every link…")
        await asyncio.gather(*(videos_for(m) for m in mods))
        total = sum(video_counts.values())
        rec.done("videos", f"{total} verified videos across {len(video_counts)} modules.",
                 [f"{m.title}: {video_counts.get(m.id, 0)}" for m in mods])

    async def papers_all():
        if not want_papers:
            rec.done("papers", "Paper sources are turned off.", status="skipped")
            return
        rec.start("papers", "Searching arXiv and Semantic Scholar…")
        for m in mods:
            papers_by_module[m.id] = await paper_agent.for_module(m, m.lessons)
            rec.update("papers", f"Searched {len(papers_by_module)} of {len(mods)} modules.")
        total = sum(len(v) for v in papers_by_module.values())
        rec.done("papers", f"{total} candidate papers found.",
                 [f"{m.title}: {len(papers_by_module.get(m.id, []))}" for m in mods])

    await asyncio.gather(videos_all(), papers_all())

    # Curator: match papers to lessons
    rec.start("curator", "Matching papers to lessons…")
    kept = 0
    for m in mods:
        papers = papers_by_module.get(m.id, [])
        picks = await curator.assign_papers(level=level, module=m, lessons=m.lessons, papers=papers)
        with session_scope() as db:
            for rank, (li, pi, why) in enumerate(picks):
                res = upsert_resource(db, papers[pi])
                attach(db, m.lessons[li].id, res.id, rank=10 + rank, why=why)
        kept += len(picks)
    with session_scope() as db:
        for m in mods:
            db.get(Module, m.id).resources_status = "ready"
    rec.done("curator", f"Kept {kept} papers; videos were matched per lesson by Video Search.")

    # Home Composer: clear cached focus notes so the home page is rebuilt
    rec.start("home", "Updating your home page…")
    with session_scope() as db:
        lesson_ids = [l.id for m in mods for l in m.lessons]
        for note in db.scalars(select(FocusNote).where(FocusNote.lesson_id.in_(lesson_ids))):
            db.delete(note)
    rec.done("home", "Home page updated." + (f" {len(errors)} module searches failed." if errors else ""))
    if errors and not video_counts and want_videos:
        raise RuntimeError("; ".join(errors)[:800])


async def write_lesson_notes(lesson_id: int, llm: LLMClient | None = None) -> None:
    llm = llm or get_llm()
    with session_scope() as db:
        lesson = db.get(Lesson, lesson_id)
        module = lesson.module
        path = module.path
        siblings = module.lessons
        i = siblings.index(lesson)
        prev_t = siblings[i - 1].title if i > 0 else None
        next_t = siblings[i + 1].title if i + 1 < len(siblings) else None
        from ..models import LessonResource
        resources = [lr.resource.title for lr in db.scalars(
            select(LessonResource).where(LessonResource.lesson_id == lesson_id))]
        args = dict(path_title=path.title, level=path.level, module_title=module.title, lesson=lesson,
                    prev_title=prev_t, next_title=next_t, resources=resources)
        lesson.notes_status = "writing"
    try:
        md = await LessonWriter(llm).run(**args)
        with session_scope() as db:
            l = db.get(Lesson, lesson_id)
            l.content_md, l.notes_status = md, "ready"
    except Exception as exc:
        log.exception("Lesson notes failed for %s", lesson_id)
        with session_scope() as db:
            db.get(Lesson, lesson_id).notes_status = "failed"
        raise exc


async def compose_focus_note(lesson_id: int, llm: LLMClient | None = None) -> str:
    llm = llm or get_llm()
    with session_scope() as db:
        cached = db.get(FocusNote, lesson_id)
        if cached:
            return cached.text
        lesson = db.get(Lesson, lesson_id)
        path = lesson.module.path
        from ..models import Progress
        all_ids = [l.id for m in path.modules for l in m.lessons]
        done = db.scalars(select(Progress).where(Progress.lesson_id.in_(all_ids), Progress.status == "done")).all()
        args = dict(path_title=path.title, module_title=lesson.module.title, lesson_title=lesson.title,
                    done_count=len(done), total=len(all_ids), hours_per_week=path.hours_per_week)
    text = await HomeComposer(llm).focus_note(**args)
    with session_scope() as db:
        if not db.get(FocusNote, lesson_id):
            db.add(FocusNote(lesson_id=lesson_id, text=text))
    return text
