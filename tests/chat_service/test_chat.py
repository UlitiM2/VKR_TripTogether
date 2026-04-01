"""Тесты chat-service: отправка и список сообщений, health."""
from fastapi.testclient import TestClient


def test_chat_root(client: TestClient):
  r = client.get("/")
  assert r.status_code == 200
  data = r.json()
  assert data.get("service") == "Chat Service"


def test_chat_health(client: TestClient):
  r = client.get("/health")
  assert r.status_code == 200
  assert r.json().get("status") == "healthy"


def test_send_and_list_messages(client: TestClient):
  trip_id = "cccccccc-cccc-cccc-cccc-cccccccc0001"
  payload = {"content": "Привет, чат!"}

  r_send = client.post(f"/trips/{trip_id}/messages", json=payload)
  assert r_send.status_code == 201
  msg = r_send.json()
  assert msg["content"] == "Привет, чат!"

  r_list = client.get(f"/trips/{trip_id}/messages")
  assert r_list.status_code == 200
  messages = r_list.json()
  assert any(m["id"] == msg["id"] for m in messages)
