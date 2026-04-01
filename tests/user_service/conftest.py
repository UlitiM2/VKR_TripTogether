"""
Фикстуры для тестов user-service (trip-layouts).
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
USER_SERVICE_DIR = REPO_ROOT / "user-service"
sys.path.insert(0, str(USER_SERVICE_DIR))

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

from db.db import Base, engine, SessionLocal  # type: ignore  # noqa: E402
from main import app, get_db, verify_token  # type: ignore  # noqa: E402
from models.trip_layout import UserTripLayout  # type: ignore  # noqa: E402


try:
  Base.metadata.create_all(bind=engine)
except Exception as e:
  pytest.skip(f"PostgreSQL недоступен (запустите docker-compose up -d postgres): {e}", allow_module_level=True)


TEST_USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


async def override_verify_token():
  return {"user_id": TEST_USER_ID, "sub": TEST_USER_ID}


@pytest.fixture
def client():
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

