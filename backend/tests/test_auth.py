from fastapi.testclient import TestClient

from backend.main import app


def test_api_needs_sign_in(client):
    anon = TestClient(app)
    assert anon.get("/api/home").status_code == 401
    assert anon.get("/api/health").status_code == 200
    assert anon.post("/api/auth/login", json={"username": "admin", "password": "nope"}).status_code == 401
    assert anon.get("/api/auth/me").status_code == 401


def test_me_and_roles(client, user_client):
    me = client.get("/api/auth/me").json()
    assert me["username"] == "admin" and me["is_admin"] and me["default_password"]
    assert user_client.get("/api/auth/me").json()["role"] == "user"
    for url in ("/api/career/certifications", "/api/interviews", "/api/career/jobs"):
        assert user_client.get(url).status_code == 403, url
        assert client.get(url).status_code != 403, url


def test_each_account_has_its_own_paths(client, user_client):
    admin_paths = {p["id"] for p in client.get("/api/paths").json()}
    user_paths = {p["id"] for p in user_client.get("/api/paths").json()}
    assert user_paths and admin_paths and not admin_paths & user_paths  # both have starter paths, not shared
    other = next(iter(admin_paths))
    assert user_client.get(f"/api/paths/{other}").status_code == 404
    assert user_client.delete(f"/api/paths/{other}").status_code == 404
    pid = user_client.post("/api/paths", json={"title": "Mine", "modules": ["One"]}).json()["id"]
    assert pid not in {p["id"] for p in client.get("/api/paths").json()}
    assert client.get("/api/home").json()["paths"] != user_client.get("/api/home").json()["paths"]


def test_profile_and_links_are_per_account(client, user_client):
    user_client.put("/api/profile", json={"name": "Asha"})
    assert client.get("/api/profile").json()["name"] != "Asha"
    user_client.post("/api/links", json={"url": "https://example.com/only-user", "title": "U"})
    assert all(l["url"] != "https://example.com/only-user" for l in client.get("/api/links").json())


def test_change_password_and_logout(client):
    c = TestClient(app)
    c.post("/api/auth/login", json={"username": "user", "password": "user"})
    assert c.post("/api/auth/password", json={"current": "bad", "new": "secret1"}).status_code == 400
    assert c.post("/api/auth/password", json={"current": "user", "new": "secret1"}).json()["default_password"] is False
    c.post("/api/auth/logout")
    assert c.get("/api/home").status_code == 401
    assert c.post("/api/auth/login", json={"username": "user", "password": "secret1"}).status_code == 200
    c.post("/api/auth/password", json={"current": "secret1", "new": "user"})  # restore for other tests
