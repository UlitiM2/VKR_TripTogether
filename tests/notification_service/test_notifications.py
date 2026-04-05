"""Тесты notification-service: корневой, health и отправка."""
from fastapi.testclient import TestClient


def test_notification_root(client: TestClient):
  r = client.get("/")
  assert r.status_code == 200
  data = r.json()
  assert data.get("service") == "Notification Service"
  assert "send" in data.get("endpoints", {})


def test_notification_health(client: TestClient):
  r = client.get("/health")
  assert r.status_code == 200
  assert r.json().get("status") == "healthy"


def test_send_invite_without_emails_error(client: TestClient):
    payload = {"event": "invite", "to_emails": ["", "bad"], "data": {}}
    r = client.post("/internal/send", json=payload)
    assert r.status_code == 400
    assert r.json().get("detail") == "to_emails required"


def test_send_password_reset_success(client: TestClient):
  payload = {
    "event": "password_reset",
    "to_emails": ["user@example.com"],
    "data": {"reset_url": "http://localhost:5173/reset-password?token=abc"},
  }
  r = client.post("/internal/send", json=payload)
  assert r.status_code == 200
  data = r.json()
  assert data["sent"] is True
  assert data["event"] == "password_reset"
  assert data["to"] == ["user@example.com"]


def test_send_new_chat_message_success(client: TestClient):
  payload = {
    "event": "new_chat_message",
    "to_emails": ["user1@example.com", "bad-email", ""],
    "data": {"trip_title": "Поездка", "author_name": "Имя", "message_preview": "Привет"},
  }
  r = client.post("/internal/send", json=payload)
  assert r.status_code == 200
  data = r.json()
  assert data["sent"] is True
  assert data["event"] == "new_chat_message"
  # в списке только валидные email
  assert data["to"] == ["user1@example.com"]

