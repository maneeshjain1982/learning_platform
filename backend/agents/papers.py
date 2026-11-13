"""Paper summary: the LLM reads the paper (arXiv abstract page and full text when it can open it) and writes a
short structured summary. Numbers must come from the paper."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient

ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})", re.I)


def arxiv_id(text: str) -> str | None:
    """arXiv id from a URL or a bare id, without the version suffix."""
    text = (text or "").strip()
    m = ARXIV_ID.search(text)
    raw = m.group(1) if m else text if re.fullmatch(r"[0-9]{4}\.[0-9]{4,5}(v\d+)?", text) else None
    return re.sub(r"v\d+$", "", raw) if raw else None


class PaperSummary(BaseModel):
    tldr: str = Field(description="One or two plain sentences: what the paper does and its main finding")
    problem: str = Field(description="The problem it tackles and why it was hard (2-3 sentences)")
    method: str = Field(description="How it works: the key idea, model or setup (3-4 sentences)")
    results: list[str] = Field(description="2-5 key results with the numbers and benchmarks exactly as reported")
    limitations: list[str] = Field(description="1-3 limitations or open questions (stated by the authors or evident)")
    why_it_matters: str = Field(description="One or two sentences on why it matters for the reader's topic")
    read_full_text: bool = Field(description="True if you read the full paper, false if only the abstract")


SYSTEM = (
    "You summarize research papers for an engineer. Read the paper itself with web search/fetch; do not rely on "
    "memory. Every number and claim must come from the paper. Be concise and concrete; no hype."
)


async def summarize(llm: LLMClient, *, title: str, url: str, abstract: str = "", context: str = "",
                    aid: str | None = None) -> dict:
    where = (f"Abstract page: https://arxiv.org/abs/{aid}\nFull text (HTML, if available): "
             f"https://arxiv.org/html/{aid}\nPDF: https://arxiv.org/pdf/{aid}") if aid else f"Link: {url}"
    prompt = (f"Summarize this paper.\nTitle: {title}\n{where}\n"
              + (f"\nAbstract (from arXiv):\n{abstract.strip()}\n" if abstract else "")
              + (f"\nThe reader is studying: {context}\n" if context else "")
              + "\nOpen the full text if you can; otherwise work from the abstract and say so via read_full_text.")
    out = await llm.ask_json(prompt, PaperSummary, system=SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=max(config.LLM_TIMEOUT, 600))
    return out.model_dump()
