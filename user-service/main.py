from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import logging
import httpx

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


@app.get("/profiles/{user_id}")
async def get_profile(user_id: str, user_data: dict = Depends(verify_token)):
    """Получение профиля пользователя"""
    return {
        "user_id": user_id,
        "email": user_data.get("email"),
        "profile": "User profile data here"
    }


@app.get("/profiles/me")
async def get_my_profile(user_data: dict = Depends(verify_token)):
    """Получение профиля текущего пользователя"""
    return {
        "user_id": user_data.get("user_id"),
        "email": user_data.get("email"),
        "profile": "My profile data here"
    }