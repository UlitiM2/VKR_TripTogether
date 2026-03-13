"""Unit-тесты для budget-service: расходы и расчёт долгов."""
import uuid

import pytest
from fastapi.testclient import TestClient


def test_budget_root(client: TestClient):
    """GET / возвращает описание сервиса."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "Budget" in data.get("service", "")
    assert "add_expense" in data.get("endpoints", {})


def test_budget_health(client: TestClient):
    """GET /health возвращает healthy."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_add_expense(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
    current_user_id: str,
    other_user_id: str,
):
    """POST /trips/{id}/expenses создаёт расход и возвращает 201."""
    payload = {
        "amount": 1000.50,
        "category": "Еда",
        "description": "Ужин",
        "split_between": [current_user_id, other_user_id],
    }
    r = client.post(f"/trips/{trip_id}/expenses", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == 1000.50
    assert data["category"] == "Еда"
    assert data["description"] == "Ужин"
    assert data["paid_by_user_id"] == current_user_id
    assert data["trip_id"] == trip_id
    assert data["share_count"] == 2
    assert "id" in data
    uuid.UUID(data["id"])


def test_add_expense_minimal(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
    current_user_id: str,
):
    """POST с минимальными полями (только amount и split_between)."""
    payload = {
        "amount": 500,
        "split_between": [current_user_id],
    }
    r = client.post(f"/trips/{trip_id}/expenses", json=payload, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["amount"] == 500
    assert data["share_count"] == 1


def test_list_expenses_empty(
    client: TestClient,
    auth_headers: dict,
    empty_trip_id: str,
):
    """GET /trips/{id}/expenses без расходов возвращает пустой список."""
    r = client.get(f"/trips/{empty_trip_id}/expenses", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_list_expenses_after_add(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
    current_user_id: str,
):
    """После добавления расхода он появляется в списке."""
    payload = {
        "amount": 300,
        "category": "Транспорт",
        "split_between": [current_user_id],
    }
    create_r = client.post(f"/trips/{trip_id}/expenses", json=payload, headers=auth_headers)
    assert create_r.status_code == 201
    expense_id = create_r.json()["id"]

    list_r = client.get(f"/trips/{trip_id}/expenses", headers=auth_headers)
    assert list_r.status_code == 200
    expenses = list_r.json()
    assert len(expenses) >= 1
    ids = [e["id"] for e in expenses]
    assert expense_id in ids


def test_get_debts_empty(
    client: TestClient,
    auth_headers: dict,
    empty_trip_id: str,
):
    """GET /trips/{id}/expenses/debts без расходов возвращает пустой список долгов."""
    r = client.get(f"/trips/{empty_trip_id}/expenses/debts", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "debts" in data
    assert data["debts"] == []


def test_get_debts_after_expense_split(
    client: TestClient,
    auth_headers: dict,
    empty_trip_id: str,
    current_user_id: str,
    other_user_id: str,
):
    """Расход 600 между двумя на пустом поезде: other должен current 300."""
    payload = {
        "amount": 600,
        "category": "Жильё",
        "split_between": [current_user_id, other_user_id],
    }
    client.post(f"/trips/{empty_trip_id}/expenses", json=payload, headers=auth_headers)

    r = client.get(f"/trips/{empty_trip_id}/expenses/debts", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    debts = data.get("debts", [])
    assert len(debts) >= 1
    from_debt = next(
        (d for d in debts if d["from_user_id"] == other_user_id and d["to_user_id"] == current_user_id),
        None,
    )
    assert from_debt is not None
    assert from_debt["amount"] == 300.0


def test_add_expense_unauthorized(client_no_auth_override: TestClient, trip_id: str):
    """POST /trips/{id}/expenses без токена возвращает 401."""
    r = client_no_auth_override.post(
        f"/trips/{trip_id}/expenses",
        json={"amount": 100, "split_between": [str(uuid.uuid4())]},
    )
    assert r.status_code == 401


def test_add_expense_negative_amount(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
    current_user_id: str,
):
    """POST с amount <= 0 возвращает 422."""
    r = client.post(
        f"/trips/{trip_id}/expenses",
        json={"amount": 0, "split_between": [current_user_id]},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_add_expense_empty_split(
    client: TestClient,
    auth_headers: dict,
    trip_id: str,
):
    """POST с пустым split_between возвращает 422."""
    r = client.post(
        f"/trips/{trip_id}/expenses",
        json={"amount": 100, "split_between": []},
        headers=auth_headers,
    )
    assert r.status_code == 422
