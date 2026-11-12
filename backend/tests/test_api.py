import time

from backend.llm import inline_schema
from backend.agents.schemas import CurriculumOut
from backend.providers import parse_arxiv, search_links, youtube_id


def wait_run(client, run_id, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = client.get(f"/api/agent-runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_seed_paths_exist(client):
    paths = client.get("/api/paths").json()
    titles = [p["title"] for p in paths]
    assert {"Agentic AI", "LLM Fundamentals", "Agentic Harness"} <= set(titles)
    agentic = next(p for p in paths if p["title"] == "Agentic AI")
    assert agentic["lessons"] == 22 and agentic["done"] == 0


def test_home_and_progress(client):
    home = client.get("/api/home").json()
    active = home["active"]
    assert active["continue"]["lesson_id"]
    first = active["continue"]["lesson_id"]
    assert len(active["course_links"]) == 4  # 2 queries x (coursera, udemy)
    client.post(f"/api/lessons/{first}/progress", json={"status": "done"})
    home2 = client.get(f"/api/home?path_id={active['id']}").json()["active"]
    assert home2["continue"]["lesson_id"] != first
    assert home2["done"] == 1
    assert home2["week"]["lessons_done"] >= 1
    # opening a finished lesson does not un-finish it
    client.post(f"/api/lessons/{first}/progress", json={"status": "doing"})
    assert client.get(f"/api/lessons/{first}").json()["status"] == "done"


def test_build_path_end_to_end(client, fake_llm):
    r = client.post("/api/requirements", json={"raw_text": "I want to learn software testing well.",
                                               "level": "beginner", "hours_per_week": 3, "weeks": 2})
    run = wait_run(client, r.json()["run_id"])
    assert run["status"] == "done", run
    assert [s["status"] for s in run["steps"]] == ["done"] * 6
    path = client.get(f"/api/paths/{run['path_id']}").json()
    assert path["title"] == "Test Topic" and path["status"] == "ready"
    assert len(path["module_list"]) == 2
    a1 = path["module_list"][0]["lessons"][0]
    assert a1["videos"] == 1  # non-YouTube URL was dropped by verification
    assert a1["papers"] == 1
    # the verified known paper (ReAct) is the curator's first candidate; the made-up id was dropped
    lesson = client.get(f"/api/lessons/{a1['id']}").json()
    assert [r["external_id"] for r in lesson["resources"] if r["kind"] == "paper"] == ["2210.03629"]


def test_lesson_notes_and_chat(client):
    path = client.get("/api/paths").json()[0]
    lesson_id = path["current_lesson_id"]
    assert client.post(f"/api/lessons/{lesson_id}/notes").json()["notes_status"] == "writing"
    for _ in range(100):
        lesson = client.get(f"/api/lessons/{lesson_id}").json()
        if lesson["notes_status"] != "writing":
            break
        time.sleep(0.05)
    assert lesson["notes_status"] == "ready" and lesson["content_md"].startswith("## Overview")

    r = client.post("/api/chat", json={"message": "Why does this matter?", "lesson_id": lesson_id}).json()
    assert r["reply"]["role"] == "assistant"
    assert set(r["reply"]["meta"]["context"]) == {"lesson", "level", "path"}
    r2 = client.post("/api/chat", json={"message": "And then?", "session_id": r["session_id"],
                                        "context": {"lesson": False, "level": True, "path": True}}).json()
    assert "lesson" not in r2["reply"]["meta"]["context"]
    assert len(client.get(f"/api/chat/{r['session_id']}").json()["messages"]) == 4
    saved = client.post(f"/api/chat/messages/{r['reply']['id']}/save-to-notes").json()
    assert "Why does this matter?" in saved["user_notes"]


def test_search_save_and_attach(client):
    papers = client.get("/api/search/papers", params={"q": "tool use"}).json()
    assert papers and papers[0]["kind"] == "paper"
    videos = client.post("/api/search/videos", json={"q": "tool use"}).json()
    assert videos[0]["external_id"] == "bbbbbbbbbbb"
    rid = videos[0]["id"]
    assert client.post(f"/api/resources/{rid}/save").json()["saved"]
    assert any(s["id"] == rid for s in client.get("/api/saved").json())
    lesson_id = client.get("/api/paths").json()[1]["current_lesson_id"]
    client.post(f"/api/lessons/{lesson_id}/resources", json={"resource_id": rid})
    assert any(r["id"] == rid for r in client.get(f"/api/lessons/{lesson_id}").json()["resources"])


def test_unknown_api_is_404(client):
    assert client.get("/api/nope").status_code == 404


def test_youtube_id_parsing():
    assert youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10") == "dQw4w9WgXcQ"
    assert youtube_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert youtube_id("https://example.com/watch?v=dQw4w9WgXcQ") is None
    assert youtube_id("https://www.youtube.com/watch?v=short") is None


def test_inline_schema_has_no_refs():
    s = inline_schema(CurriculumOut.model_json_schema())
    assert "$ref" not in str(s) and "$defs" not in s
    assert s["properties"]["modules"]["items"]["properties"]["lessons"]["items"]["type"] == "object"


def test_search_links_encode_query():
    links = {l["source"]: l["url"] for l in search_links("tool use & agents")}
    assert links["udemy"] == "https://www.udemy.com/courses/search/?q=tool+use+%26+agents"


def test_parse_arxiv():
    xml = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1706.03762v7</id>
    <published>2017-06-12T17:57:34Z</published><title>Attention Is All
    You Need</title><summary>The dominant ...</summary><author><name>Ashish Vaswani</name></author></entry></feed>"""
    [c] = parse_arxiv(xml)
    assert c.external_id == "1706.03762" and c.title == "Attention Is All You Need" and c.year == 2017
