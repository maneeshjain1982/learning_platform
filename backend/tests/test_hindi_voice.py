import time

import pytest

from backend import hindi_voice as hv
from backend.agents import career as career_agent
from backend.agents import hindi_voice as agent
from backend.agents import review
from backend.agents.hindi_voice import SlotValue, annotate


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
        seen["system"] = kw.get("system", "")
        if schema is agent.VoiceFindOut:
            return schema(summary="New Hindi models.", items=[
                {"kind": "ASR model", "title": "New ASR", "date": "2026-10-01", "summary": "s", "why_it_matters": "w",
                 "url": "https://ok.example.com/m"},
                {"kind": "Paper", "title": "Gone", "summary": "s", "why_it_matters": "w",
                 "url": "https://dead.example.com/p"}])
        if schema is agent.UtteranceOut:
            assert "set_alarm" in prompt.lower() or "SetAlarm" in prompt
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


def test_overview_and_state(client):
    d = client.get("/api/hindi-voice").json()
    assert len(d["modules"]) == len(hv.MODULES) and d["modules"][0]["qa"]["total"] == 0
    assert all(p["url"].startswith("https://arxiv.org/abs/") for p in d["papers"])
    skill = d["competencies"][0]["skills"][0]["name"]
    assert client.put("/api/hindi-voice/state", json={"kind": "skill", "key": skill, "value": 3}).status_code == 200
    assert client.put("/api/hindi-voice/state", json={"kind": "skill", "key": "nope", "value": 3}).status_code == 400
    assert client.put("/api/hindi-voice/state", json={"kind": "step", "key": "scope:0", "value": True}).status_code == 200
    assert client.put("/api/hindi-voice/state", json={"kind": "course", "key": "slp3", "value": "doing"}).status_code == 200
    d = client.get("/api/hindi-voice").json()
    assert d["competencies"][0]["skills"][0]["level"] == 3
    assert d["steps_done"] == ["scope:0"]
    assert next(c for c in d["courses"] if c["id"] == "slp3")["status"] == "doing"
    client.put("/api/hindi-voice/state", json={"kind": "step", "key": "scope:0", "value": False})
    assert client.get("/api/hindi-voice").json()["steps_done"] == []


def test_path(client):
    r = client.post("/api/hindi-voice/path").json()
    assert r["created"] is True
    path = client.get(f"/api/paths/{r['path_id']}").json()
    assert path["modules"] == len(hv.MODULES)
    assert client.post("/api/hindi-voice/path").json() == {"path_id": r["path_id"], "created": False}
    assert client.get("/api/hindi-voice").json()["path_id"] == r["path_id"]


def test_research_refresh(client, llm):
    assert client.post("/api/hindi-voice/research/refresh", json={"months": 6}).json()["status"] == "running"
    d = _wait(client, "/api/hindi-voice/research")
    assert d["status"] == "ready" and [i["title"] for i in d["items"]] == ["New ASR"] and d["dropped"] == 1
    assert d["months"] == 6


def test_utterance_generator(client, llm):
    body = {"intent": "SetAlarm", "description": "Set an alarm",
            "slots": [{"name": "time", "examples": "7 बजे"}, {"name": "date", "examples": "कल"}],
            "count": 10, "styles": ["devanagari", "romanized", "hinglish"]}
    assert client.post("/api/hindi-voice/utterances/generate", json=body).json()["status"] == "running"
    d = _wait(client, "/api/hindi-voice/utterances")
    assert d["status"] == "ready" and len(d["items"]) == 3  # duplicate removed
    first = d["items"][0]
    assert [s["name"] for s in first["slots"]] == ["time", "date"]
    assert first["annotated"] == "[g:SetAlarm] (कल)[v:date] (सुबह 7 बजे)[v:time] का alarm लगाओ"
    assert d["items"][1]["slots"] == [] and d["dropped_slots"] == 2
    bad = client.post("/api/hindi-voice/utterances/generate", json={**body, "intent": "bad intent!"})
    assert bad.status_code == 422


def test_annotate_overlaps():
    out = annotate("मुंबई से दिल्ली", "Book", [SlotValue(name="to", value="दिल्ली"), SlotValue(name="from", value="मुंबई")])
    assert out == "[g:Book] (मुंबई)[v:from] से (दिल्ली)[v:to]"


def test_module_qa_uses_shared_endpoints(client, llm):
    url = "/api/claude-academy/qa/hv-eval"
    assert client.post(url + "/generate", json={"per_lesson": 1}).status_code == 200
    d = _wait(client, url)
    assert len(d["items"]) == hv.MODULE_BY_SLUG["hv-eval"]["lessons"]
    assert "Hindi" in llm.seen["system"]
    qa = next(m for m in client.get("/api/hindi-voice").json()["modules"] if m["slug"] == "hv-eval")["qa"]
    assert qa["total"] == len(d["items"])
