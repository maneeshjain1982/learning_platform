"""Video Search, Paper Search and Curator agents."""

from __future__ import annotations

import asyncio
import difflib
import logging
import re

from .. import config
from ..llm import LLMClient
from ..providers import Candidate, arxiv_by_ids, norm_title, paper_search, youtube_verify
from .schemas import CuratorOut, KnownPapersOut, VideoPicksOut, VideoSearchOut

log = logging.getLogger("study.agents.search")

VIDEO_SYSTEM = (
    "You find educational YouTube videos using web search. Only return URLs that you actually saw in search "
    "results or on youtube.com pages - never guess or construct a video URL. Prefer university lectures, "
    "conference talks, well-known educators and official channels. Skip clickbait and shorts."
)


class VideoSearchAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def for_module(self, *, path_title: str, level: str, module, lessons) -> list[tuple[int, Candidate, str]]:
        """Returns (lesson_index, verified video, why) for a module's lessons.

        One search for the whole module, then one follow-up search for lessons still without a verified video.
        """
        found = await self._search(path_title, level, module, lessons, list(range(len(lessons))))
        missing = sorted(set(range(len(lessons))) - {i for i, _, _ in found})
        if missing:
            seen = {c.external_id for _, c, _ in found}
            extra = await self._search(path_title, level, module, lessons, missing)
            found += [x for x in extra if x[1].external_id not in seen]
        return found

    async def _search(self, path_title, level, module, lessons, indexes: list[int]):
        lesson_lines = "\n".join(
            f"{i}. {lessons[i].title} — keywords: {', '.join(lessons[i].keywords)}" for i in indexes
        )
        prompt = (
            f"Learning path: {path_title} (learner level: {level})\n"
            f"Module: {module.title} — {module.summary}\n"
            f"Lessons (use these index numbers):\n{lesson_lines}\n\n"
            "Search YouTube (via web search) and pick at least one, ideally two, good videos for EACH lesson "
            "listed (at most 8 in total). Return the exact watch URLs you found."
        )
        try:
            picks = await self.llm.ask_json(prompt, VideoPicksOut, system=VIDEO_SYSTEM, model=config.LLM_MODEL,
                                            web=True)
        except Exception as exc:
            if len(indexes) < len(lessons):  # follow-up pass: keep what we already have
                log.warning("Follow-up video search failed: %s", exc)
                return []
            raise
        return await self._verify([(p.lesson_index, p.url, p.why) for p in picks.videos if p.lesson_index in indexes])

    async def free_search(self, query: str, level: str = "intermediate") -> list[tuple[Candidate, str]]:
        prompt = (
            f"Find up to 8 good YouTube videos for: {query}\nLearner level: {level}.\n"
            "Return the exact watch URLs you found and one short sentence on why each is worth watching."
        )
        out = await self.llm.ask_json(prompt, VideoSearchOut, system=VIDEO_SYSTEM, model=config.LLM_MODEL, web=True)
        verified = await self._verify([(0, v.url, v.why) for v in out.videos])
        return [(c, why) for _, c, why in verified]

    @staticmethod
    async def _verify(items: list[tuple[int, str, str]]) -> list[tuple[int, Candidate, str]]:
        checks = await asyncio.gather(*(youtube_verify(url) for _, url, _ in items))
        seen: set[str] = set()
        out = []
        for (idx, url, why), cand in zip(items, checks):
            if cand is None:
                log.info("Dropped unverifiable video URL %s", url)
                continue
            if cand.external_id in seen:
                continue
            seen.add(cand.external_id)
            out.append((idx, cand, why))
        return out


PAPER_SYSTEM = (
    "You are a research librarian for machine learning and computer science. Only list papers you are certain "
    "exist on arXiv, with their exact arXiv id and title. If unsure about an id, leave the paper out."
)


def titles_match(expected: str, got: str) -> bool:
    a, b = norm_title(expected), norm_title(got)
    return bool(a and b) and (a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.75)


class PaperSearchAgent:
    """Foundational papers named by the LLM (each verified on arXiv by id + title), plus an arXiv search."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm

    async def known_papers(self, module, lessons) -> list[Candidate]:
        if self.llm is None:
            return []
        prompt = (
            f"Module: {module.title} — {module.summary}\nLessons: " + "; ".join(l.title for l in lessons)
            + "\n\nList up to 5 foundational or widely-cited arXiv papers a learner should know for this module."
        )
        try:
            out = await self.llm.ask_json(prompt, KnownPapersOut, system=PAPER_SYSTEM, model=config.LLM_FAST_MODEL)
        except Exception as exc:
            log.warning("Known-paper suggestion failed: %s", exc)
            return []
        wanted = {p.arxiv_id.strip().removeprefix("arXiv:"): p.title for p in out.papers[:5]}
        found = await arxiv_by_ids([i for i in wanted if re.match(r"^\d{4}\.\d{4,5}$", i)])
        verified = [c for c in found if titles_match(wanted.get(c.external_id, ""), c.title)]
        log.info("Known papers for %r: %d suggested, %d verified", module.title, len(wanted), len(verified))
        return verified

    async def for_module(self, module, lessons=()) -> list[Candidate]:
        results = await self.known_papers(module, lessons)
        seen = {c.external_id for c in results}
        queries = (module.paper_keywords or module.keywords or [module.title])[:2]
        for q in queries:  # sequential: arXiv asks for polite pacing
            for c in await paper_search(q, limit=5):
                if c.external_id not in seen:
                    seen.add(c.external_id)
                    results.append(c)
        return results[:10]


CURATOR_SYSTEM = "You are a careful teaching assistant who matches reading material to lessons. Be selective."


class Curator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def assign_papers(self, *, level: str, module, lessons, papers: list[Candidate]) -> list[tuple[int, int, str]]:
        """Returns (lesson_index, paper_index, why). Falls back to a simple rule if the LLM fails."""
        if not papers:
            return []
        lesson_lines = "\n".join(f"{i}. {l.title}: {'; '.join(l.objectives)}" for i, l in enumerate(lessons))
        paper_lines = "\n".join(
            f"{i}. {p.title} ({p.year or 'n.d.'}) — {p.summary[:300]}" for i, p in enumerate(papers)
        )
        prompt = (
            f"Learner level: {level}\nModule: {module.title}\nLessons:\n{lesson_lines}\n\nCandidate papers:\n"
            f"{paper_lines}\n\nAssign only clearly relevant papers to the lesson they help most (at most 2 per "
            "lesson, at most 5 total). Skip papers that are off-topic or too niche for this level."
        )
        try:
            out = await self.llm.ask_json(prompt, CuratorOut, system=CURATOR_SYSTEM, model=config.LLM_FAST_MODEL)
            return [(a.lesson_index, a.paper_index, a.why) for a in out.assignments
                    if 0 <= a.lesson_index < len(lessons) and 0 <= a.paper_index < len(papers)]
        except Exception as exc:
            log.warning("Curator fell back to default assignment: %s", exc)
            return [(0, i, "Related reading for this module.") for i in range(min(3, len(papers)))]
