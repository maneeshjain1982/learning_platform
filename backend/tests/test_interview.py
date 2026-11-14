import time
from datetime import date, timedelta


def wait_run(client, run_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/agent-runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def make_prep(client, **kw):
    body = {"role_title": "Agentic AI Architect", "seniority": "principal", "questions_per_area": 3,
            "interview_date": (date.today() + timedelta(days=20)).isoformat(), "hours_per_week": 6, "build_plan": True, **kw}
    r = client.post("/api/interviews", json=body)
    assert r.status_code == 200, r.text
    run = wait_run(client, r.json()["run_id"])
    assert run["status"] == "done", run
    return r.json()["id"], run


def test_build_without_jd(client, fake_llm):
    pid, run = make_prep(client)
    steps = {s["agent"]: s["status"] for s in run["steps"]}
    assert steps["JD Analyst"] == "skipped"
    assert all(v == "done" for k, v in steps.items() if k != "JD Analyst"), steps
    assert fake_llm.web_flags[-1] is True  # role research used web search

    prep = client.get(f"/api/interviews/{pid}").json()
    assert prep["status"] == "ready" and prep["stats"]["days_left"] == 20
    assert [s["url"] for s in prep["research"]["sources"]] == ["https://ok.example.com/a"]  # dead link dropped
    assert {s["name"] for s in prep["skills"]} == {"MCP", "A2A", "LangGraph"}
    assert prep["areas"] == ["Tools & protocols", "Frameworks"]
    assert prep["path"]["kind"] == "interview" and prep["path"]["weeks"] == 3
    assert prep["coach_note"]

    qs = client.get(f"/api/interviews/{pid}/questions").json()
    assert len(qs) == 6  # 3 per area x 2 areas
    refs = qs[0]["references"]
    # made-up arXiv id and dead web link removed; arXiv title replaced with the real one
    assert [r["url"] for r in refs] == ["https://arxiv.org/abs/2210.03629", "https://ok.example.com/spec"]
    assert refs[0]["title"].startswith("ReAct: Synergizing") and refs[0]["verified"]
    assert qs[0]["skill_name"] == "MCP"

    # the prep plan is a normal learning path, tagged as interview prep
    paths = client.get("/api/paths").json()
    assert any(p["id"] == prep["path_id"] and p["kind"] == "interview" for p in paths)


def test_jd_ratings_mock_and_generate(client, fake_llm):
    pid, run = make_prep(client, jd_text="We need an architect who knows MCP and LangGraph deeply.",
                         question_types=["design"], web_research=False)
    assert {s["agent"]: s["status"] for s in run["steps"]}["JD Analyst"] == "done"
    assert fake_llm.web_flags[-1] is False
    prep = client.get(f"/api/interviews/{pid}").json()
    assert prep["jd_analysis"]["required_skills"] == ["MCP", "LangGraph"]
    qs = client.get(f"/api/interviews/{pid}/questions").json()
    assert qs and all(q["qtype"] == "design" for q in qs)  # only allowed types kept

    # self-ratings raise readiness
    before = prep["stats"]["readiness"]
    for s in prep["skills"]:
        client.patch(f"/api/interview-skills/{s['id']}", json={"self_rating": 4})
    after = client.get(f"/api/interviews/{pid}").json()["stats"]
    assert after["readiness"] > before and after["rated_skills"] == 3

    # mock interview: next question hides the answer; grading is clamped to 1-5 and marks it confident
    nxt = client.post(f"/api/interviews/{pid}/mock/next", json={}).json()
    assert "answer_md" not in nxt
    res = client.post(f"/api/interview-questions/{nxt['id']}/attempts",
                      json={"answer": "I would design it with an orchestrator and MCP tools."}).json()
    assert res["score"] == 5 and res["question"]["status"] == "confident"
    assert client.get(f"/api/interviews/{pid}/attempts").json()[0]["question_text"] == nxt["question"]
    assert client.get(f"/api/interviews/{pid}").json()["stats"]["parts"]["practice"] > 0

    # generate more for one area
    n_before = len(client.get(f"/api/interviews/{pid}/questions").json())
    r = client.post(f"/api/interviews/{pid}/questions/generate", json={"area": "Frameworks", "count": 2})
    assert wait_run(client, r.json()["run_id"])["status"] == "done"
    assert len(client.get(f"/api/interviews/{pid}/questions").json()) > n_before  # non-design ones filtered

    # your own question, edit, filter, delete
    own = client.post(f"/api/interviews/{pid}/questions", json={"question": "Why not just use one agent?"}).json()
    assert own["source"] == "user" and own["area"] == "My questions"
    client.patch(f"/api/interview-questions/{own['id']}", json={"status": "needs_work", "answer_md": "Because…"})
    assert [q["id"] for q in client.get(f"/api/interviews/{pid}/questions?status=needs_work").json()] == [own["id"]]
    client.delete(f"/api/interview-questions/{own['id']}")


def test_rebuild_keeps_practised_and_own_questions(client, fake_llm):
    pid, _ = make_prep(client)
    qs = client.get(f"/api/interviews/{pid}/questions").json()
    client.post(f"/api/interview-questions/{qs[0]['id']}/attempts", json={"answer": "A long enough answer."})
    own = client.post(f"/api/interviews/{pid}/questions", json={"question": "My own question here?"}).json()
    skill = client.get(f"/api/interviews/{pid}").json()["skills"][0]
    client.patch(f"/api/interview-skills/{skill['id']}", json={"self_rating": 2})
    old_path = client.get(f"/api/interviews/{pid}").json()["path_id"]

    r = client.post(f"/api/interviews/{pid}/rebuild", json={"replace_plan": True, "replace_questions": True})
    assert wait_run(client, r.json()["run_id"])["status"] == "done"
    prep = client.get(f"/api/interviews/{pid}").json()
    ids = {q["id"] for q in client.get(f"/api/interviews/{pid}/questions").json()}
    assert qs[0]["id"] in ids and own["id"] in ids and qs[1]["id"] not in ids
    assert next(s for s in prep["skills"] if s["name"] == skill["name"])["self_rating"] == 2  # rating kept
    assert prep["path_id"] != old_path
    assert client.get(f"/api/paths/{old_path}").status_code == 404

    # questions-only rebuild skips the plan steps
    r = client.post(f"/api/interviews/{pid}/rebuild", json={"replace_plan": False, "replace_questions": False})
    run = wait_run(client, r.json()["run_id"])
    assert "Prep Planner" not in [s["agent"] for s in run["steps"]]

    assert client.delete(f"/api/interviews/{pid}").status_code == 200
    assert client.get(f"/api/paths/{prep['path_id']}").status_code == 404


def test_prep_without_study_path(client, fake_llm):
    pid, run = make_prep(client, build_plan=False)
    assert "plan" not in [s["agent"] for s in run["steps"]]
    p = client.get(f"/api/interviews/{pid}").json()
    assert p["path"] is None and p["skills"] and p["stats"]
