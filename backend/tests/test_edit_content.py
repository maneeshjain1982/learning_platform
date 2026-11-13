from backend import career, hindi_voice as hv
from backend.api import bgjobs
from backend.db import session_scope
from backend.models import AcademyQA, User


def _voice(c):
    return c.get("/api/voice/hi").json()


def test_admin_edits_and_deletes_catalog_for_everyone(client, user_client):
    model = hv.MODELS[0]["name"]
    assert user_client.post("/api/content/edit", json={"scope": "voice.hi.models", "key": model,
                                                     "fields": {"notes": "x"}}).status_code == 403
    assert client.post("/api/content/edit", json={"scope": "voice.hi.models", "key": model,
                                                "fields": {"url": "https://evil"}}).status_code == 422
    assert client.post("/api/content/edit", json={"scope": "nope", "key": "k", "fields": {}}).status_code == 404
    client.post("/api/content/edit", json={"scope": "voice.hi.models", "key": model, "fields": {"notes": " Best. "}})
    for c in (client, user_client):
        m = next(m for m in _voice(c)["models"] if m["_key"] == model)
        assert m["notes"] == "Best." and m["_edited"] is True
    paper = hv.PAPERS[0]["id"]
    assert client.post("/api/content/delete", json={"scope": "voice.hi.papers", "key": paper}).json()["for_everyone"]
    for c in (client, user_client):
        d = _voice(c)
        assert paper not in {p["id"] for p in d["papers"]} and d["removed"]["papers"] == 1
    client.post("/api/content/reset", json={"scope": "voice.hi.papers"})
    client.post("/api/content/reset", json={"scope": "voice.hi.models"})
    assert _voice(user_client)["removed"]["papers"] == 0
    assert next(m for m in _voice(client)["models"] if m["_key"] == model)["_edited"] is False


def test_user_hides_only_for_themselves(client, user_client):
    cert = career.CERTS[0]["name"]  # career is admin-only; use a Claude course for the user
    assert user_client.post("/api/content/delete", json={"scope": "career.certs", "key": cert}).status_code == 200
    slug = client.get("/api/claude-academy").json()["courses"][0]["slug"]
    r = user_client.post("/api/content/delete", json={"scope": "claude.courses", "key": slug}).json()
    assert r["for_everyone"] is False
    assert slug not in {c["slug"] for c in user_client.get("/api/claude-academy").json()["courses"]}
    assert slug in {c["slug"] for c in client.get("/api/claude-academy").json()["courses"]}
    user_client.post("/api/content/reset", json={"scope": "claude.courses"})
    assert slug in {c["slug"] for c in user_client.get("/api/claude-academy").json()["courses"]}


def test_lesson_notes_edit_and_delete(client, user_client):
    path = client.get("/api/paths").json()[0]["id"]
    lesson = client.get(f"/api/paths/{path}").json()["module_list"][0]["lessons"][0]["id"]
    d = client.put(f"/api/lessons/{lesson}/content", json={"content_md": "# Mine"}).json()
    assert d["content_md"] == "# Mine" and d["notes_status"] == "ready"
    assert user_client.put(f"/api/lessons/{lesson}/content", json={"content_md": "x"}).status_code == 404
    d = client.delete(f"/api/lessons/{lesson}/content").json()
    assert d["content_md"] is None and d["notes_status"] == "deleted"


def test_qa_marks_per_account_and_admin_edit(client, user_client):
    with session_scope() as s:
        q = AcademyQA(course_slug="hv-eval", lesson_idx=0, lesson_title="t", question="Q?", answer_md="A")
        s.add(q)
        s.flush()
        qid = q.id
    client.patch(f"/api/claude-academy/qa/items/{qid}", json={"status": "known"})
    assert user_client.patch(f"/api/claude-academy/qa/items/{qid}", json={"status": "review"}).json()["status"] == "review"
    mine = lambda c: next(i for i in c.get("/api/claude-academy/qa/hv-eval").json()["items"] if i["id"] == qid)  # noqa: E731
    assert mine(client)["status"] == "known" and mine(user_client)["status"] == "review"
    assert user_client.patch(f"/api/claude-academy/qa/items/{qid}", json={"question": "Hack?"}).status_code == 403
    assert client.patch(f"/api/claude-academy/qa/items/{qid}", json={"question": "Better?"}).json()["question"] == "Better?"
    assert user_client.delete(f"/api/claude-academy/qa/items/{qid}").status_code == 403
    assert client.delete(f"/api/claude-academy/qa/items/{qid}").json() == {"ok": True}


def test_remove_job_item_and_edit_utterance(client, user_client):
    with session_scope() as s:
        user = s.get(User, 1)
        from backend.auth import set_uid
        set_uid(1)
        bgjobs.write(s, "updates", status="ready", items=[{"url": "https://a"}, {"url": "https://b"}])
        bgjobs.write(s, "hv-utterances", status="ready", params={"intent": "SetAlarm"}, items=[
            {"text": "कल 7 बजे alarm", "style": "hinglish", "tone": "casual",
             "slots": [{"name": "time", "value": "7 बजे"}, {"name": "date", "value": "कल"}], "annotated": ""}])
        assert user
    assert client.post("/api/content/job-item/remove", json={"job": "updates", "url": "https://a"}).json()["ok"]
    assert [i["url"] for i in client.get("/api/claude-academy/updates").json()["items"]] == ["https://b"]
    assert client.post("/api/content/job-item/remove", json={"job": "updates", "url": "https://zz"}).status_code == 404
    assert user_client.post("/api/content/job-item/remove", json={"job": "jobs", "url": "x"}).status_code == 403
    d = client.post("/api/voice/hi/utterances/edit", json={"old": "कल 7 बजे alarm", "text": "कल 8 बजे alarm"}).json()
    u = d["items"][0]
    assert u["slots"] == [{"name": "date", "value": "कल"}] and u["annotated"] == "[g:SetAlarm] (कल)[v:date] 8 बजे alarm"
    assert client.post("/api/voice/hi/utterances/edit", json={"old": "कल 8 बजे alarm"}).json()["items"] == []
