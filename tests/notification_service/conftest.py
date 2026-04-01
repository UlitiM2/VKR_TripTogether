"""
Фикстуры для notification-service.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NOTIF_SERVICE_DIR = REPO_ROOT / "notification-service"
sys.path.insert(0, str(NOTIF_SERVICE_DIR))

from main import app  # type: ignore  # noqa: E402


@pytest.fixture
def client():
  with TestClient(app) as c:
    yield c

