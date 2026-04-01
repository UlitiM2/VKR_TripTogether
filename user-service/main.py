import os
import uuid
from datetime import date
from time import monotonic
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import httpx
from sqlalchemy.orm import Session

from db.db import engine, Base, get_db
from models.achievement import UserAchievementProgress
from models.trip_layout import UserTripLayout
from schemas.achievement import AchievementListResponse, AchievementItem
from schemas.trip_layout import TripLayoutPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL", "http://trip-service:8000")
VOTING_SERVICE_URL = os.getenv("VOTING_SERVICE_URL", "http://voting-service:8000")
BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://budget-service:8000")
ACHIEVEMENTS_CACHE_TTL_SECONDS = int(os.getenv("ACHIEVEMENTS_CACHE_TTL_SECONDS", "60"))

# In-memory TTL cache: {user_id: (expires_at_monotonic, payload)}
_achievements_cache: dict[str, tuple[float, AchievementListResponse]] = {}

DEFAULT_ACHIEVEMENTS = [
    {
        "id": "first-route",
        "icon": "🧭",
        "title": "Первый маршрут",
        "requirement": "Создайте свою первую поездку.",
        "target": 1,
        "default_current": 1,
    },
    {
        "id": "team-organizer",
        "icon": "🤝",
        "title": "Командный организатор",
        "requirement": "Пригласите в поездки не менее 10 участников суммарно.",
        "target": 10,
        "default_current": 7,
    },
    {
        "id": "budget-master",
        "icon": "💰",
        "title": "Мастер бюджета",
        "requirement": "Добавьте 20 расходов и закройте расчеты долгов без конфликтов.",
        "target": 20,
        "default_current": 11,
    },
    {
        "id": "active-voter",
        "icon": "🗳️",
        "title": "Активный голосующий",
        "requirement": "Проголосуйте минимум в 15 опросах.",
        "target": 15,
        "default_current": 6,
    },
    {
        "id": "traveler",
        "icon": "🎒",
        "title": "Путешественник",
        "requirement": "Завершите 5 поездок в разные города.",
        "target": 5,
        "default_current": 1,
    },
]


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Верификация токена через Auth Service"""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=5.0
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            data = response.json()
            data["_token"] = token
            return data
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


def _get_user_uuid(user_data: dict) -> uuid.UUID:
    raw = user_data.get("user_id") or user_data.get("sub")
    if not raw:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user id")


def _validate_layout_payload(payload: TripLayoutPayload) -> None:
    allowed = {
        "participants",
        "polls",
        "pollsCreate",
        "pollsResults",
        "expenses",
        "expensesSummary",
        "expensesCreate",
        "expensesHistory",
        "chat",
    }
    for k in payload.collapsed.keys():
        if k not in allowed:
            raise HTTPException(status_code=400, detail="Invalid widget id in collapsed")
    try:
        for _bp, items in payload.layouts.items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                wid = it.get("i")
                if wid is None:
                    continue
                if str(wid) not in allowed:
                    raise HTTPException(status_code=400, detail="Invalid widget id in layouts")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid layout payload")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting User Service")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("User Service stopped")
    engine.dispose()

app = FastAPI(
    title="TripPlanner User Service",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "service": "User Service",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "user-service"}


async def _fetch_profile_from_auth(user_id: str) -> dict:
    """Внутренний запрос к Auth: данные пользователя по id."""
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{AUTH_SERVICE_URL}/auth/internal/user/{user_id}",
                timeout=5.0,
            )
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                return None
            return r.json()
        except httpx.RequestError:
            return None


def _make_auth_headers(user_data: dict) -> dict[str, str]:
    token = user_data.get("_token")
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"Authorization": f"Bearer {token}"}


async def _safe_get_json(client: httpx.AsyncClient, url: str, headers: dict[str, str], fallback):
    try:
        r = await client.get(url, headers=headers, timeout=8.0)
        if r.status_code == 200:
            return r.json()
    except httpx.RequestError:
        pass
    return fallback


@app.get("/profiles/{user_id}")
async def get_profile(user_id: str, user_data: dict = Depends(verify_token)):
    """Получение профиля пользователя (данные из Auth Service)."""
    profile = await _fetch_profile_from_auth(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@app.get("/profiles/me")
async def get_my_profile(user_data: dict = Depends(verify_token)):
    """Профиль текущего пользователя (данные из Auth Service)."""
    user_id = user_data.get("user_id") or user_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    profile = await _fetch_profile_from_auth(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@app.get("/profiles/me/achievements", response_model=AchievementListResponse)
async def get_my_achievements(
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user_uuid = _get_user_uuid(user_data)
    cache_key = str(user_uuid)
    now = monotonic()
    cached = _achievements_cache.get(cache_key)
    if cached and cached[0] > now:
      return cached[1]
    row = (
        db.query(UserAchievementProgress)
        .filter(UserAchievementProgress.user_id == user_uuid)
        .first()
    )
    saved = (row.progress_json or {}) if row else {}
    headers = _make_auth_headers(user_data)
    user_id_str = str(user_uuid)

    trips: list[dict] = []
    organized_trip_ids: list[str] = []
    participant_invites = 0
    expenses_paid_total = 0
    voted_polls_total = 0
    finished_trips_total = 0
    today = date.today()

    async with httpx.AsyncClient() as client:
        trips_data = await _safe_get_json(client, f"{TRIP_SERVICE_URL}/trips", headers, [])
        if isinstance(trips_data, list):
            trips = trips_data
        organized_trips = [t for t in trips if t.get("is_organizer") is True]
        organized_trip_ids = [str(t.get("id")) for t in organized_trips if t.get("id")]

        # Metric: completed trips by end_date.
        for t in trips:
            end_raw = t.get("end_date")
            if not isinstance(end_raw, str):
                continue
            try:
                end_d = date.fromisoformat(end_raw)
                if end_d < today:
                    finished_trips_total += 1
            except ValueError:
                continue

        # Metric: invited/managed participants (excluding self).
        for trip_id in organized_trip_ids:
            ppl = await _safe_get_json(client, f"{TRIP_SERVICE_URL}/trips/{trip_id}/participants", headers, [])
            if isinstance(ppl, list):
                participant_invites += sum(1 for p in ppl if str(p.get("user_id")) != user_id_str)

        # Metrics from budget and voting across user's trips.
        for trip_id in [str(t.get("id")) for t in trips if t.get("id")]:
            expenses = await _safe_get_json(client, f"{BUDGET_SERVICE_URL}/trips/{trip_id}/expenses", headers, [])
            if isinstance(expenses, list):
                expenses_paid_total += sum(1 for e in expenses if str(e.get("paid_by_user_id")) == user_id_str)

            polls = await _safe_get_json(client, f"{VOTING_SERVICE_URL}/trips/{trip_id}/polls", headers, [])
            if isinstance(polls, list):
                voted_polls_total += sum(1 for p in polls if p.get("my_option_id") is not None)

    # Real metrics baseline (can be overridden by saved JSON for manual tuning/testing).
    real_current = {
        "first-route": max(0, len(trips)),
        "team-organizer": max(0, participant_invites),
        "budget-master": max(0, expenses_paid_total),
        "active-voter": max(0, voted_polls_total),
        "traveler": max(0, finished_trips_total),
    }

    achievements: list[AchievementItem] = []
    for ach in DEFAULT_ACHIEVEMENTS:
        current_raw = saved.get(ach["id"], real_current.get(ach["id"], ach["default_current"]))
        try:
            current = max(0, int(current_raw))
        except Exception:
            current = real_current.get(ach["id"], ach["default_current"])
        target = int(ach["target"])
        progress = min(100, int(round((current / target) * 100))) if target > 0 else 0
        achievements.append(
            AchievementItem(
                id=ach["id"],
                icon=ach["icon"],
                title=ach["title"],
                requirement=ach["requirement"],
                current=current,
                target=target,
                progress=progress,
                unlocked=current >= target,
            )
        )

    result = AchievementListResponse(achievements=achievements)
    _achievements_cache[cache_key] = (now + max(1, ACHIEVEMENTS_CACHE_TTL_SECONDS), result)
    return result


@app.get("/profiles/me/trip-layouts/{trip_id}", response_model=TripLayoutPayload)
async def get_my_trip_layout(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user_uuid = _get_user_uuid(user_data)
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip_id")
    row = (
        db.query(UserTripLayout)
        .filter(UserTripLayout.user_id == user_uuid, UserTripLayout.trip_id == trip_uuid)
        .first()
    )
    if not row:
        return TripLayoutPayload(layouts={}, collapsed={})
    data = row.layout_json or {}
    return TripLayoutPayload(
        layouts=data.get("layouts") or {},
        collapsed=data.get("collapsed") or {},
    )


@app.put("/profiles/me/trip-layouts/{trip_id}", response_model=TripLayoutPayload)
async def save_my_trip_layout(
    trip_id: str,
    body: TripLayoutPayload,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user_uuid = _get_user_uuid(user_data)
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trip_id")

    _validate_layout_payload(body)

    row = (
        db.query(UserTripLayout)
        .filter(UserTripLayout.user_id == user_uuid, UserTripLayout.trip_id == trip_uuid)
        .first()
    )
    payload = {"layouts": body.layouts, "collapsed": body.collapsed}
    if row:
        row.layout_json = payload
    else:
        row = UserTripLayout(user_id=user_uuid, trip_id=trip_uuid, layout_json=payload)
        db.add(row)
    db.commit()
    return body