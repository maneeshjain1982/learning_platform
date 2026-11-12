"""Thin async wrapper over LLM_Bridge so agents never import the bridge directly.

The bridge is synchronous (it runs the vendor CLI as a subprocess), so calls run in a
worker thread, and a semaphore caps how many CLI processes run at once.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from . import config

log = logging.getLogger("study.llm")
T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """The bridge or its CLI is missing, or the call failed (limit, timeout, bad output)."""


@dataclass
class Answer:
    text: str
    model: str | None
    duration_ms: int | None
    provider: str


class LLMClient(Protocol):
    async def ask(self, prompt: str, *, system: str | None = None, model: str | None = None,
                  web: bool = False, timeout: int | None = None) -> Answer: ...

    async def ask_json(self, prompt: str, schema: type[T], *, system: str | None = None,
                       model: str | None = None, web: bool = False, timeout: int | None = None) -> T: ...


def inline_schema(schema: dict) -> dict:
    """Pydantic emits $defs/$ref; inline them and drop titles so every CLI accepts the schema."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return walk(defs[name])
            return {k: walk(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


class BridgeClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or config.LLM_PROVIDER
        self.model = model or config.LLM_MODEL
        self._sem = asyncio.Semaphore(config.LLM_MAX_PARALLEL)
        self._bridge = None

    def _get_bridge(self):
        if self._bridge is None:
            try:
                from llm_bridge import get_bridge
            except ImportError as exc:  # pragma: no cover
                raise LLMUnavailable("llm_bridge is not installed. Run: pip install -e D:/Y26/work_dir/LLM_Bridge") from exc
            try:
                self._bridge = get_bridge(self.provider, timeout=config.LLM_TIMEOUT)
            except Exception as exc:
                raise LLMUnavailable(str(exc)) from exc
        return self._bridge

    async def _call(self, **kwargs):
        from llm_bridge import LLMError

        bridge = self._get_bridge()
        async with self._sem:
            started = time.monotonic()
            try:
                result = await asyncio.to_thread(bridge.ask, **kwargs)
            except LLMError as exc:
                raise LLMUnavailable(str(exc)) from exc
            log.info("LLM %s/%s %.1fs web=%s", self.provider, kwargs.get("model"),
                     time.monotonic() - started, kwargs.get("web"))
            return result

    async def ask(self, prompt, *, system=None, model=None, web=False, timeout=None) -> Answer:
        res = await self._call(prompt=prompt, system_prompt=system, model=model or self.model, web=web,
                               timeout=timeout)
        return Answer(res.text.strip(), res.model or model or self.model, res.duration_ms, self.provider)

    async def ask_json(self, prompt, schema, *, system=None, model=None, web=False, timeout=None):
        js = inline_schema(schema.model_json_schema())
        last_err: Exception | None = None
        for attempt in range(2):
            res = await self._call(prompt=prompt, system_prompt=system, json_schema=js,
                                   model=model or self.model, web=web, timeout=timeout)
            try:
                return schema.model_validate(res.structured)
            except ValidationError as exc:
                last_err = exc
                log.warning("LLM JSON did not validate (attempt %d): %s", attempt + 1, exc)
        raise LLMUnavailable(f"The model's reply did not match the expected format: {last_err}")


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = BridgeClient()
    return _client


def set_llm(client: LLMClient | None) -> None:
    """Tests swap in a fake client."""
    global _client
    _client = client


def provider_status() -> list[dict]:
    try:
        from llm_bridge import list_providers
    except ImportError:
        return []
    return [
        {"name": p.name, "label": p.label, "available": p.available, "error": p.error, "models": p.models}
        for p in list_providers()
    ]
