"""Unit-тесты для голосований (voting-service): опросы, варианты, голоса."""
import uuid

import pytest
from fastapi.testclient import TestClient


def test_voting_root(client: TestClient):
    """GET / возвращает описание сервиса."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "Voting" in data.get("service", "")
    assert "create_poll" in data.get("endpoints", {})


def test_voting_health(client: TestClient):
    """GET /health возвращает healthy."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_create_poll(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """POST /trips/{id}/polls создаёт опрос и возвращает 201."""
    payload = {
        "question": "Какой отель выбрать?",
        "options": ["Отель А", "Отель Б", "Отель В"],
    }
    r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["question"] == payload["question"]
    assert len(data["options"]) == 3
    assert data["options"][0]["text"] == "Отель А"
    assert data["options"][0]["vote_count"] == 0
    assert "id" in data
    assert data["trip_id"] == trip_id
    uuid.UUID(data["id"])


def test_list_polls(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """GET /trips/{id}/polls возвращает список опросов."""
    r = client.get(f"/trips/{trip_id}/polls", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_polls_after_create(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """После создания опроса он появляется в списке."""
    payload = {"question": "Дата поездки?", "options": ["Июль", "Август"]}
    create_r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    poll_id = create_r.json()["id"]

    list_r = client.get(f"/trips/{trip_id}/polls", headers=auth_headers)
    assert list_r.status_code == 200
    polls = list_r.json()
    ids = [p["id"] for p in polls]
    assert poll_id in ids


def test_get_poll(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """GET /trips/{id}/polls/{poll_id} возвращает опрос с результатами."""
    payload = {"question": "Транспорт?", "options": ["Поезд", "Самолёт"]}
    create_r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    poll_id = create_r.json()["id"]

    r = client.get(f"/trips/{trip_id}/polls/{poll_id}", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == poll_id
    assert data["question"] == "Транспорт?"
    assert len(data["options"]) == 2


def test_add_poll_option(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """POST /trips/{id}/polls/{poll_id}/options добавляет вариант."""
    payload = {"question": "Где ужинать?", "options": ["Ресторан А"]}
    create_r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    poll_id = create_r.json()["id"]

    r = client.post(
        f"/trips/{trip_id}/polls/{poll_id}/options",
        json={"text": "Ресторан Б"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["options"]) == 2
    texts = [o["text"] for o in data["options"]]
    assert "Ресторан Б" in texts


def test_vote_poll(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """POST /trips/{id}/polls/{poll_id}/vote отдаёт голос за вариант."""
    payload = {"question": "Выбор?", "options": ["Вариант 1", "Вариант 2"]}
    create_r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    poll_id = create_r.json()["id"]
    option_id = create_r.json()["options"][0]["id"]

    r = client.post(
        f"/trips/{trip_id}/polls/{poll_id}/vote",
        json={"option_id": option_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    opt1 = next(o for o in data["options"] if o["id"] == option_id)
    assert opt1["vote_count"] == 1


def test_vote_change(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """Повторный голос меняет выбор на другой вариант."""
    payload = {"question": "A или B?", "options": ["A", "B"]}
    create_r = client.post(f"/trips/{trip_id}/polls", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    poll_id = create_r.json()["id"]
    option_a_id = create_r.json()["options"][0]["id"]
    option_b_id = create_r.json()["options"][1]["id"]

    client.post(
        f"/trips/{trip_id}/polls/{poll_id}/vote",
        json={"option_id": option_a_id},
        headers=auth_headers,
    )
    r = client.post(
        f"/trips/{trip_id}/polls/{poll_id}/vote",
        json={"option_id": option_b_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    opt_a = next(o for o in data["options"] if o["id"] == option_a_id)
    opt_b = next(o for o in data["options"] if o["id"] == option_b_id)
    assert opt_a["vote_count"] == 0
    assert opt_b["vote_count"] == 1


def test_get_poll_not_found(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """GET /trips/{id}/polls/{poll_id} с несуществующим poll_id возвращает 404."""
    fake_poll_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/trips/{trip_id}/polls/{fake_poll_id}", headers=auth_headers)
    assert r.status_code == 404


def test_create_poll_unauthorized(client_no_auth_override: TestClient, trip_id: str):
    """POST /trips/{id}/polls без токена возвращает 401."""
    r = client_no_auth_override.post(
        f"/trips/{trip_id}/polls",
        json={"question": "?", "options": ["A"]},
    )
    assert r.status_code == 401
