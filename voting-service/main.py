from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import os
import uuid

import httpx

from db.db import engine, Base, get_db
from models.poll import Poll, PollOption, PollVote
from schemas.poll import (
    PollCreate,
    PollResponse,
    PollOptionResponse,
    PollVoteCreate,
    PollOptionCreate,
)
from sqlalchemy.orm import Session
from sqlalchemy import func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
TRIP_SERVICE_URL = os.getenv("TRIP_SERVICE_URL", "http://trip-service:8000")


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Верификация токена через Auth Service."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/auth/verify",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=5.0,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def check_trip_access(
    trip_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Проверка доступа к поездке через Trip Service (создатель или участник)."""
    token = credentials.credentials
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{TRIP_SERVICE_URL}/trips/{trip_id}/internal/check-access",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Trip not found")
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access this trip",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502, detail="Trip service error"
                )
            return response.json()
        except httpx.RequestError:
            raise HTTPException(
                status_code=503, detail="Trip service unavailable"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Voting Service")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    yield
    logger.info("Voting Service stopped")
    engine.dispose()


app = FastAPI(
    title="TripPlanner Voting Service",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "service": "Voting Service",
        "status": "running",
        "endpoints": {
            "create_poll": "POST /trips/{trip_id}/polls",
            "list_polls": "GET /trips/{trip_id}/polls",
            "get_poll": "GET /trips/{trip_id}/polls/{poll_id}",
            "add_poll_option": "POST /trips/{trip_id}/polls/{poll_id}/options",
            "vote": "POST /trips/{trip_id}/polls/{poll_id}/vote",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "voting-service"}


def _poll_response_with_results(db: Session, poll: Poll) -> PollResponse:
    options = (
        db.query(PollOption)
        .filter(PollOption.poll_id == poll.id)
        .order_by(PollOption.position)
        .all()
    )
    option_ids = [o.id for o in options]
    vote_counts = {}
    if option_ids:
        counts = (
            db.query(PollVote.option_id, func.count(PollVote.id))
            .filter(PollVote.option_id.in_(option_ids))
            .group_by(PollVote.option_id)
            .all()
        )
        vote_counts = {opt_id: c for opt_id, c in counts}
    option_responses = [
        PollOptionResponse(
            id=o.id,
            poll_id=o.poll_id,
            text=o.text,
            position=o.position,
            vote_count=vote_counts.get(o.id, 0),
        )
        for o in options
    ]
    return PollResponse(
        id=poll.id,
        trip_id=poll.trip_id,
        created_by=poll.created_by,
        question=poll.question,
        created_at=poll.created_at,
        options=option_responses,
    )


def _get_user_uuid(user_data: dict) -> uuid.UUID:
    user_id_str = user_data.get("user_id") or user_data.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


def _parse_trip_id(trip_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Trip not found")


def _parse_poll_id(poll_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(poll_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Poll not found")


@app.post(
    "/trips/{trip_id}/polls",
    response_model=PollResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_poll(
    trip_id: str,
    body: PollCreate,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Создать опрос (любой участник поездки)."""
    user_uuid = _get_user_uuid(user_data)
    trip_uuid = _parse_trip_id(trip_id)

    poll = Poll(
        trip_id=trip_uuid,
        created_by=user_uuid,
        question=body.question,
    )
    db.add(poll)
    db.flush()
    for i, text in enumerate(body.options):
        opt = PollOption(poll_id=poll.id, text=text.strip(), position=i)
        db.add(opt)
    db.commit()
    db.refresh(poll)
    logger.info(f"Poll created: {poll.id} in trip {trip_id}")
    return _poll_response_with_results(db, poll)


@app.get("/trips/{trip_id}/polls", response_model=list[PollResponse])
async def list_polls(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Список опросов поездки с результатами."""
    trip_uuid = _parse_trip_id(trip_id)
    polls = (
        db.query(Poll)
        .filter(Poll.trip_id == trip_uuid)
        .order_by(Poll.created_at.desc())
        .all()
    )
    return [_poll_response_with_results(db, p) for p in polls]


@app.get("/trips/{trip_id}/polls/{poll_id}", response_model=PollResponse)
async def get_poll(
    trip_id: str,
    poll_id: str,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Получить опрос с результатами."""
    trip_uuid = _parse_trip_id(trip_id)
    poll_uuid = _parse_poll_id(poll_id)
    poll = (
        db.query(Poll)
        .filter(Poll.id == poll_uuid, Poll.trip_id == trip_uuid)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    return _poll_response_with_results(db, poll)


@app.post("/trips/{trip_id}/polls/{poll_id}/options", response_model=PollResponse)
async def add_poll_option(
    trip_id: str,
    poll_id: str,
    body: PollOptionCreate,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Добавить вариант ответа к опросу."""
    trip_uuid = _parse_trip_id(trip_id)
    poll_uuid = _parse_poll_id(poll_id)
    poll = (
        db.query(Poll)
        .filter(Poll.id == poll_uuid, Poll.trip_id == trip_uuid)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    options_count = db.query(PollOption).filter(PollOption.poll_id == poll.id).count()
    opt = PollOption(poll_id=poll.id, text=body.text.strip(), position=options_count)
    db.add(opt)
    db.commit()
    db.refresh(poll)
    return _poll_response_with_results(db, poll)


@app.post("/trips/{trip_id}/polls/{poll_id}/vote", response_model=PollResponse)
async def vote_poll(
    trip_id: str,
    poll_id: str,
    body: PollVoteCreate,
    user_data: dict = Depends(verify_token),
    trip_access: dict = Depends(check_trip_access),
    db: Session = Depends(get_db),
):
    """Отдать голос за вариант (один голос на участника за опрос)."""
    user_uuid = _get_user_uuid(user_data)
    trip_uuid = _parse_trip_id(trip_id)
    poll_uuid = _parse_poll_id(poll_id)
    poll = (
        db.query(Poll)
        .filter(Poll.id == poll_uuid, Poll.trip_id == trip_uuid)
        .first()
    )
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    option = (
        db.query(PollOption)
        .filter(PollOption.id == body.option_id, PollOption.poll_id == poll.id)
        .first()
    )
    if not option:
        raise HTTPException(
            status_code=400,
            detail="Option does not belong to this poll",
        )
    existing = (
        db.query(PollVote)
        .filter(PollVote.poll_id == poll.id, PollVote.user_id == user_uuid)
        .first()
    )
    if existing:
        existing.option_id = body.option_id
        db.commit()
        db.refresh(poll)
    else:
        vote = PollVote(poll_id=poll.id, option_id=body.option_id, user_id=user_uuid)
        db.add(vote)
        db.commit()
        db.refresh(poll)
    return _poll_response_with_results(db, poll)
