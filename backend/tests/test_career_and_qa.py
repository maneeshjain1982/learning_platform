import time

import pytest

from backend.agents import career as career_agent
from backend.agents import review


def _wait(client, url, key="status"):
    for _ in range(100):
        d = client.get(url).json()
        st = d[key]["status"] if isinstance(d.get(key), dict) else d[key]
        if st != "running":
            return d
        time.sleep(0.05)
    raise AssertionError("job did not finish")


async def _state(url):
    return "dead" if "dead.example" in url else "ok"


@pytest.fixture()
def llm(fake_llm, monkeypatch):
    original = fake_llm.ask_json

    async def ask_json(prompt, schema, **kw):
        if schema is review.QABatchOut:
            idx = [int(line.split(".")[0]) for line in prompt.split("Lessons:\n")[1].splitlines() if line]
            ref = lambda u: {"title": "Docs", "url": u}  # noqa: E731
            return schema(items=[{"lesson_index": i, "question": f"Q{i}-{k}?", "answer_md": "A", "key_points": ["k"],
                                  "references": [ref("https://ok.example.com/d"), ref("https://dead.example.com/x")]}
                                 for i in idx for k in range(2)] + [
                {"lesson_index": 999, "question": "stray", "answer_md": "x", "key_points": [], "references": []}])
        if schema is career_agent.CertFindOut:
            return schema(summary="One new exam.", items=[
                {"name": "New Agent Exam", "issuer": "X", "tier": "architect", "change": "new", "what_changed": "Oct",
                 "focus": "f", "fit": "g", "url": "https://ok.example.com/cert"},
                {"name": "Dead", "issuer": "Y", "tier": "developer", "change": "new", "what_changed": "",
                 "focus": "f", "fit": "g", "url": "https://dead.example.com/c"}])
        if schema is career_agent.JobSearchOut:
            assert ("Pune" in prompt or "based in India" in prompt) and kw["web"] is True
            job = lambda t, u, d, s: {"title": t, "company": "Acme", "location": "Pune", "url": u, "posted": d,  # noqa
                                      "summary": "s", "responsibilities": ["r"], "must_have": ["long " + x for x in s],
                                      "skill_tags": s}
            return schema(market_summary="Hot.", trends=["MCP"], jobs=[
                job("Old", "https://ok.example.com/j1", "2026-10-01", ["MCP", "Python"]),
                job("New", "https://ok.example.com/j2", "2026-11-10", ["MCP"]),
                job("Gone", "https://dead.example.com/j", "2026-11-11", ["Go"])])
        return await original(prompt, schema, **kw)

    monkeypatch.setattr(fake_llm, "ask_json", ask_json, raising=False)
    monkeypatch.setattr(career_agent, "check_url", _state)
    return fake_llm


def test_review_qa_generate_and_mark(client, llm):
    url = "/api/claude-academy/qa/introduction-to-subagents"
    assert client.get(url).json()["items"] == []
    assert client.post(url + "/generate", json={"per_lesson": 2}).json()["job"]["status"] == "running"
    d = _wait(client, url, "job")
    assert d["job"]["status"] == "ready", d["job"]
    assert len(d["items"]) == 8  # 4 lessons x 2, stray lesson index dropped
    assert d["items"][0]["lesson_title"] == "What are subagents?"
    assert [r["url"] for r in d["items"][0]["references"]] == ["https://ok.example.com/d"]

    qid = d["items"][0]["id"]
    assert client.patch(f"/api/claude-academy/qa/items/{qid}", json={"status": "known"}).json()["status"] == "known"
    cat = client.get("/api/claude-academy").json()
    sub = next(c for c in cat["courses"] if c["slug"] == "introduction-to-subagents")
    assert sub["qa"] == {"total": 8, "known": 1, "review": 0}

    # Regenerating keeps marks on questions that come back unchanged.
    client.post(url + "/generate", json={"per_lesson": 2})
    d = _wait(client, url, "job")
    assert d["items"][0]["status"] == "known"
    assert client.get("/api/claude-academy/qa/claude-101").status_code == 400  # no outline
    assert client.get("/api/claude-academy/qa/nope").status_code == 404


def test_certifications_curated_and_refresh(client, llm):
    d = client.get("/api/career/certifications").json()
    assert len(d["certs"]) >= 15 and {t["id"] for t in d["tiers"]} == {c["tier"] for c in d["certs"]}
    assert all(c["url"].startswith("https://") for c in d["certs"])
    client.post("/api/career/certifications/refresh")
    d = _wait(client, "/api/career/certifications", "refresh")
    assert [i["name"] for i in d["refresh"]["items"]] == ["New Agent Exam"]
    assert d["refresh"]["dropped"] == 1


def test_jobs_refresh(client, llm):
    assert client.get("/api/career/jobs").json()["status"] == "idle"
    client.post("/api/career/jobs/refresh", json={"location": "Pune", "count": 5})
    d = _wait(client, "/api/career/jobs")
    assert d["status"] == "ready", d
    assert [j["title"] for j in d["jobs"]] == ["New", "Old"]
    assert d["top_skills"][0] == {"skill": "MCP", "count": 2}
    assert d["params"]["location"] == "Pune" and d["dropped"] == 1


def test_jobs_country(client, llm):
    from backend.agents.career import job_location
    assert "Only include postings based in India" in job_location("India", "Bengaluru")
    assert job_location("Remote") == "remote roles only (any country)"
    assert job_location("", "") == "any location; include remote roles"
    client.post("/api/career/jobs/refresh", json={"country": "India", "location": "Bengaluru", "count": 5})
    d = _wait(client, "/api/career/jobs")
    assert d["status"] == "ready", d
    assert d["params"]["country"] == "India" and d["params"]["location"] == "Bengaluru"


def test_home_has_no_jobs_card(client):
    assert "jobs" not in {c["id"] for c in client.get("/api/home/layout").json()}
