"""
Фикстуры для тестов trip-service.
Запуск из корня репозитория: pytest tests/trip_service -v
При этом из папки trip-service: cd trip-service && pytest ../tests/trip_service -v

Требуется PostgreSQL (например: docker-compose up -d postgres).
Для локального запуска: TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tripplanner
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRIP_SERVICE_DIR = REPO_ROOT / "trip-service"
if not TRIP_SERVICE_DIR.exists():
    TRIP_SERVICE_DIR = REPO_ROOT / "trip-service"

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

from db.db import Base, engine, get_db, SessionLocal
from main import app, verify_token
from models.trip import Trip
from models.participant import TripParticipant, ParticipantRole

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    pytest.skip(f"PostgreSQL недоступен (запустите docker-compose up -d postgres): {e}", allow_module_level=True)

TEST_USER_ID_STR = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TEST_USER_UUID = uuid.UUID(TEST_USER_ID_STR)


async def override_verify_token():
    return {"user_id": TEST_USER_ID_STR, "sub": TEST_USER_ID_STR}


@pytest.fixture
def client():
    """Клиент с подменой get_db и verify_token. Одна сессия на тест."""
    session = SessionLocal()
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_token] = override_verify_token
    try:
        with TestClient(app) as c:
            yield c
    finally:
        session.rollback()
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth_override():
    """Клиент без подмены verify_token — для тестов на 403 без токена."""
    session = SessionLocal()
    def override_get_db():
        yield session
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.pop(verify_token, None)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        session.rollback()
        session.close()
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Заголовок Authorization для тестовых запросов."""
    return {"Authorization": "Bearer test-token"}
