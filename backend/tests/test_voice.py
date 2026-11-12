import time

import pytest

from backend import english_voice as ev
from backend import hindi_voice as hv
from backend.agents import career as career_agent
from backend.agents import review
from backend.agents import voice as agent
from backend.agents.voice import SlotValue, annotate
from backend.voice_langs import LANGS

API = "/api/voice"


def _wait(client, url):
    for _ in range(100):
        d = client.get(url).json()
        st = d["job"]["status"] if "job" in d else d["status"]
        if st != "running":
            return d
        time.sleep(0.05)
    raise AssertionError("job did not finish")


async def _state(url):
    return "dead" if "dead.example" in url else "ok"


@pytest.fixture()
def llm(fake_llm, monkeypatch):
    original = fake_llm.ask_json
    seen = {}

    async def ask_json(prompt, schema, **kw):
        seen["system"], seen["prompt"] = kw.get("system", ""), prompt
        if schema is agent.VoiceFindOut:
            return schema(summary="New models.", items=[
                {"kind": "ASR model", "title": "New ASR", "date": "2026-10-01", "summary": "s", "why_it_matters": "w",
                 "url": "https://ok.example.com/m"},
                {"kind": "Paper", "title": "Gone", "summary": "s", "why_it_matters": "w",
                 "url": "https://dead.example.com/p"}])
        if schema is agent.UtteranceOut:
            if "English utterances" in prompt:
                return schema(utterances=[
                    {"text": "kindly set an alarm for 7 am tomorrow", "style": "indian",
                     "slots": [{"name": "time", "value": "7 am"}, {"name": "date", "value": "tomorrow"}]},
                    {"text": "alarm 7 tmrw", "style": "hinglish", "slots": []}])  # style not requested: dropped
            return schema(utterances=[
                {"text": "कल सुबह 7 बजे का alarm लगाओ", "style": "hinglish",
                 "slots": [{"name": "time", "value": "सुबह 7 बजे"}, {"name": "date", "value": "कल"}]},
                {"text": "kal subah 7 baje alarm laga do", "style": "romanized",
                 "slots": [{"name": "time", "value": "not in text"}]},
                {"text": "कल सुबह 7 बजे का alarm लगाओ", "style": "hinglish", "slots": []},  # duplicate
                {"text": "अलार्म लगाइए", "style": "devanagari", "slots": [{"name": "bogus", "value": "अलार्म"}]}])
        if schema is review.QABatchOut:
            idx = [int(line.split(".")[0]) for line in prompt.split("Lessons:\n")[1].splitlines() if line]
            return schema(items=[{"lesson_index": i, "question": f"Q{i}?", "answer_md": "A", "key_points": ["k"],
                                  "references": []} for i in idx])
        return await original(prompt, schema, **kw)

    monkeypatch.setattr(fake_llm, "ask_json", ask_json, raising=False)
    monkeypatch.setattr(career_agent, "check_url", _state)
    fake_llm.seen = seen
    return fake_llm


def test_language_modules_are_consistent():
    for lang in LANGS.values():
        assert all(m["slug"].startswith(lang.SLUG_PREFIX) for m in lang.MODULES)
        assert {m["side"] for m in lang.MODULES} <= {s["id"] for s in lang.SIDES}
        assert {m["kind"] for m in lang.MODELS} <= {k["id"] for k in lang.MODEL_KINDS}
        assert {d["kind"] for d in lang.DATASETS} <= {k["id"] for k in lang.DATASET_KINDS}
        assert {p["topic"] for p in lang.PAPERS} <= {t["id"] for t in lang.PAPER_TOPICS}
        assert {c["phase"] for c in lang.COURSES} <= {p["id"] for p in lang.PHASES}
        assert len({p["id"] for p in lang.PAPERS}) == len(lang.PAPERS)
        assert set(lang.DEFAULT_UTTER["styles"]) <= set(lang.UTTER_STYLES)


def test_languages_and_unknown(client):
    assert [l["code"] for l in client.get(API).json()] == ["hi", "en"]
    assert client.get(f"{API}/fr").status_code == 404


@pytest.mark.parametrize("code,mod", [("hi", hv), ("en", ev)])
def test_overview_and_state(client, code, mod):
    d = client.get(f"{API}/{code}").json()
    assert d["name"] == mod.NAME and len(d["modules"]) == len(mod.MODULES)
    assert all(p["url"].startswith("https://arxiv.org/abs/") for p in d["papers"])
    skill = d["competencies"][0]["skills"][0]["name"]
    url = f"{API}/{code}/state"
    assert client.put(url, json={"kind": "skill", "key": skill, "value": 3}).status_code == 200
    assert client.put(url, json={"kind": "skill", "key": "nope", "value": 3}).status_code == 400
    assert client.put(url, json={"kind": "step", "key": "scope:0", "value": True}).status_code == 200
    assert client.put(url, json={"kind": "course", "key": "slp3", "value": "doing"}).status_code == 200
    d = client.get(f"{API}/{code}").json()
    assert d["competencies"][0]["skills"][0]["level"] == 3 and d["steps_done"] == ["scope:0"]
    assert next(c for c in d["courses"] if c["id"] == "slp3")["status"] == "doing"
    client.put(url, json={"kind": "step", "key": "scope:0", "value": False})
    assert client.get(f"{API}/{code}").json()["steps_done"] == []


def test_languages_keep_separate_state(client):
    levels = lambda c: [s["level"] for a in client.get(f"{API}/{c}").json()["competencies"] for s in a["skills"]]  # noqa: E731
    before = levels("en")
    skill = client.get(f"{API}/hi").json()["competencies"][0]["skills"][1]["name"]
    assert skill in {s[0] for a in ev.COMPETENCIES for s in a["skills"]}  # same skill name in both languages
    client.put(f"{API}/hi/state", json={"kind": "skill", "key": skill, "value": 4})
    assert levels("en") == before


@pytest.mark.parametrize("code,mod", [("hi", hv), ("en", ev)])
def test_path(client, code, mod):
    r = client.post(f"{API}/{code}/path").json()
    assert r["created"] is True
    assert client.get(f"/api/paths/{r['path_id']}").json()["modules"] == len(mod.MODULES)
    assert client.post(f"{API}/{code}/path").json() == {"path_id": r["path_id"], "created": False}


def test_research_refresh(client, llm):
    assert client.post(f"{API}/en/research/refresh", json={"months": 6}).json()["status"] == "running"
    d = _wait(client, f"{API}/en/research")
    assert d["status"] == "ready" and [i["title"] for i in d["items"]] == ["New ASR"] and d["dropped"] == 1
    assert "English" in llm.seen["prompt"] and d["months"] == 6
    assert client.get(f"{API}/hi/research").json()["status"] == "idle"


def test_hindi_utterances(client, llm):
    body = {"intent": "SetAlarm", "description": "Set an alarm",
            "slots": [{"name": "time", "examples": "7 बजे"}, {"name": "date", "examples": "कल"}],
            "count": 10, "styles": ["devanagari", "romanized", "hinglish"]}
    assert client.post(f"{API}/hi/utterances/generate", json=body).json()["status"] == "running"
    d = _wait(client, f"{API}/hi/utterances")
    assert d["status"] == "ready" and len(d["items"]) == 3  # duplicate removed
    assert d["items"][0]["annotated"] == "[g:SetAlarm] (कल)[v:date] (सुबह 7 बजे)[v:time] का alarm लगाओ"
    assert d["items"][1]["slots"] == [] and d["dropped_slots"] == 2
    assert client.post(f"{API}/hi/utterances/generate", json={**body, "intent": "bad intent!"}).status_code == 422


def test_english_utterances(client, llm):
    body = {"intent": "SetAlarm", "slots": [{"name": "time"}, {"name": "date"}], "count": 10,
            "styles": ["indian", "casual"]}
    assert client.post(f"{API}/en/utterances/generate", json={**body, "styles": ["hinglish"]}).status_code == 422
    client.post(f"{API}/en/utterances/generate", json=body)
    d = _wait(client, f"{API}/en/utterances")
    assert [i["style"] for i in d["items"]] == ["indian"]
    assert d["items"][0]["annotated"] == "[g:SetAlarm] kindly set an alarm for (7 am)[v:time] (tomorrow)[v:date]"
    assert "spoken in India" in llm.seen["prompt"]


def test_annotate_overlaps():
    out = annotate("मुंबई से दिल्ली", "Book", [SlotValue(name="to", value="दिल्ली"), SlotValue(name="from", value="मुंबई")])
    assert out == "[g:Book] (मुंबई)[v:from] से (दिल्ली)[v:to]"


@pytest.mark.parametrize("slug,word", [("hv-eval", "Hindi"), ("ev-eval", "English")])
def test_module_qa_uses_shared_endpoints(client, llm, slug, word):
    url = f"/api/claude-academy/qa/{slug}"
    assert client.post(url + "/generate", json={"per_lesson": 1}).status_code == 200
    d = _wait(client, url)
    lang = hv if slug.startswith("hv") else ev
    assert len(d["items"]) == lang.MODULE_BY_SLUG[slug]["lessons"]
    assert word in llm.seen["system"]
    code = lang.CODE
    qa = next(m for m in client.get(f"{API}/{code}").json()["modules"] if m["slug"] == slug)["qa"]
    assert qa["total"] == len(d["items"])
