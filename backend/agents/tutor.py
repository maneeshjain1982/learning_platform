"""Lesson Writer, Home Composer (focus note) and the Ask LLM tutor."""

from __future__ import annotations

from .. import config
from ..llm import Answer, LLMClient

WRITER_SYSTEM = (
    "You write clear, accurate lesson notes for self-directed learners, in Markdown. "
    "Explain with concrete examples; include short code where it helps. Do not invent citations or URLs."
)


class LessonWriter:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, *, path_title: str, level: str, module_title: str, lesson, prev_title: str | None,
                  next_title: str | None, resources: list[str]) -> str:
        prompt = (
            f"Learning path: {path_title} (learner level: {level})\nModule: {module_title}\n"
            f"Lesson: {lesson.title}\nObjectives:\n" + "\n".join(f"- {o}" for o in lesson.objectives) + "\n"
            + (f"Previous lesson: {prev_title}\n" if prev_title else "")
            + (f"Next lesson: {next_title}\n" if next_title else "")
            + ("Resources the learner will also see (you may refer to them by title):\n"
               + "\n".join(f"- {r}" for r in resources) + "\n" if resources else "")
            + f"\nWrite the lesson notes for about {lesson.est_minutes} minutes of reading. Structure:\n"
              "## Overview (2-3 sentences: what and why)\n"
              "## numbered concept sections with examples (and code blocks where useful)\n"
              "## Common pitfalls\n## Key takeaways (bullets)\n## Check yourself (3 short questions)\n"
              "Start directly with '## Overview'. Do not repeat the lesson title as a heading."
        )
        ans = await self.llm.ask(prompt, system=WRITER_SYSTEM, model=config.LLM_MODEL)
        return ans.text


class HomeComposer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def focus_note(self, *, path_title: str, module_title: str, lesson_title: str, done_count: int,
                         total: int, hours_per_week: int) -> str:
        prompt = (
            f"The learner is on the path '{path_title}'. They have finished {done_count} of {total} lessons. "
            f"Next lesson: '{lesson_title}' in module '{module_title}'. Their goal is {hours_per_week} hours/week.\n"
            "Write two short, friendly sentences (max 45 words) on why this lesson is today's focus and how it "
            "connects to what they already learned. No greeting, no emoji."
        )
        ans = await self.llm.ask(prompt, model=config.LLM_FAST_MODEL)
        return ans.text.strip().strip('"')


TUTOR_SYSTEM = (
    "You are a patient expert tutor inside a learning app. Answer the learner's question clearly and accurately, "
    "at their level. Use short paragraphs, bullets and small code examples when useful (Markdown). "
    "If the question relates to the current lesson, connect your answer to it. If you are not sure, say so. "
    "When asked to quiz, ask 3 questions one block at a time and wait for answers. Keep answers under 350 words "
    "unless asked for more."
)


class Tutor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def answer(self, *, question: str, history: list[tuple[str, str]], context: dict) -> Answer:
        ctx_lines = []
        if context.get("path"):
            ctx_lines.append(f"Learning path: {context['path']}")
        if context.get("level"):
            ctx_lines.append(f"Learner level: {context['level']}")
        if context.get("lesson"):
            ctx_lines.append(f"Current lesson: {context['lesson']}")
        if context.get("objectives"):
            ctx_lines.append("Lesson objectives: " + "; ".join(context["objectives"]))
        if context.get("notes"):
            ctx_lines.append("Lesson notes (excerpt):\n<<<\n" + context["notes"][:6000] + "\n>>>")

        convo = "\n\n".join(f"{'Learner' if r == 'user' else 'Tutor'}: {t}" for r, t in history[-10:])
        prompt = (
            ("Context:\n" + "\n".join(ctx_lines) + "\n\n" if ctx_lines else "")
            + (f"Conversation so far:\n{convo}\n\n" if convo else "")
            + f"Learner: {question}\n\nTutor:"
        )
        return await self.llm.ask(prompt, system=TUTOR_SYSTEM, model=config.LLM_MODEL)
