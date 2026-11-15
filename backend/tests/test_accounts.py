from fastapi.testclient import TestClient

from backend.main import app


def sign_in(username, password):
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    return c, r


def test_only_admin_manages_accounts(client, user_client):
    assert user_client.get("/api/accounts").status_code == 403
    assert user_client.post("/api/accounts", json={"username": "sneaky", "password": "pass1"}).status_code == 403
    names = [a["username"] for a in client.get("/api/accounts").json()]
    assert {"admin", "user"} <= set(names)
    assert next(a for a in client.get("/api/accounts").json() if a["username"] == "admin")["is_you"]


def test_create_sign_in_and_starter_paths(client):
    r = client.post("/api/accounts", json={"username": "Priya.K", "name": "Priya", "password": "secret1"})
    assert r.status_code == 200, r.text
    acc = r.json()
    assert acc["username"] == "priya.k" and acc["role"] == "user" and not acc["default_password"]

    priya, login = sign_in("priya.k", "secret1")
    assert login.status_code == 200 and login.json()["name"] == "Priya"
    titles = {p["title"] for p in priya.get("/api/paths").json()}
    assert {"Agentic AI", "LLM Fundamentals", "Agentic Harness"} <= titles  # own starter paths
    assert not {p["id"] for p in priya.get("/api/paths").json()} & {p["id"] for p in client.get("/api/paths").json()}
    assert priya.get("/api/career/jobs").status_code == 403  # plain user account

    # duplicates and bad usernames are refused
    assert client.post("/api/accounts", json={"username": "PRIYA.K", "password": "xxxx"}).status_code == 409
    assert client.post("/api/accounts", json={"username": "a b", "password": "xxxx"}).status_code == 422
    assert client.post("/api/accounts", json={"username": "shorty", "password": "abc"}).status_code == 422


def test_reset_password_role_and_delete(client):
    acc = client.post("/api/accounts", json={"username": "ravi", "password": "first1"}).json()
    ravi, _ = sign_in("ravi", "first1")
    ravi.post("/api/links", json={"url": "https://example.com/a", "title": "A"})

    # reset password: old one stops working and existing sessions are signed out
    assert client.patch(f"/api/accounts/{acc['id']}", json={"password": "second2"}).status_code == 200
    assert ravi.get("/api/auth/me").status_code == 401
    assert sign_in("ravi", "first1")[1].status_code == 401
    ravi, r = sign_in("ravi", "second2")
    assert r.status_code == 200

    # promote to admin: Career opens up
    client.patch(f"/api/accounts/{acc['id']}", json={"role": "admin"})
    assert ravi.get("/api/career/jobs").status_code != 403

    # delete: account and its data are gone
    assert client.delete(f"/api/accounts/{acc['id']}").status_code == 200
    assert sign_in("ravi", "second2")[1].status_code == 401
    assert "ravi" not in [a["username"] for a in client.get("/api/accounts").json()]


def test_admin_safety_rules(client):
    me = client.get("/api/auth/me").json()
    assert client.delete(f"/api/accounts/{me['id']}").status_code == 409  # can't delete yourself
    admins = [a for a in client.get("/api/accounts").json() if a["role"] == "admin"]
    if len(admins) == 1:
        assert client.patch(f"/api/accounts/{me['id']}", json={"role": "user"}).status_code == 409  # last admin stays
