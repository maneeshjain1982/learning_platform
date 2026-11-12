"""Review Q&A writer: questions and answers for each lesson of a Claude Academy course or Hindi Voice module.

The course videos sit behind a sign-in, so answers are grounded in Anthropic's public documentation (found with
web search). Every reference link is checked; dead ones are dropped.
"""

from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from .interview import verify_sources
from .schemas import SourceLink

log = logging.getLogger("study.review")
LESSONS_PER_CALL = 10


class QAItem(BaseModel):
    lesson_index: int = Field(description="Index of the lesson in the numbered list you were given")
    question: str = Field(description="A review question that checks understanding, not trivia")
    answer_md: str = Field(description="Model answer in markdown, 60-180 words, concrete and correct")
    key_points: list[str] = Field(description="2-4 points a good answer must contain")
    references: list[SourceLink] = Field(description="1-2 pages backing the answer: official docs, papers, specs, repos")


class QABatchOut(BaseModel):
    items: list[QAItem]


SYSTEM = (
    "You write review questions for an engineer working through Anthropic's Claude Academy courses, aiming to "
    "become an Agentic AI Architect. Use web search to check facts against current official sources: "
    "docs.claude.com / platform.claude.com, anthropic.com/engineering, modelcontextprotocol.io, "
    "code.claude.com/docs, and github.com/anthropics. Prefer 'why' and 'when would you' questions over definitions. "
    "Answers must be accurate for the current product; never invent API names, flags or URLs."
)

HINDI_SYSTEM = (
    "You write review questions for an engineer adding Hindi to a voice assistant's ASR and NLU (for example "
    "Samsung Bixby). Use web search to check facts against primary sources: arXiv and ACL/Interspeech papers, "
    "AI4Bharat, Hugging Face model and dataset cards, NVIDIA NeMo, ESPnet, k2, Kaldi and bixbydevelopers.com docs "
    "(cite bixbydevelopers.com itself, never mirror sites). "
    "Use Hindi (Devanagari) examples where they help. Prefer 'why', 'how would you test' and 'what goes wrong' "
    "questions over definitions. Never invent numbers, model names or URLs."
)


def build_prompt(course: dict, lessons: list[tuple[int, str, str]], per_lesson: int) -> str:
    listing = "\n".join(f"{i}. [{section}] {title}" for i, section, title in lessons)
    return (
        f"Course: {course['title']} ({course['url']})\n"
        f"About the course: {course['summary']}\n\n"
        f"Write exactly {per_lesson} review question(s) for EACH lesson below. Use the lesson's number as "
        f"lesson_index. Mix recall, application and design-tradeoff questions.\n\nLessons:\n{listing}"
    )


async def write_course_qa(llm: LLMClient, course: dict, per_lesson: int, system: str = SYSTEM) -> list[dict]:
    """Return Q&A dicts for every lesson of `course`, with checked references."""
    lessons = [(i, sec, t) for i, (sec, t) in enumerate((s, t) for s, ls in course["outline"] for t in ls)]
    chunks = [lessons[i:i + LESSONS_PER_CALL] for i in range(0, len(lessons), LESSONS_PER_CALL)]

    async def one(chunk):
        out = await llm.ask_json(build_prompt(course, chunk, per_lesson), QABatchOut, system=system,
                                 model=config.LLM_MODEL, web=True, timeout=max(config.LLM_TIMEOUT, 600))
        valid = {i for i, _, _ in chunk}
        return [it for it in out.items if it.lesson_index in valid]

    results = await asyncio.gather(*(one(c) for c in chunks), return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    items = [it for r in results if not isinstance(r, Exception) for it in r]
    if not items:
        raise failures[0] if failures else RuntimeError("The model returned no questions.")
    if failures:
        log.warning("%d of %d Q&A batches failed for %s: %s", len(failures), len(chunks), course["slug"], failures[0])

    titles = {i: t for i, _, t in lessons}
    refs = await asyncio.gather(*(verify_sources([r.model_dump() for r in it.references]) for it in items))
    counts: dict[int, int] = {}
    out = []
    for it, kept in zip(items, refs):
        pos = counts.get(it.lesson_index, 0)
        counts[it.lesson_index] = pos + 1
        out.append({"lesson_idx": it.lesson_index, "lesson_title": titles[it.lesson_index], "position": pos,
                    "question": it.question.strip(), "answer_md": it.answer_md.strip(),
                    "key_points": it.key_points, "references": kept})
    out.sort(key=lambda q: (q["lesson_idx"], q["position"]))
    return out
