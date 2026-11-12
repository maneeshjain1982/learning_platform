"""Voice (ASR + NLU) agents, per language: research refresh (new models, datasets, papers, news) and the
utterance generator. Language-specific prompts and styles live in the language content module."""

from __future__ import annotations

import logging
import re
from datetime import date
from types import ModuleType
from typing import Literal

from pydantic import BaseModel, Field

from .. import config
from ..llm import LLMClient
from .career import _check

log = logging.getLogger("study.voice")
TIMEOUT = max(config.LLM_TIMEOUT, 600)

# ---------------------------------------------------------------- research refresh

FindKind = Literal["ASR model", "NLU / LLM model", "Dataset", "Paper", "Tool", "News"]


class VoiceFind(BaseModel):
    kind: FindKind
    title: str
    org: str = Field("", description="Organisation or authors")
    date: str = Field("", description="Release or publication date, YYYY-MM-DD or YYYY-MM if known")
    summary: str = Field(description="1-2 sentences: what it is")
    why_it_matters: str = Field(description="One sentence on why it matters for ASR/NLU in a voice assistant")
    result: str = Field("", description="Benchmark result exactly as reported, with the benchmark name, else empty")
    licence: str = ""
    url: str = Field(description="Official page, model card, repo or arXiv URL you opened")


class VoiceFindOut(BaseModel):
    summary: str = Field(description="Two sentences on what changed recently")
    items: list[VoiceFind] = Field(description="6-15 items")


async def find_research(llm: LLMClient, lang: ModuleType, known: list[str], months: int = 12,
                        today: date | None = None) -> dict:
    listing = "\n".join(f"- {k}" for k in known)
    prompt = (f"Today is {(today or date.today()).isoformat()}. " + lang.RESEARCH_PROMPT.format(months=months)
              + " Skip anything in the known list unless it had a significant new version.\n\nKnown list:\n" + listing)
    out = await llm.ask_json(prompt, VoiceFindOut, system=lang.RESEARCH_SYSTEM, model=config.LLM_MODEL, web=True,
                             timeout=TIMEOUT)
    kept, dropped = await _check([i.model_dump() for i in out.items])
    kept.sort(key=lambda i: i["date"] or "", reverse=True)
    return {"summary": out.summary, "items": kept, "dropped": dropped}


# ---------------------------------------------------------------- utterance generator


class SlotSpec(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    examples: str = Field("", max_length=300, description="Comma-separated example values")


class SlotValue(BaseModel):
    name: str
    value: str = Field(description="The exact substring of the utterance text that fills this slot")


class Utterance(BaseModel):
    text: str
    style: str = Field(description="One of the style ids you were given")
    tone: Literal["casual", "polite", "formal"] = "casual"
    slots: list[SlotValue] = Field(default_factory=list)


class UtteranceOut(BaseModel):
    utterances: list[Utterance]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


async def generate_utterances(llm: LLMClient, lang: ModuleType, intent: str, description: str,
                              slots: list[SlotSpec], count: int, styles: list[str]) -> dict:
    slot_lines = "\n".join(f"- {s.name}: e.g. {s.examples or '(choose realistic values)'}" for s in slots) or "- (none)"
    style_lines = "\n".join(f"- {s}: {lang.UTTER_STYLES[s][1]}" for s in styles)
    prompt = (
        f"Intent: {intent}\nWhat it does: {description or '(infer from the name)'}\nSlots:\n{slot_lines}\n\n"
        f"Write {count} DIFFERENT {lang.NAME} utterances a user might say for this intent, spread evenly across "
        f"these styles (use the style id as `style`):\n{style_lines}\n\nVary: {lang.GEN_VARY} (use new realistic "
        "values, not only the examples). Some utterances may leave out optional slots. For each slot you use, give "
        "its value as the exact substring in the text."
    )
    out = await llm.ask_json(prompt, UtteranceOut, system=lang.GEN_SYSTEM, model=config.LLM_MODEL, timeout=TIMEOUT)
    known = {s.name for s in slots}
    seen, items, fixed = set(), [], 0
    for u in out.utterances:
        text = u.text.strip()
        if not text or _norm(text) in seen or u.style not in styles:
            continue
        seen.add(_norm(text))
        good = [s for s in u.slots if s.name in known and s.value and s.value in text]
        fixed += len(u.slots) - len(good)
        items.append({"text": text, "style": u.style, "tone": u.tone,
                      "slots": [s.model_dump() for s in good], "annotated": annotate(text, intent, good)})
    return {"items": items, "dropped_slots": fixed}


def annotate(text: str, intent: str, slots: list[SlotValue]) -> str:
    """Bixby Aligned-NL style: `[g:Intent] text (value)[v:slot] text`, marking the first non-overlapping
    occurrence of each slot value (longest values first)."""
    spans: list[tuple[int, int, str]] = []
    for s in sorted(slots, key=lambda s: -len(s.value)):
        start = 0
        while (i := text.find(s.value, start)) != -1:
            end = i + len(s.value)
            if all(end <= a or i >= b for a, b, _ in spans):
                spans.append((i, end, s.name))
                break
            start = i + 1
    out, pos = [], 0
    for a, b, name in sorted(spans):
        out += [text[pos:a], f"({text[a:b]})[v:{name}]"]
        pos = b
    out.append(text[pos:])
    return f"[g:{intent}] {''.join(out)}"
