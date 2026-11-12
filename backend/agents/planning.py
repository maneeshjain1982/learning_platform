"""Topic Identifier and Curriculum Planner agents."""

from __future__ import annotations

from .. import config
from ..llm import LLMClient
from .schemas import CurriculumOut, TopicGraphOut

GOALS = {
    "understand": "understand the concepts well",
    "build": "build a real project",
    "interview": "prepare for technical interviews",
    "research": "read and understand research papers",
}

SYSTEM = (
    "You are an expert curriculum designer for self-directed adult learners. "
    "Be concrete and accurate. Prefer widely-taught, well-established concepts. Never invent sources."
)


def describe_requirement(req) -> str:
    return (
        f"Learning request: {req.raw_text.strip()}\n"
        f"Goal: {GOALS.get(req.goal, req.goal)}\n"
        f"Current level: {req.level}\n"
        f"Time available: about {req.hours_per_week} hours per week for {req.weeks} weeks "
        f"(~{req.hours_per_week * req.weeks} hours total)\n"
        f"Preferred formats: {', '.join(req.formats) or 'any'}"
    )


class TopicIdentifier:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, req) -> TopicGraphOut:
        prompt = (
            describe_requirement(req)
            + "\n\nAnalyse this learning request. Identify the core topics the learner needs, in learning order, "
              "with prerequisites for each, what is out of scope for their goal, and short search keywords."
        )
        return await self.llm.ask_json(prompt, TopicGraphOut, system=SYSTEM, model=config.LLM_MODEL)


class CurriculumPlanner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def run(self, req, topics: TopicGraphOut) -> CurriculumOut:
        total_min = req.hours_per_week * req.weeks * 60
        topic_lines = "\n".join(f"- {t.name}: {t.description}" for t in topics.core_topics)
        prompt = (
            describe_requirement(req)
            + f"\n\nPath title: {topics.title}\nCore topics (in order):\n{topic_lines}\n"
            + f"Out of scope: {', '.join(topics.out_of_scope) or 'none'}\n\n"
              "Design a sequential course: 4-7 modules, each with 3-5 lessons, simple to advanced, each lesson "
              "building on the previous one. Lesson study time should add up to roughly "
              f"{int(total_min * 0.6)} minutes (the rest of the time goes to videos, papers and practice). "
              "Keywords must be short, searchable phrases (e.g. 'function calling LLM', not full sentences)."
        )
        return await self.llm.ask_json(prompt, CurriculumOut, system=SYSTEM, model=config.LLM_MODEL)
