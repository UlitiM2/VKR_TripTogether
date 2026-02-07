from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import httpx
import uuid

from db.db import engine, Base, get_db
from models.trip import Trip
from schemas.trip import TripCreate, TripResponse
from sqlalchemy.orm import Session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Верификация токена через Auth Service"""
    token = credentials.credentials
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://auth-service:8000/auth/verify",
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
            "get_trip": "GET /trips/{trip_id}"
        }
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
    
    trips = db.query(Trip).filter(Trip.created_by == user_id).all()
    
    logger.info(f"Returning {len(trips)} trips for user {user_id}")
    return trips

@app.get("/trips/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: str, user_data: dict = Depends(verify_token),db: Session = Depends(get_db)):
    """Получение конкретной поездки"""
    user_id = user_data.get("user_id") or user_data.get("sub")
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    user_uuid = uuid.UUID(user_id)

    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.created_by != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this trip"
        )
    
    return trip

@app.delete("/trips/{trip_id}")
async def delete_trip(
    trip_id: str,
    user_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Удаление поездки"""
    user_id = user_data.get("user_id") or user_data.get("sub")
    user_uuid = uuid.UUID(user_id)
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.created_by != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this trip"
        )
    
    db.delete(trip)
    db.commit()
    
    return {"message": "Trip deleted successfully"}