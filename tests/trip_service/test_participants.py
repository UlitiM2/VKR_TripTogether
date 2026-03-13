"""Unit-тесты для участников и приглашений (trip-service)."""
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient


def test_invite_requires_organizer(client: TestClient, auth_headers: dict):
    """Пригласить может только организатор (создатель поездки)."""
    # Создаём поездку — текущий пользователь организатор
    create_r = client.post(
        "/trips",
        json={
            "title": "Поездка с участниками",
            "destination": "Крым",
            "start_date": "2025-07-01",
            "end_date": "2025-07-10",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    # Мокаем resolve_user_id_by_email — возвращаем другого пользователя
    invited_user_id = "b2b3c4d5-e6f7-8901-bcde-f23456789012"

    with patch("main.resolve_user_id_by_email", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = uuid.UUID(invited_user_id)
        r = client.post(
            f"/trips/{trip_id}/participants/invite",
            json={"email": "friend@example.com"},
            headers=auth_headers,
        )
    assert r.status_code == 201
    data = r.json()
    assert "participant" in data
    assert data["participant"]["user_id"] == invited_user_id
    assert data["participant"]["role"] == "member"


def test_list_participants(client: TestClient, auth_headers: dict):
    """GET /trips/{id}/participants возвращает список участников."""
    create_r = client.post(
        "/trips",
        json={
            "title": "Поездка для списка участников",
            "destination": "Алтай",
            "start_date": "2025-08-01",
            "end_date": "2025-08-14",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    r = client.get(f"/trips/{trip_id}/participants", headers=auth_headers)
    assert r.status_code == 200
    participants = r.json()
    assert len(participants) >= 1
    organizer = next(p for p in participants if p["role"] == "organizer")
    assert organizer is not None


def test_accept_invitation(client: TestClient, auth_headers: dict):
    """PATCH /trips/{id}/participants/me/accept принимает приглашение."""
    create_r = client.post(
        "/trips",
        json={
            "title": "Поездка для accept",
            "destination": "Байкал",
            "start_date": "2025-09-01",
            "end_date": "2025-09-10",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    # Текущий пользователь уже организатор (добавлен при создании), принятие уже есть
    r = client.patch(
        f"/trips/{trip_id}/participants/me/accept",
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert "participant" in r.json()


def test_invite_self_fails(client: TestClient, auth_headers: dict):
    """Нельзя пригласить самого себя."""
    create_r = client.post(
        "/trips",
        json={
            "title": "Поездка",
            "destination": "Сочи",
            "start_date": "2025-07-01",
            "end_date": "2025-07-07",
        },
        headers=auth_headers,
    )
    assert create_r.status_code == 201
    trip_id = create_r.json()["id"]

    with patch("main.resolve_user_id_by_email", new_callable=AsyncMock) as mock_resolve:
        mock_resolve.return_value = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        r = client.post(
            f"/trips/{trip_id}/participants/invite",
            json={"email": "me@example.com"},
            headers=auth_headers,
        )
    assert r.status_code == 400
    assert "yourself" in r.json().get("detail", "").lower() or "self" in r.json().get("detail", "").lower()
