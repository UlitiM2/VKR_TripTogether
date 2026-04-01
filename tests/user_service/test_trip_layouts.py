"""Тесты user-service: сохранение и загрузка личного layout дашборда."""
from fastapi.testclient import TestClient


def test_user_root(client: TestClient):
  r = client.get("/")
  assert r.status_code == 200
  assert r.json().get("service") == "User Service"


def test_user_health(client: TestClient):
  r = client.get("/health")
  assert r.status_code == 200
  assert r.json().get("status") == "healthy"


def test_trip_layout_empty_then_save_and_load(client: TestClient):
  trip_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"

  r_empty = client.get(f"/profiles/me/trip-layouts/{trip_id}")
  assert r_empty.status_code == 200
  data_empty = r_empty.json()
  assert data_empty["layouts"] == {}
  assert data_empty["collapsed"] == {}

  payload = {
    "layouts": {
      "lg": [
        {"i": "participants", "x": 0, "y": 0, "w": 6, "h": 8},
        {"i": "chat", "x": 6, "y": 0, "w": 6, "h": 8},
      ]
    },
    "collapsed": {"chat": False, "participants": False, "polls": True, "expenses": False},
  }
  r_put = client.put(f"/profiles/me/trip-layouts/{trip_id}", json=payload)
  assert r_put.status_code == 200

  r_loaded = client.get(f"/profiles/me/trip-layouts/{trip_id}")
  assert r_loaded.status_code == 200
  data_loaded = r_loaded.json()
  assert data_loaded["layouts"]["lg"][0]["i"] == "participants"
  assert data_loaded["collapsed"]["polls"] is True


def test_trip_layout_invalid_widget_id(client: TestClient):
  trip_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0002"
  payload = {
    "layouts": {"lg": [{"i": "unknown", "x": 0, "y": 0, "w": 1, "h": 1}]},
    "collapsed": {},
  }
  r = client.put(f"/profiles/me/trip-layouts/{trip_id}", json=payload)
  assert r.status_code == 400
  assert r.json().get("detail") == "Invalid widget id in layouts"

