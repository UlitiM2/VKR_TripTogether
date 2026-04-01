"""
Фикстуры для тестов chat-service.
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHAT_SERVICE_DIR = REPO_ROOT / "chat-service"
sys.path.insert(0, str(CHAT_SERVICE_DIR))

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
from main import app, get_db, verify_token, check_trip_access, _notify_new_message  # type: ignore  # noqa: E402


try:
  Base.metadata.create_all(bind=engine)
except Exception as e:
  pytest.skip(f"PostgreSQL недоступен (запустите docker-compose up -d postgres): {e}", allow_module_level=True)


TEST_USER_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


async def override_verify_token():
  return {"user_id": TEST_USER_ID, "sub": TEST_USER_ID}


async def override_check_trip_access(trip_id: str):
  return {"trip_id": trip_id, "ok": True}


async def override_notify_new_message(trip_id, author_id, message_preview):  # noqa: ANN001
  return None


@pytest.fixture
def client():
  session = SessionLocal()

  def override_get_db():
    yield session

  app.dependency_overrides[get_db] = override_get_db
  app.dependency_overrides[verify_token] = override_verify_token
  app.dependency_overrides[check_trip_access] = override_check_trip_access
  app.dependency_overrides[_notify_new_message] = override_notify_new_message

  try:
    with TestClient(app) as c:
      yield c
  finally:
    session.rollback()
    session.close()
    app.dependency_overrides.clear()

