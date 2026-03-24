import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import httpx

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting User Service")
    yield
    logger.info("User Service stopped")

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