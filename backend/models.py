"""SQLite tables. Single-user app: user id 1 is created on first start."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="Learner")
    email: Mapped[Optional[str]] = mapped_column(String(200))
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LearningRequirement(Base):
    __tablename__ = "learning_requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    raw_text: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(String(60), default="understand")
    level: Mapped[str] = mapped_column(String(30), default="intermediate")
    hours_per_week: Mapped[int] = mapped_column(default=5)
    weeks: Mapped[int] = mapped_column(default=6)
    formats: Mapped[list[str]] = mapped_column(JSON, default=list)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class TopicGraph(Base):
    __tablename__ = "topic_graphs"
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("learning_requirements.id", ondelete="CASCADE"))
    graph: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LearningPath(Base):
    __tablename__ = "paths"
    id: Mapped[int] = mapped_column(primary_key=True)
    requirement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_requirements.id", ondelete="SET NULL"))
    slug: Mapped[Optional[str]] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    level: Mapped[str] = mapped_column(String(30), default="intermediate")
    hours_per_week: Mapped[int] = mapped_column(default=5)
    weeks: Mapped[int] = mapped_column(default=6)
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="ready")  # building | ready | failed
    is_seed: Mapped[bool] = mapped_column(default=False)
    show_on_home: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(default=0)
    kind: Mapped[str] = mapped_column(String(20), default="learning")  # learning | interview
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="path", order_by="Module.idx", cascade="all, delete-orphan"
    )


class Module(Base):
    __tablename__ = "modules"
    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("paths.id", ondelete="CASCADE"))
    idx: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    paper_keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    resources_status: Mapped[str] = mapped_column(String(20), default="none")  # none | searching | ready | failed

    path: Mapped[LearningPath] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module", order_by="Lesson.idx", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id", ondelete="CASCADE"))
    idx: Mapped[int]
    title: Mapped[str] = mapped_column(String(200))
    objectives: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    est_minutes: Mapped[int] = mapped_column(default=20)
    content_md: Mapped[Optional[str]] = mapped_column(Text)
    notes_status: Mapped[str] = mapped_column(String(20), default="none")  # none | writing | ready | failed
    user_notes: Mapped[str] = mapped_column(Text, default="")

    module: Mapped[Module] = relationship(back_populates="lessons")


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("source", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))      # video | paper | course | article
    source: Mapped[str] = mapped_column(String(30))    # youtube | arxiv | semantic_scholar | ...
    external_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    author: Mapped[str] = mapped_column(String(500), default="")
    year: Mapped[Optional[int]]
    duration_min: Mapped[Optional[int]]
    summary: Mapped[str] = mapped_column(Text, default="")
    thumbnail: Mapped[Optional[str]] = mapped_column(String(1000))
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(default=utcnow)


class LessonResource(Base):
    __tablename__ = "lesson_resources"
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    rank: Mapped[int] = mapped_column(default=0)
    why: Mapped[str] = mapped_column(Text, default="")
    added_by: Mapped[str] = mapped_column(String(20), default="agent")  # agent | user | seed

    resource: Mapped[Resource] = relationship()


class Progress(Base):
    __tablename__ = "progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, default=1)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default="doing")  # doing | done
    minutes_spent: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    completed_at: Mapped[Optional[datetime]]


class SavedResource(Base):
    __tablename__ = "saved_resources"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, default=1)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
    saved_at: Mapped[datetime] = mapped_column(default=utcnow)

    resource: Mapped[Resource] = relationship()


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    lesson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    messages: Mapped[list["ChatMessage"]] = relationship(
        order_by="ChatMessage.id", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(10))  # user | assistant | error
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))  # build_path | find_resources | write_notes
    requirement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("learning_requirements.id", ondelete="SET NULL"))
    path_id: Mapped[Optional[int]] = mapped_column(ForeignKey("paths.id", ondelete="SET NULL"))
    interview_id: Mapped[Optional[int]] = mapped_column(ForeignKey("interview_preps.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running | done | failed
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    finished_at: Mapped[Optional[datetime]]

    steps: Mapped[list["AgentStep"]] = relationship(order_by="AgentStep.id", cascade="all, delete-orphan")


class AgentStep(Base):
    __tablename__ = "agent_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"))
    agent: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued | running | done | failed | skipped
    summary: Mapped[str] = mapped_column(Text, default="")
    chips: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[Optional[datetime]]
    finished_at: Mapped[Optional[datetime]]


class Bookmark(Base):
    """A course or link the user added themselves (e.g. a Udemy course they bought, docs, a blog post)."""

    __tablename__ = "bookmarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    kind: Mapped[str] = mapped_column(String(20), default="link")  # course | link | video | paper | doc
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(2000))
    provider: Mapped[str] = mapped_column(String(40), default="web")
    note: Mapped[str] = mapped_column(Text, default="")
    path_id: Mapped[Optional[int]] = mapped_column(ForeignKey("paths.id", ondelete="SET NULL"))
    show_on_home: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(20), default="todo")  # todo | doing | done
    position: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class CacheEntry(Base):
    """Search-result cache (paper and video searches)."""

    __tablename__ = "cache"
    key: Mapped[str] = mapped_column(String(500), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(default=utcnow)


class FocusNote(Base):
    """Home page 'today's focus' note, cached per lesson."""

    __tablename__ = "focus_notes"
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# ---------------------------------------------------------------- interview companion

class InterviewPrep(Base):
    """One interview companion: the role you're preparing for and everything the agents built for it."""

    __tablename__ = "interview_preps"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), default=1)
    role_title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(200), default="")
    jd_text: Mapped[str] = mapped_column(Text, default="")
    seniority: Mapped[str] = mapped_column(String(30), default="senior")  # senior | staff | principal | lead
    interview_date: Mapped[Optional[date]]
    hours_per_week: Mapped[int] = mapped_column(default=8)
    background: Mapped[str] = mapped_column(Text, default="")
    focus_notes: Mapped[str] = mapped_column(Text, default="")
    question_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    questions_per_area: Mapped[int] = mapped_column(default=6)
    question_bar: Mapped[str] = mapped_column(String(20), default="top_ai")  # top_ai | big_tech | standard
    web_research: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(20), default="building")  # building | ready | failed
    path_id: Mapped[Optional[int]] = mapped_column(ForeignKey("paths.id", ondelete="SET NULL"))
    jd_analysis: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    research: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    coach_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    skills: Mapped[list["InterviewSkill"]] = relationship(
        order_by="InterviewSkill.idx", cascade="all, delete-orphan")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        order_by="InterviewQuestion.id", cascade="all, delete-orphan")


class InterviewSkill(Base):
    __tablename__ = "interview_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    prep_id: Mapped[int] = mapped_column(ForeignKey("interview_preps.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(default=0)
    area: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(200))
    importance: Mapped[str] = mapped_column(String(20), default="important")  # must | important | nice
    evidence: Mapped[str] = mapped_column(Text, default="")
    in_jd: Mapped[bool] = mapped_column(default=False)
    how_tested: Mapped[str] = mapped_column(Text, default="")
    self_rating: Mapped[Optional[int]]


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    prep_id: Mapped[int] = mapped_column(ForeignKey("interview_preps.id", ondelete="CASCADE"))
    skill_id: Mapped[Optional[int]] = mapped_column(ForeignKey("interview_skills.id", ondelete="SET NULL"))
    area: Mapped[str] = mapped_column(String(120), default="")
    qtype: Mapped[str] = mapped_column(String(20), default="concept")  # concept | design | scenario | hands_on | behavioral
    difficulty: Mapped[str] = mapped_column(String(20), default="hard")  # medium | hard | expert
    question: Mapped[str] = mapped_column(Text)
    answer_md: Mapped[str] = mapped_column(Text, default="")
    key_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    follow_ups: Mapped[list[str]] = mapped_column(JSON, default=list)
    red_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    references: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="new")  # new | needs_work | confident
    source: Mapped[str] = mapped_column(String(20), default="agent")  # agent | user
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    attempts: Mapped[list["PracticeAttempt"]] = relationship(
        order_by="PracticeAttempt.id", cascade="all, delete-orphan")


class PracticeAttempt(Base):
    __tablename__ = "practice_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"))
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(default=0)
    verdict: Mapped[str] = mapped_column(Text, default="")
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing: Mapped[list[str]] = mapped_column(JSON, default=list)
    better_answer_md: Mapped[str] = mapped_column(Text, default="")
    follow_up: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
