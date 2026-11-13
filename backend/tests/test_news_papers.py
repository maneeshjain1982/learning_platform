import time

import pytest

from backend.agents import career as career_agent
from backend.agents import news as news_agent
from backend.agents import papers as papers_agent
from backend.agents.papers import arxiv_id
from backend.api import papers as papers_api
from backend.providers import Candidate


def _wait(c, method, url, body=None):
    for _ in range(100):
        d = c.post(url, json=body).json() if method == "post" else c.get(url).json()
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

    async def ask_json(prompt, schema, **kw):
        fake_llm.last_prompt = prompt
        if schema is news_agent.NewsOut:
            return schema(headline="Big week.", items=[
                {"topic": "ai", "title": "Model X", "source": "Lab", "date": "2026-11-10", "summary": "s",
                 "why_it_matters": "w", "url": "https://ok.example.com/x"},
                {"topic": "speech", "title": "Gone", "source": "S", "date": "", "summary": "s", "why_it_matters": "w",
                 "url": "https://dead.example.com/y"},
                {"topic": "cloud", "title": "Not asked", "source": "C", "date": "", "summary": "s",
                 "why_it_matters": "w", "url": "https://ok.example.com/z"}])
        if schema is papers_agent.PaperSummary:
            return schema(tldr="It reasons and acts.", problem="p", method="m", results=["+10 on HotpotQA"],
                          limitations=["l"], why_it_matters="w", read_full_text=True)
        return await original(prompt, schema, **kw)

    async def by_ids(ids):
        return [Candidate(kind="paper", source="arxiv", external_id=i, title="ReAct", url=f"https://arxiv.org/abs/{i}",
                          summary="We explore LLMs that reason and act.") for i in ids]

    monkeypatch.setattr(fake_llm, "ask_json", ask_json, raising=False)
    monkeypatch.setattr(career_agent, "check_url", _state)
    monkeypatch.setattr(papers_api, "arxiv_by_ids", by_ids)
    return fake_llm


def test_arxiv_id():
    assert arxiv_id("https://arxiv.org/abs/2210.03629v3") == "2210.03629"
    assert arxiv_id("https://arxiv.org/pdf/2210.03629") == "2210.03629"
    assert arxiv_id("2210.03629") == "2210.03629"
    assert arxiv_id("https://example.com/paper") is None


def test_news_digest_topics_and_hide(client, user_client, llm):
    d = client.get("/api/news").json()
    assert d["status"] == "idle" and d["topics"] == news_agent.DEFAULT_TOPICS
    assert client.post("/api/news/refresh", json={"topics": ["nope"]}).status_code == 422
    client.post("/api/news/refresh", json={"days": 14, "topics": ["ai", "speech"]})
    d = _wait(client, "get", "/api/news")
    assert [i["title"] for i in d["items"]] == ["Model X"] and d["dropped"] == 1 and d["days"] == 14
    assert d["topics"] == ["ai", "speech"] and "last 14 days" in llm.last_prompt
    client.post("/api/news/hide", json={"url": "https://ok.example.com/x"})
    assert client.get("/api/news").json()["items"] == []
    assert user_client.get("/api/news").json()["status"] == "idle"  # each account has its own digest


def test_live_headlines_survive_errors(client, monkeypatch):
    async def boom(limit=20):
        raise RuntimeError("offline")
    monkeypatch.setattr("backend.api.news.hacker_news", boom)
    assert client.get("/api/news/live").json() == {"items": [], "error": "Couldn't load live headlines right now."}


def test_paper_summary_flow(client, user_client, llm):
    ref = {"url": "https://arxiv.org/abs/2210.03629v2", "title": "ReAct"}
    d = client.post("/api/papers/summary/lookup", json=ref).json()
    assert d["summary"] is None and d["url"] == "https://arxiv.org/abs/2210.03629"
    rid = d["resource_id"]
    client.post("/api/papers/summary", json={**ref, "context": "Agent loops"})
    d = _wait(client, "post", "/api/papers/summary/lookup", {"resource_id": rid})
    assert d["summary"]["tldr"] == "It reasons and acts." and "Agent loops" in llm.last_prompt
    assert "arxiv.org/html/2210.03629" in llm.last_prompt
    # shared: the other account sees it, but can't replace, edit or delete it
    assert user_client.post("/api/papers/summary/lookup", json={"resource_id": rid}).json()["summary"]["tldr"]
    assert user_client.post("/api/papers/summary", json={"resource_id": rid}).status_code == 403
    assert user_client.delete(f"/api/papers/summary/{rid}").status_code == 403
    edit = {**d["summary"], "resource_id": rid, "tldr": "Edited.", "results": ["a", " "]}
    s = client.put("/api/papers/summary", json=edit).json()["summary"]
    assert s["tldr"] == "Edited." and s["results"] == ["a"] and s["edited"] is True
    assert client.delete(f"/api/papers/summary/{rid}").json() == {"ok": True}
    assert client.post("/api/papers/summary/lookup", json={"resource_id": rid}).json()["summary"] is None
    assert client.post("/api/papers/summary/lookup", json={"url": "https://example.com/x"}).status_code == 422
