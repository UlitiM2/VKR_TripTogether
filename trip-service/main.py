from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import os
import uuid
from datetime import datetime

import httpx

from db.db import engine, Base, get_db
from models.trip import Trip
from models.participant import TripParticipant, ParticipantRole
from schemas.trip import TripCreate, TripResponse
from schemas.participant import InviteCreate, InviteResponse, ParticipantResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

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
            
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


async def resolve_user_id_by_email(email: str) -> uuid.UUID:
    """Получить user_id по email через Auth Service (внутренний вызов)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/auth/internal/user-by-email",
                params={"email": email},
                timeout=5.0,
            )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User with this email not found",
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Auth service error",
                )
            data = response.json()
            return uuid.UUID(data["id"])
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")


def get_trip_if_accessible(
    db: Session, trip_id: str, user_id: uuid.UUID
) -> Trip:
    """Вернуть поездку, если пользователь — создатель или участник. Иначе 403/404."""
    try:
        trip_uuid = uuid.UUID(trip_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    trip = db.query(Trip).filter(Trip.id == trip_uuid).first()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )
    if trip.created_by == user_id:
        return trip
    participant = (
        db.query(TripParticipant)
        .filter(
            TripParticipant.trip_id == trip_uuid,
            TripParticipant.user_id == user_id,
        )
        .first()
    )
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip",
        )
    return trip


def is_trip_organizer(trip: Trip, user_id: uuid.UUID, db: Session) -> bool:
    """Проверка, что пользователь — организатор (создатель или участник с ролью organizer)."""
    if trip.created_by == user_id:
        return True
    p = (
        db.query(TripParticipant)
        .filter(
            TripParticipant.trip_id == trip.id,
            TripParticipant.user_id == user_id,
            TripParticipant.role == ParticipantRole.organizer.value,
        )
        .first()
    )
    return p is not None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Trip Service")
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    yield
    
    logger.info("Trip Service stopped")
    engine.dispose()

app = FastAPI(
    title="TripPlanner Trip Service",
    lifespan=lifespan
)

@app.get("/")
async def root():
    return {
        "service": "Trip Service",
        "status": "running",
        "endpoints": {
            "create_trip": "POST /trips",
            "get_trips": "GET /trips",
            "get_trip": "GET /trips/{trip_id}",
            "delete_trip": "DELETE /trips/{trip_id}",
            "invite": "POST /trips/{trip_id}/participants/invite",
            "list_participants": "GET /trips/{trip_id}/participants",
            "accept_invite": "PATCH /trips/{trip_id}/participants/me/accept",
        },
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "trip-service"}


@app.post("/trips", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    trip: TripCreate, 
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Создание новой поездки"""
    user_id_str = user_data.get("user_id") or user_data.get("sub")
    
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token"
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    db_trip = Trip(
        title=trip.title,
        description=trip.description,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        created_by=user_id  
    )
    
    db.add(db_trip)
    db.flush()
    participant = TripParticipant(
        trip_id=db_trip.id,
        user_id=user_id,
        role=ParticipantRole.organizer.value,
        accepted_at=db_trip.created_at,
    )
    db.add(participant)
    db.commit()
    db.refresh(db_trip)

    logger.info(f"Trip created: {db_trip.id} by user {user_id}")

    return db_trip

@app.get("/trips", response_model=list[TripResponse])
async def get_trips(
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Получение всех поездок пользователя"""
    user_id_str = user_data.get("user_id") or user_data.get("sub")
    
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found in token"
        )
    
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    subq = db.query(TripParticipant.trip_id).filter(
        TripParticipant.user_id == user_id
    )
    trips = (
        db.query(Trip)
        .filter(or_(Trip.created_by == user_id, Trip.id.in_(subq)))
        .distinct()
        .all()
    )

    logger.info(f"Returning {len(trips)} trips for user {user_id}")
    return trips

@app.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Получение конкретной поездки (доступно создателю и участникам)."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    trip = get_trip_if_accessible(db, trip_id, user_uuid)
    return trip

@app.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Удаление поездки (только организатор/создатель)."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    trip = get_trip_if_accessible(db, trip_id, user_uuid)
    if trip.created_by != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trip organizer can delete the trip",
        )
    db.delete(trip)
    db.commit()
    return {"message": "Trip deleted successfully"}


# ---------- Участники и приглашения ----------


@app.post(
    "/trips/{trip_id}/participants/invite",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_participant(
    trip_id: str,
    body: InviteCreate,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Пригласить участника по email (только организатор поездки)."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    trip = get_trip_if_accessible(db, trip_id, user_uuid)
    if trip.created_by != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trip organizer can invite participants",
        )

    invitee_id = await resolve_user_id_by_email(body.email)
    if invitee_id == user_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite yourself",
        )

    existing = (
        db.query(TripParticipant)
        .filter(
            TripParticipant.trip_id == trip.id,
            TripParticipant.user_id == invitee_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a participant or invited",
        )

    participant = TripParticipant(
        trip_id=trip.id,
        user_id=invitee_id,
        role=ParticipantRole.member.value,
        accepted_at=None,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)

    logger.info(f"Invited user {invitee_id} to trip {trip_id}")
    return InviteResponse(
        message="Invitation sent",
        participant=ParticipantResponse.model_validate(participant),
    )


@app.get("/trips/{trip_id}/participants", response_model=list[ParticipantResponse])
async def list_participants(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Список участников поездки (доступно всем участникам поездки)."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    trip = get_trip_if_accessible(db, trip_id, user_uuid)
    participants = (
        db.query(TripParticipant)
        .filter(TripParticipant.trip_id == trip.id)
        .all()
    )
    return participants


@app.get("/trips/{trip_id}/internal/check-access")
async def check_trip_access_internal(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Внутренний эндпоинт для других сервисов (voting-service). Проверяет, что пользователь — создатель или участник поездки. Возвращает 200 или 403/404."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    get_trip_if_accessible(db, trip_id, user_uuid)
    return {"ok": True}


@app.patch("/trips/{trip_id}/participants/me/accept")
async def accept_invitation(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Принять приглашение в поездку (установить accepted_at для текущего пользователя)."""
    user_uuid = uuid.UUID(user_data.get("user_id") or user_data.get("sub"))
    get_trip_if_accessible(db, trip_id, user_uuid)

    trip = get_trip_if_accessible(db, trip_id, user_uuid)
    participant = (
        db.query(TripParticipant)
        .filter(
            TripParticipant.trip_id == trip.id,
            TripParticipant.user_id == user_uuid,
        )
        .first()
    )
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a participant of this trip",
        )
    if participant.accepted_at:
        return {
            "message": "Invitation already accepted",
            "participant": ParticipantResponse.model_validate(participant),
        }

    participant.accepted_at = datetime.utcnow()
    db.commit()
    db.refresh(participant)
    return {"message": "Invitation accepted", "participant": ParticipantResponse.model_validate(participant)}