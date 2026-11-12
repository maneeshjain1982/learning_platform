"""Typed outputs each agent asks the LLM for (sent to the bridge as JSON Schema)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CoreTopic(BaseModel):
    name: str
    description: str
    prerequisites: list[str] = Field(default_factory=list)


class TopicGraphOut(BaseModel):
    title: str = Field(description="Short name for the learning path, 2-5 words")
    summary: str = Field(description="One or two sentences describing what the learner will be able to do")
    core_topics: list[CoreTopic] = Field(description="5-8 core topics in a sensible learning order")
    prerequisites: list[str] = Field(default_factory=list, description="Things the learner should already know")
    out_of_scope: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(description="6-10 short search phrases for videos and papers")


class LessonPlan(BaseModel):
    title: str
    objectives: list[str] = Field(description="2-3 'you can ...' learning objectives")
    keywords: list[str] = Field(description="2-4 short search phrases specific to this lesson")
    est_minutes: int = Field(description="Estimated study time, 10-45")


class ModulePlan(BaseModel):
    title: str
    summary: str
    objectives: list[str]
    keywords: list[str] = Field(description="2-4 search phrases for videos/courses on this module")
    paper_keywords: list[str] = Field(description="1-2 short academic search phrases for papers")
    lessons: list[LessonPlan] = Field(description="3-5 lessons in order")


class CurriculumOut(BaseModel):
    modules: list[ModulePlan] = Field(description="4-7 modules in order, simple to advanced")


class VideoPick(BaseModel):
    lesson_index: int = Field(description="0-based index of the lesson this video fits")
    url: str = Field(description="Full YouTube watch URL seen in search results")
    title: str
    channel: str = ""
    why: str = Field(description="One short sentence: why this video fits this lesson")


class VideoPicksOut(BaseModel):
    videos: list[VideoPick]


class PaperAssignment(BaseModel):
    paper_index: int
    lesson_index: int
    why: str = Field(description="One short sentence: why this paper helps with this lesson")


class CuratorOut(BaseModel):
    assignments: list[PaperAssignment]


class KnownPaper(BaseModel):
    arxiv_id: str = Field(description="arXiv identifier like 2210.03629 (no version suffix)")
    title: str = Field(description="Exact paper title")


class KnownPapersOut(BaseModel):
    papers: list[KnownPaper]


class VideoResult(BaseModel):
    url: str
    title: str
    channel: str = ""
    why: str = ""


class VideoSearchOut(BaseModel):
    videos: list[VideoResult]


# ---------------------------------------------------------------- interview companion

from typing import Literal  # noqa: E402

QType = Literal["concept", "design", "scenario", "hands_on", "behavioral"]


class SourceLink(BaseModel):
    title: str
    url: str = Field(description="Full https URL of a page you actually found")


class JDAnalysisOut(BaseModel):
    role_summary: str = Field(description="2-3 sentences: what this person will own and deliver")
    responsibilities: list[str] = Field(description="5-10 key responsibilities")
    required_skills: list[str] = Field(description="Skills and technologies the JD requires")
    nice_to_have: list[str] = Field(default_factory=list)
    seniority_signals: list[str] = Field(default_factory=list, description="What signals the expected level")
    likely_rounds: list[str] = Field(default_factory=list, description="Interview rounds this JD implies")


class SkillFrequency(BaseModel):
    name: str
    note: str = Field(description="How often / in what form it appears in postings, e.g. 'most postings'")


class RoleResearchOut(BaseModel):
    role_summary: str = Field(description="What companies mean by this role today, 2-4 sentences")
    responsibilities: list[str] = Field(description="Responsibilities commonly listed for the role")
    common_skills: list[SkillFrequency] = Field(description="10-25 skills and technologies seen across postings")
    interview_format: list[str] = Field(description="Typical interview rounds and what each one tests")
    trends: list[str] = Field(description="3-6 current trends interviewers expect candidates to know")
    sources: list[SourceLink] = Field(description="5-12 pages you used: postings, interview guides, docs, blogs")


class MappedSkill(BaseModel):
    area: str = Field(description="Competency area name, reused exactly across skills in the same area")
    name: str = Field(description="Skill or technology, short (e.g. 'Model Context Protocol (MCP)')")
    importance: Literal["must", "important", "nice"]
    evidence: str = Field(description="One sentence: why it matters for this role (cite JD or research)")
    in_jd: bool = Field(description="True only if the job description explicitly asks for it")
    how_tested: str = Field(description="One sentence: how interviewers usually test this")


class SkillMapOut(BaseModel):
    skills: list[MappedSkill] = Field(description="30-60 skills grouped into 8-12 areas, most important first")


class PrepPlanOut(BaseModel):
    title: str = Field(description="Short name for the prep plan")
    summary: str = Field(description="One or two sentences")
    modules: list[ModulePlan] = Field(description="5-9 modules in study order")


class Reference(BaseModel):
    title: str = Field(description="Exact title of the paper, doc page, spec or blog post")
    url: str = Field(description="Its canonical URL (arXiv abs page for papers)")
    arxiv_id: str = Field("", description="arXiv id like 2210.03629 when it is an arXiv paper, else empty")


class WrittenQuestion(BaseModel):
    skill_name: str = Field(description="Exact name of the skill this question tests, from the list given")
    qtype: QType
    difficulty: Literal["medium", "hard", "expert"]
    question: str
    answer_md: str = Field(description="Model answer in Markdown: structured, specific, with trade-offs")
    key_points: list[str] = Field(description="4-7 points a strong answer must cover (used for grading)")
    follow_ups: list[str] = Field(description="2-3 probing follow-up questions")
    red_flags: list[str] = Field(description="1-3 answers or habits that sink candidates")
    references: list[Reference] = Field(description="1-4 sources backing the answer: papers, official docs, specs")


class QuestionBatchOut(BaseModel):
    questions: list[WrittenQuestion]


class MockGradeOut(BaseModel):
    score: int = Field(description="1 = would fail, 2 = weak, 3 = acceptable, 4 = strong, 5 = exceptional for the bar")
    verdict: str = Field(description="One or two sentences, direct, as an interviewer's debrief")
    strengths: list[str]
    missing: list[str] = Field(description="Key points missed or got wrong")
    better_answer_md: str = Field(description="A tighter, stronger version of the candidate's answer in Markdown")
    follow_up: str = Field(description="The follow-up question an interviewer would ask next")
