"""Unit-тесты для эндпоинтов поездок (trip-service): создание, список, просмотр, удаление."""
import uuid

import pytest
from fastapi.testclient import TestClient


def test_root(client: TestClient):
    """GET / возвращает описание сервиса."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "Trip Service"
    assert "create_trip" in data.get("endpoints", {})


def test_health(client: TestClient):
    """GET /health возвращает healthy."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_create_trip(client: TestClient, auth_headers: dict):
    """POST /trips создаёт поездку и возвращает 201."""
    payload = {
        "title": "Отпуск в горах",
        "destination": "Кавказ",
        "start_date": "2025-07-01",
        "end_date": "2025-07-14",
        "budget": 50000.50,
        "description": "Поездка с палатками",
    }
    r = client.post("/trips", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == payload["title"]
    assert data["destination"] == payload["destination"]
    assert data["start_date"] == payload["start_date"]
    assert data["end_date"] == payload["end_date"]
    assert data["budget"] == payload["budget"]
    assert data["description"] == payload["description"]
    assert "id" in data
    assert "created_by" in data
    uuid.UUID(data["id"])
    uuid.UUID(data["created_by"])


def test_create_trip_minimal(client: TestClient, auth_headers: dict):
    """POST /trips с минимальными полями (без budget, description)."""
    payload = {
        "title": "Выходные",
        "destination": "Петербург",
        "start_date": "2025-06-01",
        "end_date": "2025-06-02",
    }
    r = client.post("/trips", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Выходные"
    assert data.get("budget") is None


def test_create_trip_unauthorized(client_no_auth_override: TestClient):
    """POST /trips без токена возвращает 401."""
    r = client_no_auth_override.post(
        "/trips",
        json={
            "title": "Поездка",
            "destination": "Москва",
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
        },
    )
    assert r.status_code == 401


def test_get_trips(client: TestClient, auth_headers: dict):
    """GET /trips возвращает 200 и список поездок (массив)."""
    r = client.get("/trips", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_trips_after_create(client: TestClient, auth_headers: dict):
    """GET /trips возвращает созданные поездки пользователя."""
    payload = {
        "title": "Поездка для списка",
        "destination": "Сочи",
        "start_date": "2025-08-01",
        "end_date": "2025-08-07",
    }
    create_r = client.post("/trips", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    r = client.get("/trips", headers=auth_headers)
    assert r.status_code == 200
    trips = r.json()
    assert len(trips) >= 1
    ids = [t["id"] for t in trips]
    assert trip_id in ids


def test_get_trip(client: TestClient, auth_headers: dict):
    """GET /trips/{id} возвращает поездку по её id."""
    create_r = client.post(
        "/trips",
        json={
            "title": "Для get_trip",
            "destination": "Казань",
            "start_date": "2025-09-01",
            "end_date": "2025-09-05",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    r = client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["id"] == trip_id
    assert r.json()["title"] == "Для get_trip"


def test_get_trip_not_found(client: TestClient, auth_headers: dict):
    """GET /trips/{id} с несуществующим id возвращает 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/trips/{fake_id}", headers=auth_headers)
    assert r.status_code == 404


def test_delete_trip(client: TestClient, auth_headers: dict):
    """DELETE /trips/{id} удаляет поездку и возвращает 200."""
    create_r = client.post(
        "/trips",
        json={
            "title": "Для удаления",
            "destination": "Владивосток",
            "start_date": "2025-10-01",
            "end_date": "2025-10-03",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    r = client.delete(f"/trips/{trip_id}", headers=auth_headers)
    assert r.status_code == 200
    assert "deleted" in r.json().get("message", "").lower()

    get_r = client.get(f"/trips/{trip_id}", headers=auth_headers)
    assert get_r.status_code == 404
