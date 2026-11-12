"""Languages in the Voice (ASR + NLU) tab. Each language is a content module with the same attributes
(see hindi_voice.py and english_voice.py)."""

from __future__ import annotations

from types import ModuleType

from . import english_voice, hindi_voice

LANGS: dict[str, ModuleType] = {"hi": hindi_voice, "en": english_voice}
MODULE_INDEX: dict[str, tuple[ModuleType, dict]] = {
    m["slug"]: (lang, m) for lang in LANGS.values() for m in lang.MODULES}
