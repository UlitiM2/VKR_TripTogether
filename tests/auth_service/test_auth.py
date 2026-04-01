"""Тесты auth-service: регистрация, логин, профиль, обновление."""
import pytest
from fastapi.testclient import TestClient

from security import get_password_hash  # type: ignore


def test_auth_root(client: TestClient):
  r = client.get("/")
  assert r.status_code == 200
  data = r.json()
  assert data.get("service") == "Auth Service"
  assert "register" in data.get("endpoints", {})
  assert "login" in data.get("endpoints", {})


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

