import re

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "adminpass123")
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "t.sqlite"), "SECRET_KEY": "t"})
    return app.test_client()


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)


def login(client, user="admin", pw="adminpass123"):
    return client.post("/login", data={"username": user, "password": pw, "_csrf": token(client)})


def test_requires_login(client):
    assert client.get("/").status_code == 302


def test_bad_login(client):
    assert "غير صحيحة" in login(client, pw="x").get_data(as_text=True)


def test_csrf_enforced(client):
    assert client.post("/login", data={"username": "admin", "password": "adminpass123"}).status_code == 400


def test_customer_flow(client):
    assert login(client).status_code == 302
    client.post("/customers/new", data={"name": "أحمد", "phone": "123", "_csrf": token(client, "/customers/new")})
    assert "أحمد" in client.get("/customers").get_data(as_text=True)


def test_staff_cannot_manage_users(client):
    login(client)
    client.post("/users", data={"username": "emp", "password": "password1", "role": "staff",
                                "_csrf": token(client, "/users")})
    client.post("/logout", data={"_csrf": token(client, "/users")})
    login(client, "emp", "password1")
    assert client.get("/users").status_code == 403
