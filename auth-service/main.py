from typing import Optional
import re
from fastapi import FastAPI, Depends, HTTPException, status, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging

from sqlalchemy import func
from config import settings
from db.db import engine, Base, get_db
from security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token
)
from models.user import UserCreate, UserResponse, Token
from schemas.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Auth Service")
    
    # Создаем таблицы в БД
    Base.metadata.create_all(bind=engine)
    
    yield
    
    logger.info("Stop Auth Service")
    engine.dispose()

app = FastAPI(
    title="TripPlanner Auth Service",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    return user_id


@app.get("/")
async def root():
    return {
        "service": "Auth Service",
        "status": "running",
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "health": "GET /health"
        }
    }


@app.get("/health")
async def health_check():
    """Эндпоинт для проверки сервиса"""
    return {
        "status": "healthy",
        "service": "auth-service"
    }


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db=Depends(get_db)):
    """Регистрация нового пользователя"""
    
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@app.post("/auth/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db)
):
    """Аутентификация пользователя"""
    
    user = db.query(User).filter(
        (User.email == username) | (User.username == username)
    ).first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post("/auth/verify")
async def verify(token: str = Depends(oauth2_scheme)):
    """Верификация JWT токена"""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email")
    }

@app.get("/auth/me", response_model=UserResponse)
async def read_users_me(current_user_id: str = Depends(get_current_user), db=Depends(get_db)):
    """Получение информации о текущем пользователе (без пароля)."""
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


class UserUpdate(BaseModel):
    """Обновление профиля (PATCH /auth/me)."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None


@app.patch("/auth/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Обновление профиля: имя, URL аватара."""
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if "full_name" in body.model_fields_set:
        if body.full_name is None:
            user.full_name = None
        else:
            cleaned = body.full_name.strip()
            if cleaned == "":
                user.full_name = None
            else:
                parts = cleaned.split()
                # ожидаем "Имя Фамилия" (1-2 слова)
                if len(parts) > 2:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Full name must contain only letters",
                    )
                letter_re = re.compile(r"^[A-Za-zА-Яа-яЁё]+$")
                for p in parts:
                    if not letter_re.fullmatch(p):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Full name must contain only letters",
                        )
                user.full_name = cleaned
    if "email" in body.model_fields_set and body.email:
        existing = db.query(User).filter(User.email == str(body.email), User.id != current_user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = str(body.email)
    if "avatar_url" in body.model_fields_set:
        user.avatar_url = body.avatar_url
    db.commit()
    db.refresh(user)
    return user


@app.get("/auth/internal/user/{user_id}")
async def get_user_by_id_internal(
    user_id: str,
    db=Depends(get_db),
):
    """Внутренний эндпоинт: данные пользователя по id (для user-service, уведомлений)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "is_active": user.is_active,
    }


@app.get("/auth/internal/user-by-email")
async def get_user_id_by_email(
    email: str = Query(..., description="Email пользователя"),
    db=Depends(get_db),
):
    """
    Внутренний эндпоинт для сервисов (trip-service).
    Возвращает id пользователя по email. Вызывается только из внутренней сети.
    """
    user = db.query(User).filter(func.lower(User.email) == email.lower().strip()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive",
        )
    return {"id": str(user.id)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )