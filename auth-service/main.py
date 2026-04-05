from typing import Optional
import re
import uuid
import hashlib
import secrets
from pathlib import Path
import mimetypes
from fastapi import FastAPI, Depends, HTTPException, status, Query, Form, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import asyncio
import json
import logging
import urllib.request

from sqlalchemy import func, or_, and_
from config import settings
from db.db import engine, Base, get_db
from fastapi.staticfiles import StaticFiles
from security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token
)
from models.user import UserCreate, UserResponse, Token
from schemas.user import User, PasswordResetToken

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

BASE_DIR = Path(__file__).resolve().parent
STATIC_ROOT = BASE_DIR / "static"
AVATAR_DIR = STATIC_ROOT / "avatars"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

def _hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


FORGOT_PASSWORD_RESPONSE = (
    "Если указанный адрес зарегистрирован, мы отправили на него ссылку для сброса пароля."
)


def _send_password_reset_email_sync(to_email: str, reset_url: str) -> None:
    """POST в notification-service без httpx (stdlib — образ Docker без лишних пакетов)."""
    url = f"{settings.NOTIFICATION_SERVICE_URL.rstrip('/')}/internal/send"
    payload = {
        "event": "password_reset",
        "to_emails": [to_email],
        "data": {"reset_url": reset_url},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


async def _send_password_reset_email(to_email: str, reset_url: str) -> None:
    try:
        await asyncio.to_thread(_send_password_reset_email_sync, to_email, reset_url)
    except Exception as e:
        logger.warning("Failed to send password reset notification: %s", e)


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

app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")

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


def _user_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@app.get("/")
async def root():
    return {
        "service": "Auth Service",
        "status": "running",
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "forgot_password": "POST /auth/forgot-password",
            "reset_password": "POST /auth/reset-password",
            "change_password": "POST /auth/me/password",
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
    
    email_norm = str(user_data.email).lower().strip()
    existing_user = db.query(User).filter(func.lower(User.email) == email_norm).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    user = User(
        email=email_norm,
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
    un = (username or "").strip()
    if not un:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(
        or_(
            func.lower(User.email) == un.lower(),
            and_(User.username.isnot(None), func.lower(User.username) == un.lower()),
        )
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


@app.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db=Depends(get_db)):
    """Запрос ссылки на сброс пароля. Ответ одинаковый при отсутствии пользователя (без раскрытия email)."""
    email_norm = str(body.email).lower().strip()
    user = db.query(User).filter(func.lower(User.email) == email_norm).first()
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_password_reset_token(token),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
        )
        db.commit()
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        reset_url = f"{base}/reset-password?token={token}"
        await _send_password_reset_email(user.email, reset_url)
    return {"detail": FORGOT_PASSWORD_RESPONSE}


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    new_password: str = Field(..., min_length=8, max_length=100)


@app.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest, db=Depends(get_db)):
    """Установка нового пароля по одноразовой ссылке из письма."""
    raw = body.token.strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )
    token_hash = _hash_password_reset_token(raw)
    row = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link",
        )
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.utcnow()
    db.delete(row)
    db.commit()
    return {"detail": "Пароль успешно изменён. Можно войти."}


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
    uid = _user_uuid(current_user_id)
    user = db.query(User).filter(User.id == uid).first()
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
    uid = _user_uuid(current_user_id)
    user = db.query(User).filter(User.id == uid).first()
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
        existing = db.query(User).filter(
            func.lower(User.email) == str(body.email).lower().strip(),
            User.id != uid,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = str(body.email).lower().strip()
    if "avatar_url" in body.model_fields_set:
        user.avatar_url = body.avatar_url
    # Явно обновляем updated_at (и для сброса аватара), чтобы фронт мог сбрасывать кэш картинки
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)


@app.post("/auth/me/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Смена пароля для авторизованного пользователя (без email)."""
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен отличаться от текущего",
        )
    uid = _user_uuid(current_user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль",
        )
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"detail": "Пароль обновлён"}


@app.post("/auth/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    request: Request = None,
    current_user_id: str = Depends(get_current_user),
    db=Depends(get_db),
):
    """Загрузка аватара из файла.

    Сохраняет изображение в static/avatars и обновляет avatar_url у пользователя.
    Ограничения: только image/*, размер до 2 МБ.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно загрузить только изображение.",
        )

    content = await file.read()
    max_bytes = 2 * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Слишком большой файл аватара (максимум 2 МБ).",
        )

    # Определяем расширение
    guessed_ext = mimetypes.guess_extension(file.content_type or "") or ""
    original_ext = Path(file.filename or "").suffix
    ext = (original_ext or guessed_ext or ".png").lower()
    if len(ext) > 8 or not ext.startswith("."):
        ext = ".png"

    filename = f"{current_user_id}{ext}"
    avatar_path = AVATAR_DIR / filename
    with avatar_path.open("wb") as f:
        f.write(content)

    # Абсолютный URL, чтобы картинка открывалась и из фронтенда
    if request is not None:
        try:
            avatar_url = str(request.url_for("static", path=f"avatars/{filename}"))
        except Exception:
            avatar_url = f"/static/avatars/{filename}"
    else:
        avatar_url = f"/static/avatars/{filename}"

    uid = _user_uuid(current_user_id)
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.avatar_url = avatar_url
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/auth/internal/user/{user_id}")
async def get_user_by_id_internal(
    user_id: str,
    db=Depends(get_db),
):
    """Внутренний эндпоинт: данные пользователя по id (для user-service, уведомлений)."""
    uid = _user_uuid(user_id)
    user = db.query(User).filter(User.id == uid).first()
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