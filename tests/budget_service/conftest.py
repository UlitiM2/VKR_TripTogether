"""
Фикстуры для тестов budget-service.
Запуск из корня: pytest tests/budget_service -v
Из папки budget-service: cd budget-service && pytest ../tests/budget_service -v

Требуется PostgreSQL. Создаются таблицы trips (trip-service) и expenses, expense_shares.
"""
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRIP_SERVICE_DIR = REPO_ROOT / "trip-service"
BUDGET_SERVICE_DIR = REPO_ROOT / "budget-service"

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/tripplanner_test"),
)
_db_url = os.environ["DATABASE_URL"]
if "tripplanner_test" not in _db_url:
    pytest.skip(
        "Небезопасный DATABASE_URL для тестов. Используйте TEST_DATABASE_URL с БД tripplanner_test.",
        allow_module_level=True,
    )

sys.path.insert(0, str(TRIP_SERVICE_DIR))
from db.db import Base as TripBase, engine as _trip_engine
from models.trip import Trip as TripModel

try:
    TripBase.metadata.create_all(bind=_trip_engine)
except Exception as e:
    pytest.skip(f"PostgreSQL недоступен: {e}", allow_module_level=True)

sys.path.insert(0, str(BUDGET_SERVICE_DIR))
from db.db import Base, engine, get_db, SessionLocal
from main import app, verify_token, check_trip_access

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    pytest.skip(f"PostgreSQL недоступен: {e}", allow_module_level=True)

FIXTURE_TRIP_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-000000000001")
EMPTY_TRIP_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-000000000002")  # поезд без расходов для тестов empty
FIXTURE_USER_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
OTHER_USER_ID = uuid.UUID("b2b3c4d5-e6f7-8901-bcde-f23456789012")


def _ensure_fixture_trip(session):
    from sqlalchemy import text
    for tid, name in [(FIXTURE_TRIP_ID, "Test Trip"), (EMPTY_TRIP_ID, "Empty Trip")]:
        row = session.execute(text("SELECT 1 FROM trips WHERE id = :id"), {"id": str(tid)}).scalar()
        if not row:
            session.execute(
                text(
                    "INSERT INTO trips (id, title, destination, start_date, end_date, created_by, created_at, updated_at) "
                    "VALUES (:id, :title, 'Test', :start, :end, :user_id, NOW(), NOW())"
                ),
                {
                    "id": str(tid),
                    "title": name,
                    "start": date(2025, 7, 1),
                    "end": date(2025, 7, 10),
                    "user_id": str(FIXTURE_USER_ID),
                },
            )
            session.commit()


TEST_USER_ID_STR = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


async def override_verify_token():
    return {"user_id": TEST_USER_ID_STR, "sub": TEST_USER_ID_STR}


async def override_check_trip_access(trip_id: str = ""):
    return {"ok": True}


@pytest.fixture
def client():
    session = SessionLocal()
    # Отключаем реальный commit, чтобы откат в finally изолировал тесты
    _original_commit = session.commit
    def _no_commit():
        session.flush()
    session.commit = _no_commit
    try:
        _ensure_fixture_trip(session)

        def override_get_db():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[verify_token] = override_verify_token
        app.dependency_overrides[check_trip_access] = override_check_trip_access
        with TestClient(app) as c:
            yield c
    finally:
        session.rollback()
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth_override():
    """Клиент без подмены verify_token — для тестов на 401 без токена."""
    session = SessionLocal()
    _original_commit = session.commit
    session.commit = lambda: session.flush()
    try:
        _ensure_fixture_trip(session)

        def override_get_db():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides.pop(verify_token, None)
        app.dependency_overrides.pop(check_trip_access, None)
        with TestClient(app) as c:
            yield c
    finally:
        session.rollback()
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def trip_id():
    return str(FIXTURE_TRIP_ID)


@pytest.fixture
def empty_trip_id():
    """Поезд без расходов — для тестов test_list_expenses_empty и test_get_debts_empty."""
    return str(EMPTY_TRIP_ID)


@pytest.fixture
def current_user_id():
    """UUID текущего тестового пользователя (плательщик по умолчанию)."""
    return str(FIXTURE_USER_ID)


@pytest.fixture
def other_user_id():
    """UUID второго пользователя для split_between."""
    return str(OTHER_USER_ID)
