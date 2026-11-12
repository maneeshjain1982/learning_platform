from backend import claude_academy as ca


def test_catalog_lists_agent_track_in_order(client):
    d = client.get("/api/claude-academy").json()
    assert d["base_url"] == "https://academy.claude.com"
    track = sorted((c for c in d["courses"] if c["group"] == "agents"), key=lambda c: c["order"])
    assert [c["order"] for c in track] == list(range(1, len(track) + 1))
    assert track[0]["slug"] == "claude-platform-101"
    assert all(c["url"].startswith("https://academy.claude.com/courses/") for c in d["courses"])
    assert all(c["status"] == "todo" for c in d["courses"])
    assert d["path_id"] is None
    # every agent-track course has its full lesson outline
    for c in ca.AGENT_TRACK:
        assert sum(len(ls) for _, ls in c["outline"]) == c["lessons"], c["slug"]


def test_course_status_round_trip(client):
    assert client.put("/api/claude-academy/courses/claude-code-101/status", json={"status": "done"}).status_code == 200
    d = client.get("/api/claude-academy").json()
    assert next(c for c in d["courses"] if c["slug"] == "claude-code-101")["status"] == "done"
    client.put("/api/claude-academy/courses/claude-code-101/status", json={"status": "todo"})
    assert client.put("/api/claude-academy/courses/nope/status", json={"status": "done"}).status_code == 404
    assert client.put("/api/claude-academy/courses/claude-101/status", json={"status": "bad"}).status_code == 422


def test_track_becomes_a_study_path(client):
    r = client.post("/api/claude-academy/path").json()
    assert r["created"] is True
    assert client.post("/api/claude-academy/path").json() == {"path_id": r["path_id"], "created": False}
    path = client.get(f"/api/paths/{r['path_id']}").json()
    assert [m["title"] for m in path["module_list"]] == [c["title"] for c in ca.AGENT_TRACK]
    first = path["module_list"][0]["lessons"][0]
    lesson = client.get(f"/api/lessons/{first['id']}").json()
    assert lesson["resources"][0]["source"] == "claude_academy"

    client.post(f"/api/lessons/{first['id']}/progress", json={"status": "done"})
    d = client.get("/api/claude-academy").json()
    assert d["path_id"] == r["path_id"]
    p101 = next(c for c in d["courses"] if c["slug"] == "claude-platform-101")
    assert p101["path_progress"]["done"] == 1 and p101["path_progress"]["total"] == 13


def test_updates_refresh(client, fake_llm, monkeypatch):
    from backend.agents import updates as upd

    async def fake_ask_json(prompt, schema, **kw):
        assert schema is upd.UpdatesOut and kw["web"] is True and "Claude Platform 101" in prompt
        item = lambda t, u, d: {"title": t, "date": d, "category": "Models & API", "summary": "s",  # noqa: E731
                                "why_it_matters": "w", "url": u}
        return upd.UpdatesOut(headline="Big week.", items=[
            item("Old", "https://ok.example.com/a", "2026-10-01"),
            item("Newer", "https://ok.example.com/b", "2026-11-01"),
            item("Gone", "https://dead.example.com/x", "2026-11-02")])

    monkeypatch.setattr(fake_llm, "ask_json", fake_ask_json, raising=False)
    monkeypatch.setattr(upd, "check_url", lambda u: _state(u))
    assert client.get("/api/claude-academy/updates").json()["status"] == "idle"
    r = client.post("/api/claude-academy/updates/refresh", json={"days": 30})
    assert r.json()["status"] == "running"
    d = client.get("/api/claude-academy/updates").json()
    for _ in range(50):
        if d["status"] != "running":
            break
        import time; time.sleep(0.05)  # noqa: E702
        d = client.get("/api/claude-academy/updates").json()
    assert d["status"] == "ready", d
    assert [i["title"] for i in d["items"]] == ["Newer", "Old"]  # dead link dropped, newest first
    assert d["dropped"] == 1 and d["headline"] == "Big week." and d["days"] == 30


async def _state(url):
    return "dead" if "dead.example" in url else "ok"
