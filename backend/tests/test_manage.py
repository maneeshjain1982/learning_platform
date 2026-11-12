from backend.api.manage import detect, normalize_url


def test_links_crud_and_home(client):
    r = client.post("/api/links", json={"url": "www.udemy.com/course/llm-engineering/", "title": "LLM Engineering",
                                        "note": "Bought this one"})
    assert r.status_code == 200, r.text
    link = r.json()
    assert link["provider"] == "udemy" and link["kind"] == "course"
    assert link["url"].startswith("https://")

    home = client.get("/api/home").json()
    assert [l["title"] for l in home["my_links"]] == ["LLM Engineering"]

    r = client.patch(f"/api/links/{link['id']}", json={"title": "LLM Eng (Udemy)", "show_on_home": False, "status": "doing"})
    assert r.json()["title"] == "LLM Eng (Udemy)" and r.json()["status"] == "doing"
    assert client.get("/api/home").json()["my_links"] == []

    assert client.delete(f"/api/links/{link['id']}").status_code == 200
    assert client.get("/api/links").json() == []


def test_link_tied_to_path_shows_only_on_that_path(client):
    paths = client.get("/api/paths").json()
    a, b = paths[0]["id"], paths[1]["id"]
    client.post("/api/links", json={"url": "https://docs.example.com/agents", "title": "Agent docs", "path_id": a})
    assert [l["title"] for l in client.get(f"/api/home?path_id={a}").json()["my_links"]] == ["Agent docs"]
    assert client.get(f"/api/home?path_id={b}").json()["my_links"] == []
    assert client.get(f"/api/links?path_id={a}").json()[0]["path_title"] == paths[0]["title"]


def test_bad_url_rejected(client):
    assert client.post("/api/links", json={"url": "not a url", "title": "x"}).status_code == 422


def test_detect_and_normalize():
    assert detect("https://www.coursera.org/learn/x") == ("coursera", "course")
    assert detect("https://youtu.be/abc") == ("youtube", "video")
    assert detect("https://arxiv.org/abs/2210.03629") == ("arxiv", "paper")
    assert detect("https://blog.example.com/post") == ("blog.example.com", "link")
    assert normalize_url("example.com/a") == "https://example.com/a"


def test_create_and_edit_own_course(client):
    r = client.post("/api/paths", json={"title": "My Kubernetes course", "summary": "Notes from work",
                                        "level": "beginner", "modules": ["Pods", "Services"]})
    pid = r.json()["id"]
    path = client.get(f"/api/paths/{pid}").json()
    assert [m["title"] for m in path["module_list"]] == ["Pods", "Services"]
    m1, m2 = path["module_list"][0]["id"], path["module_list"][1]["id"]

    l1 = client.post(f"/api/modules/{m1}/lessons", json={"title": "What is a pod", "est_minutes": 15}).json()
    l2 = client.post(f"/api/modules/{m1}/lessons", json={"title": "Pod lifecycle"}).json()
    assert (l1["idx"], l2["idx"]) == (0, 1)

    client.patch(f"/api/lessons/{l2['id']}", json={"title": "Pod lifecycle & probes", "objectives": ["Explain probes", " "]})
    client.post(f"/api/lessons/{l2['id']}/move", json={"direction": "up"})
    client.patch(f"/api/modules/{m2}", json={"title": "Services & networking"})
    client.post(f"/api/modules/{m2}/move", json={"direction": "up"})
    client.patch(f"/api/paths/{pid}", json={"title": "Kubernetes basics", "hours_per_week": 3})

    path = client.get(f"/api/paths/{pid}").json()
    assert path["title"] == "Kubernetes basics" and path["hours_per_week"] == 3
    assert [m["title"] for m in path["module_list"]] == ["Services & networking", "Pods"]
    pods = path["module_list"][1]
    assert [l["title"] for l in pods["lessons"]] == ["Pod lifecycle & probes", "What is a pod"]
    assert client.get(f"/api/lessons/{l2['id']}").json()["objectives"] == ["Explain probes"]

    client.delete(f"/api/lessons/{l2['id']}")
    pods = client.get(f"/api/paths/{pid}").json()["module_list"][1]
    assert [(l["idx"], l["title"]) for l in pods["lessons"]] == [(0, "What is a pod")]
    client.delete(f"/api/modules/{m2}")
    path = client.get(f"/api/paths/{pid}").json()
    assert [(m["idx"], m["title"]) for m in path["module_list"]] == [(0, "Pods")]


def test_hide_reorder_and_delete_starter_path(client):
    from backend.db import session_scope
    from backend.seed import seed_structure

    paths = client.get("/api/paths").json()
    first, second = paths[0], paths[1]

    client.patch(f"/api/paths/{first['id']}", json={"show_on_home": False})
    home = client.get(f"/api/home?path_id={first['id']}").json()
    assert first["id"] not in [p["id"] for p in home["paths"]]
    assert home["active"]["id"] != first["id"] and home["hidden_paths"] == 1
    client.patch(f"/api/paths/{first['id']}", json={"show_on_home": True})

    client.post(f"/api/paths/{second['id']}/move", json={"direction": "up"})
    assert client.get("/api/paths").json()[0]["id"] == second["id"]

    starter = next(p for p in paths if p["is_seed"])
    assert client.delete(f"/api/paths/{starter['id']}").status_code == 200
    with session_scope() as db:
        assert seed_structure(db) == []  # a deleted starter path is not recreated on restart
    assert starter["title"] not in [p["title"] for p in client.get("/api/paths").json()]
    # a deleted path id remembered by the browser falls back instead of failing
    assert client.get(f"/api/home?path_id={starter['id']}").status_code == 200

    assert client.post("/api/paths/restore-starters").json()["restored"] == 1
    assert starter["title"] in [p["title"] for p in client.get("/api/paths").json()]
