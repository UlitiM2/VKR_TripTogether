"""
Фикстуры для тестов auth-service.
Запуск из корня репозитория:

- cd auth-service && PYTHONPATH=. pytest ../tests/auth_service -v
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUTH_SERVICE_DIR = REPO_ROOT / "auth-service"
sys.path.insert(0, str(AUTH_SERVICE_DIR))

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
from main import app, get_db  # type: ignore  # noqa: E402
from schemas.user import User  # type: ignore  # noqa: E402


try:
  Base.metadata.create_all(bind=engine)
except Exception as e:
  pytest.skip(f"PostgreSQL недоступен (запустите docker-compose up -d postgres): {e}", allow_module_level=True)


@pytest.fixture
def db_session():
  session = SessionLocal()
  try:
    yield session
  finally:
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
  """Клиент с подменой get_db. Одна сессия на тест, чистая таблица users."""
  # Чистим пользователей перед каждым тестом, чтобы не было конфликтов уникальности email.
  db_session.query(User).delete()
  db_session.commit()

  def override_get_db():
    yield db_session

  app.dependency_overrides[get_db] = override_get_db
  try:
    with TestClient(app) as c:
      yield c
  finally:
    app.dependency_overrides.clear()


@pytest.fixture
def create_user(db_session):
  """Фабрика для создания пользователя напрямую в БД."""
  def _create_user(email: str, username: str, full_name: str | None, hashed_password: str):
    u = User(
      email=email,
      username=username,
      full_name=full_name,
      hashed_password=hashed_password,
      is_active=True,
      is_verified=False,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u

  return _create_user

