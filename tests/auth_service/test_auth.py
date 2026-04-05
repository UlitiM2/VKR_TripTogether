"""Тесты auth-service: регистрация, логин, профиль, обновление."""
import pytest
from fastapi.testclient import TestClient

import main  # type: ignore
from security import get_password_hash  # type: ignore


def test_auth_root(client: TestClient):
  r = client.get("/")
  assert r.status_code == 200
  data = r.json()
  assert data.get("service") == "Auth Service"
  assert "register" in data.get("endpoints", {})
  assert "login" in data.get("endpoints", {})
  assert "forgot_password" in data.get("endpoints", {})
  assert "change_password" in data.get("endpoints", {})


def test_auth_health(client: TestClient):
  r = client.get("/health")
  assert r.status_code == 200
  assert r.json().get("status") == "healthy"


def test_register_and_login(client: TestClient):
  payload = {
    "email": "user1@example.com",
    "username": "user1",
    "full_name": "Имя Фамилия",
    "password": "secret123",
  }
  r = client.post("/auth/register", json=payload)
  assert r.status_code == 201
  data = r.json()
  assert data["email"] == payload["email"]
  assert data["username"] == payload["username"]

  form = {"username": payload["email"], "password": payload["password"]}
  r2 = client.post("/auth/login", data=form)
  assert r2.status_code == 200
  token = r2.json().get("access_token")
  assert token


def test_login_email_case_insensitive(client: TestClient):
  payload = {
    "email": "mixedcase@example.com",
    "username": "mixeduser",
    "full_name": "Имя Фамилия",
    "password": "secret123",
  }
  assert client.post("/auth/register", json=payload).status_code == 201
  r = client.post(
    "/auth/login",
    data={"username": "MixedCase@Example.COM", "password": payload["password"]},
  )
  assert r.status_code == 200
  assert r.json().get("access_token")


def test_register_duplicate_email_case_insensitive(client: TestClient):
  payload = {
    "email": "dupcase@example.com",
    "username": "userdupc1",
    "full_name": "Имя Фамилия",
    "password": "secret123",
  }
  r1 = client.post("/auth/register", json=payload)
  assert r1.status_code == 201
  r2 = client.post(
    "/auth/register",
    json={
      "email": "DUPCASE@EXAMPLE.COM",
      "username": "userdupc2",
      "full_name": "Имя Фамилия",
      "password": "secret456",
    },
  )
  assert r2.status_code == 400


def test_register_duplicate_email(client: TestClient):
  payload = {
    "email": "dup@example.com",
    "username": "userdup1",
    "full_name": "Имя Фамилия",
    "password": "secret123",
  }
  r1 = client.post("/auth/register", json=payload)
  assert r1.status_code == 201

  payload2 = {
    "email": "dup@example.com",
    "username": "userdup2",
    "full_name": "Имя Фамилия",
    "password": "secret456",
  }
  r2 = client.post("/auth/register", json=payload2)
  assert r2.status_code == 400


def test_login_wrong_password(client: TestClient, create_user):
  hashed = get_password_hash("correct-pass")
  u = create_user("wrongpass@example.com", "wronguser", "Имя", hashed)

  r = client.post("/auth/login", data={"username": u.email, "password": "bad"})
  assert r.status_code == 401


def test_update_me_full_name_and_avatar(client: TestClient):
  payload = {
    "email": "me@example.com",
    "username": "meuser",
    "full_name": "Имя Фамилия",
    "password": "pass12345",
  }
  r = client.post("/auth/register", json=payload)
  assert r.status_code == 201

  login_r = client.post("/auth/login", data={"username": payload["email"], "password": payload["password"]})
  token = login_r.json()["access_token"]
  headers = {"Authorization": f"Bearer {token}"}

  patch_r = client.patch(
    "/auth/me",
    json={"full_name": "Нове Имя", "avatar_url": "https://example.com/avatar.png"},
    headers=headers,
  )
  assert patch_r.status_code == 200
  data = patch_r.json()
  assert data["full_name"] == "Нове Имя"
  assert data["avatar_url"] == "https://example.com/avatar.png"


def test_update_me_invalid_full_name(client: TestClient):
  payload = {
    "email": "badname@example.com",
    "username": "badname",
    "full_name": "Имя Фамилия",
    "password": "pass12345",
  }
  r = client.post("/auth/register", json=payload)
  assert r.status_code == 201
  login_r = client.post("/auth/login", data={"username": payload["email"], "password": payload["password"]})
  token = login_r.json()["access_token"]
  headers = {"Authorization": f"Bearer {token}"}

  patch_r = client.patch("/auth/me", json={"full_name": "Имя 123"}, headers=headers)
  assert patch_r.status_code == 400
  assert patch_r.json().get("detail") == "Full name must contain only letters"


def test_change_password_success(client: TestClient):
  payload = {
    "email": "chgpwd@example.com",
    "username": "chgpwd",
    "full_name": "Имя Фамилия",
    "password": "oldpass12",
  }
  assert client.post("/auth/register", json=payload).status_code == 201
  login_r = client.post("/auth/login", data={"username": payload["email"], "password": payload["password"]})
  token = login_r.json()["access_token"]
  headers = {"Authorization": f"Bearer {token}"}

  r = client.post(
    "/auth/me/password",
    json={"current_password": "oldpass12", "new_password": "newpass12"},
    headers=headers,
  )
  assert r.status_code == 200
  assert r.json().get("detail") == "Пароль обновлён"

  assert client.post("/auth/login", data={"username": payload["email"], "password": "oldpass12"}).status_code == 401
  login_new = client.post("/auth/login", data={"username": payload["email"], "password": "newpass12"})
  assert login_new.status_code == 200


def test_change_password_wrong_current(client: TestClient):
  payload = {
    "email": "badcur@example.com",
    "username": "badcur",
    "full_name": "Имя Фамилия",
    "password": "rightpass1",
  }
  assert client.post("/auth/register", json=payload).status_code == 201
  token = client.post("/auth/login", data={"username": payload["email"], "password": payload["password"]}).json()[
    "access_token"
  ]
  r = client.post(
    "/auth/me/password",
    json={"current_password": "wrong", "new_password": "newpass12"},
    headers={"Authorization": f"Bearer {token}"},
  )
  assert r.status_code == 400
  assert r.json().get("detail") == "Неверный текущий пароль"


def test_change_password_same_as_current(client: TestClient):
  payload = {
    "email": "samepwd@example.com",
    "username": "samepwd",
    "full_name": "Имя Фамилия",
    "password": "samepass12",
  }
  assert client.post("/auth/register", json=payload).status_code == 201
  token = client.post("/auth/login", data={"username": payload["email"], "password": payload["password"]}).json()[
    "access_token"
  ]
  r = client.post(
    "/auth/me/password",
    json={"current_password": "samepass12", "new_password": "samepass12"},
    headers={"Authorization": f"Bearer {token}"},
  )
  assert r.status_code == 400
  assert "отличаться" in (r.json().get("detail") or "")


def test_forgot_password_unknown_email_opaque_response(client: TestClient, monkeypatch):
  async def noop(*_, **__):
    return None

  monkeypatch.setattr(main, "_send_password_reset_email", noop)
  r = client.post("/auth/forgot-password", json={"email": "missing-user@example.com"})
  assert r.status_code == 200
  assert r.json().get("detail") == main.FORGOT_PASSWORD_RESPONSE


def test_forgot_then_reset_and_login(client: TestClient, monkeypatch):
  async def noop(*_, **__):
    return None

  monkeypatch.setattr(main, "_send_password_reset_email", noop)
  monkeypatch.setattr("secrets.token_urlsafe", lambda _n: "fixed-reset-token-test-xyz")

  payload = {
    "email": "resetme@example.com",
    "username": "resetme",
    "full_name": "Имя Фамилия",
    "password": "oldpass12",
  }
  assert client.post("/auth/register", json=payload).status_code == 201

  r1 = client.post("/auth/forgot-password", json={"email": payload["email"]})
  assert r1.status_code == 200
  assert r1.json().get("detail") == main.FORGOT_PASSWORD_RESPONSE

  r2 = client.post(
    "/auth/reset-password",
    json={"token": "fixed-reset-token-test-xyz", "new_password": "newpass12"},
  )
  assert r2.status_code == 200

  login_old = client.post(
    "/auth/login",
    data={"username": payload["email"], "password": payload["password"]},
  )
  assert login_old.status_code == 401

  login_new = client.post(
    "/auth/login",
    data={"username": payload["email"], "password": "newpass12"},
  )
  assert login_new.status_code == 200
  assert login_new.json().get("access_token")


def test_reset_password_invalid_token(client: TestClient):
  r = client.post(
    "/auth/reset-password",
    json={"token": "not-a-valid-token-at-all-xxx", "new_password": "newpass12"},
  )
  assert r.status_code == 400


def test_internal_get_user_by_id(client: TestClient):
  payload = {
    "email": "internal@example.com",
    "username": "internal",
    "full_name": "Имя Внутренний",
    "password": "pass12345",
  }
  r = client.post("/auth/register", json=payload)
  assert r.status_code == 201
  user_id = r.json()["id"]

  r2 = client.get(f"/auth/internal/user/{user_id}")
  assert r2.status_code == 200
  data = r2.json()
  assert data["id"] == user_id
  assert data["email"] == payload["email"]

