import time

import pytest

from backend.agents import career as career_agent
from backend.agents import domains as agent
from backend.agents import papers as papers_agent


async def _state(url):
    return "dead" if "dead.example" in url else "ok"


@pytest.fixture()
def llm(fake_llm, monkeypatch):
    original = fake_llm.ask_json
    seen = []

    async def ask_json(prompt, schema, **kw):
        seen.append((schema.__name__, kw.get("web")))
        if schema is agent.TopicWrite:
            return schema(overview="What it is.", key_points=["one", "two", "three"], why="It matters.", sources=[
                {"title": "Talk", "url": "https://www.youtube.com/watch?v=abcdefghijk", "kind": "video",
                 "access": "free", "summary": "A talk."},
                {"title": "Gone", "url": "https://dead.example.com/x", "kind": "article", "access": "free",
                 "summary": "x"}])
        if schema is agent.SummaryOnly:
            return schema(overview="Short overview.", key_points=["a", "b", "c"], why="Because.")
        if schema is agent.DomainPlan:
            return schema(description="Robots.", sections=[
                {"title": "Basics", "topics": [{"title": "Kinematics", "blurb": "k"}, {"title": "Sensors", "blurb": "s"}]},
                {"title": "Advanced", "topics": [{"title": "SLAM", "blurb": "x"}]}])
        if schema is agent.SourceSummary:
            return schema(tldr="Teaches X.", key_points=["p"], best_for="Engineers.", read_source=True)
        if schema is papers_agent.PaperSummary:
            return schema(tldr="Paper.", problem="p", method="m", results=["r"], limitations=["l"],
                          why_it_matters="w", read_full_text=True)
        if schema is career_agent.ReportedOut:
            return schema(process="Phone screen then onsite.", questions=[
                {"question": "Design a RAG system for Search.", "round": "ml_design", "answer_outline": ["a", "b", "c"],
                 "source_name": "Blog", "url": "https://ok.example.com/q"},
                {"question": "Made up", "answer_outline": ["a"], "source_name": "x", "url": "https://dead.example.com/q"}])
        if schema is agent.BlogFind:
            return schema(posts=[
                {"title": "Deep dive", "url": "https://huggingface.co/blog/deep", "why": "Thorough.", "level": "advanced",
                 "access": "free"},
                {"title": "Gentle intro", "url": "https://medium.com/@a/intro", "why": "Clear diagrams.",
                 "level": "beginner", "read_minutes": 8, "published": "2025-03", "access": "limited"},
                {"title": "Gone", "url": "https://dead.example.com/b", "why": "x", "level": "beginner", "access": "free"}])
        if schema is career_agent.CVProfile:
            assert "@" not in prompt and "98765" not in prompt  # contact details never reach the LLM
            return schema(headline="Senior Speech Engineer", years=11, level="staff", domains=["Voice AI"],
                          skills=["ASR", "PyTorch"], roles=["Staff Speech Engineer"], summary="Built ASR.")
        if schema is career_agent.MatchedSearchOut:
            assert "Staff Speech Engineer" in prompt and "Remote" not in prompt and "hybrid only" in prompt
            job = lambda t, m: {"title": t, "company": "Acme", "location": "Bengaluru, India", "url": f"https://ok.example.com/{m}",  # noqa
                                "summary": "s", "responsibilities": ["r"], "must_have": ["ASR"], "skill_tags": ["ASR"],
                                "match": m, "fits": ["ASR"], "gaps": ["Kubernetes"]}
            return schema(market_summary="Hiring.", trends=["t"], jobs=[job("B", 60), job("A", 90)])
        if schema is career_agent.JobSearchOut:
            assert "Voice AI" in prompt
            return schema(market_summary="Hiring.", trends=["t"], jobs=[])
        return await original(prompt, schema, **kw)

    monkeypatch.setattr(fake_llm, "ask_json", ask_json)
    monkeypatch.setattr("backend.agents.domains.check_url", _state)
    monkeypatch.setattr("backend.agents.career.check_url", _state)
    fake_llm.seen = seen
    return fake_llm


def _wait(fn, done, tries=200):
    for _ in range(tries):
        d = fn()
        if done(d):
            return d
        time.sleep(0.05)
    raise AssertionError("did not finish")


def test_classify():
    c = agent.classify
    assert c("https://www.youtube.com/watch?v=x") == {"site": "YouTube", "kind": "video", "access": "free"}
    assert c("https://www.coursera.org/learn/nlp")["access"] == "login"
    assert c("https://medium.com/@a/post")["access"] == "limited"
    assert c("https://huggingface.co/datasets/ai4bharat/Kathbath")["kind"] == "dataset"
    assert c("https://web.stanford.edu/class/cs224s/")["site"] == "University"
    assert c("https://arxiv.org/abs/2210.03629")["kind"] == "paper"


def test_starting_domains(client, user_client):
    names = [d["name"] for d in client.get("/api/domains").json()]
    assert names[:4] == ["Gen AI", "LLM", "Agentic AI", "Voice AI"]
    voice = client.get("/api/domains/voice-ai").json()
    titles = [s["title"] for s in voice["section_list"]]
    assert "Hindi: research papers" in titles and "English: launch playbook" in titles
    agentic = user_client.get("/api/domains/agentic-ai").json()  # the user account can read
    assert any(s["title"] == "Claude agent builder track" for s in agentic["section_list"])


def test_draft_topic_gets_summary_on_open(client, llm):
    voice = client.get("/api/domains/voice-ai").json()
    papers = next(s for s in voice["section_list"] if s["title"] == "Hindi: research papers")
    tid = papers["topics"][0]["id"]
    t = client.get(f"/api/topics/{tid}").json()
    assert t["domain"]["name"] == "Voice AI" and len(t["source_list"]) >= 3
    assert t["source_list"][0]["kind"] == "paper" and t["source_list"][0]["access"] == "free"
    t = _wait(lambda: client.get(f"/api/topics/{tid}").json(), lambda d: d["status"] == "ready")
    assert t["overview"] == "Short overview." and t["key_points"] == ["a", "b", "c"]
    assert ("SummaryOnly", False) in llm.seen  # enough sources already: no web search


def test_admin_builds_new_domain_and_user_cannot(client, user_client, llm):
    assert user_client.post("/api/domains", json={"name": "Robotics"}).status_code == 403
    d = client.post("/api/domains", json={"name": "Robotics AI", "description": ""}).json()
    assert d["slug"] == "robotics-ai" and d["status"] == "building"
    d = _wait(lambda: client.get("/api/domains/robotics-ai").json(), lambda x: x["status"] != "building")
    assert d["status"] == "ready" and d["description"] == "Robots." and d["topics"] == 3
    tid = d["section_list"][0]["topics"][0]["id"]
    t = client.get(f"/api/topics/{tid}").json()
    assert t["status"] == "ready" and [s["site"] for s in t["source_list"]] == ["YouTube"]  # dead link dropped
    assert client.delete(f"/api/domains/{d['id']}").json() == {"ok": True}
    assert client.get("/api/domains/robotics-ai").status_code == 404


def test_edit_topic_sources_bookmarks_search(client, user_client, llm):
    d = client.post("/api/domains", json={"name": "Quantum", "build": False}).json()
    sec = client.post(f"/api/domains/{d['id']}/sections", json={"title": "Basics"}).json()
    t = client.post(f"/api/sections/{sec['id']}/topics", json={"title": "Qubits explained", "auto": False}).json()
    tid = t["id"]
    t = client.patch(f"/api/topics/{tid}", json={"overview": "Qubits hold superpositions.",
                                                  "key_points": ["Superposition", " ", "Entanglement"]}).json()
    assert t["key_points"] == ["Superposition", "Entanglement"] and t["status"] == "ready"
    assert user_client.patch(f"/api/topics/{tid}", json={"why": "x"}).status_code == 403

    s = client.post(f"/api/topics/{tid}/sources", json={"url": "https://www.coursera.org/learn/quantum"}).json()
    assert s["site"] == "Coursera" and s["access"] == "login"
    s = client.patch(f"/api/sources/{s['id']}", json={"title": "Quantum course", "access": "paid"}).json()
    assert s["title"] == "Quantum course" and s["access"] == "paid"

    # any account can write a missing source summary
    assert user_client.post(f"/api/sources/{s['id']}/summary").status_code == 200
    s = _wait(lambda: client.get(f"/api/topics/{tid}").json()["source_list"][0],
              lambda x: x["summary_status"] != "writing")
    assert s["ai_summary"]["tldr"] == "Teaches X."
    assert user_client.post(f"/api/sources/{s['id']}/summary").status_code == 403  # replacing is admin-only

    assert user_client.put(f"/api/topics/{tid}/bookmark", json={"on": True}).json() == {"bookmarked": True}
    assert [b["id"] for b in user_client.get("/api/topics/bookmarks").json()] == [tid]
    assert client.get("/api/topics/bookmarks").json() == []  # bookmarks are per account

    hits = user_client.get("/api/topics/search", params={"q": "qubits"}).json()
    assert hits[0]["id"] == tid and hits[0]["domain"]["name"] == "Quantum"
    m = client.post("/api/topics/match", json={"terms": ["Entanglement"]}).json()
    assert m["Entanglement"][0]["id"] == tid

    assert client.delete(f"/api/sources/{s['id']}").json() == {"ok": True}
    assert client.delete(f"/api/topics/{tid}").json() == {"ok": True}
    client.delete(f"/api/domains/{d['id']}")


def test_job_search_by_domain_and_faang(client, user_client, llm):
    assert client.post("/api/career/search", json={}).status_code == 422
    client.post("/api/career/search", json={"domain": "Voice AI", "country": "India"})
    d = _wait(lambda: client.get("/api/career/search").json(), lambda x: x["status"] != "running")
    assert d["status"] == "ready" and d["params"]["domain"] == "Voice AI"

    assert client.get("/api/career/faang").json()["companies"][0] == "Google"
    client.post("/api/career/faang/refresh", json={"company": "Google", "domain": "LLM"})
    d = _wait(lambda: client.get("/api/career/faang", params={"company": "Google"}).json(),
              lambda x: x["status"] != "running")
    assert d["process"].startswith("Phone") and [q["question"] for q in d["questions"]] == [
        "Design a RAG system for Search."]
    assert client.get("/api/career/faang").json()["loaded"]["Google"]
    assert user_client.get("/api/career/faang").status_code == 403  # career is admin-only


def test_blog_scout_on_open_and_admin_runs(client, user_client, llm):
    d = client.post("/api/domains", json={"name": "Blogs test", "build": False}).json()
    client.patch(f"/api/domains/{d['id']}", json={"trusted_blogs": [{"name": "AI4Bharat", "url": "https://ai4bharat.iitm.ac.in/blog"}]})
    assert client.get("/api/domains/blogs-test").json()["trusted_blogs"][0]["name"] == "AI4Bharat"
    sec = client.post(f"/api/domains/{d['id']}/sections", json={"title": "S"}).json()
    tid = client.post(f"/api/sections/{sec['id']}/topics", json={"title": "Attention", "auto": False}).json()["id"]
    t = user_client.get(f"/api/topics/{tid}").json()  # first open starts Blog Scout, for any account
    assert t["blog_status"] == "finding"
    t = _wait(lambda: client.get(f"/api/topics/{tid}").json(), lambda x: x["blog_status"] != "finding")
    blogs = [s for s in t["source_list"] if s["blog"]]
    assert [b["title"] for b in blogs] == ["Gentle intro", "Deep dive"]  # beginner first, dead link dropped
    assert blogs[0]["post_level"] == "beginner" and blogs[0]["read_minutes"] == 8 and blogs[0]["access"] == "limited"
    assert blogs[1]["kind"] == "article" and blogs[1]["site"] == "Hugging Face"
    assert user_client.post(f"/api/topics/{tid}/blogs").status_code == 403
    assert client.post(f"/api/topics/{tid}/blogs").status_code == 200
    _wait(lambda: client.get(f"/api/topics/{tid}").json(), lambda x: x["blog_status"] != "finding")
    assert len(client.get(f"/api/topics/{tid}").json()["source_list"]) == 2  # no duplicates
    assert client.post(f"/api/domains/{d['id']}/blogs").json() == {"started": 0}
    client.delete(f"/api/domains/{d['id']}")


def test_cv_profile_and_matched_job_search(client, user_client, llm):
    import base64
    from backend import cv
    text = "Ravi Kumar\nravi.kumar@example.com | +91 98765 43210 | linkedin.com/in/ravi\n" \
           "Staff Speech Engineer, 2014 - 2025. Built Hindi ASR used by 10M users with PyTorch and Kaldi.\n" * 2
    clean = cv.strip_contacts(text)
    assert "Ravi" not in clean.split("\n")[0] and "@" not in clean and "98765" not in clean and "2014 - 2025" in clean
    with pytest.raises(cv.CVError):
        cv.extract_text("cv.exe", b"x" * 100)

    assert client.post("/api/career/search", json={"use_profile": True}).status_code == 422  # no CV yet
    b64 = base64.b64encode(text.encode()).decode()
    p = client.post("/api/career/profile/cv", json={"filename": "cv.txt", "content_b64": b64}).json()["profile"]
    assert p["years"] == 11 and p["cv_name"] == "cv.txt" and "@" not in p["cv_text"]
    p = client.put("/api/career/profile", json={"skills": ["ASR", " ", "Whisper"]}).json()["profile"]
    assert p["skills"] == ["ASR", "Whisper"] and p["headline"] == "Senior Speech Engineer"
    assert user_client.get("/api/career/profile").status_code == 403

    client.post("/api/career/search", json={"use_profile": True, "work_mode": "hybrid", "country": "India"})
    d = _wait(lambda: client.get("/api/career/search").json(), lambda x: x["status"] != "running")
    assert d["status"] == "ready" and d["matched"] and [j["match"] for j in d["jobs"]] == [90, 60]
    assert d["jobs"][0]["gaps"] == ["Kubernetes"] and d["params"]["work_mode"] == "hybrid"
    assert client.delete("/api/career/profile").json() == {"profile": None}
