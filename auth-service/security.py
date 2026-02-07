from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt  
import os

from config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля"""
    plain_bytes = plain_password.encode('utf-8')
    
    
    if len(plain_bytes) > 72: # поработать с паролем
        plain_bytes = plain_bytes[:72]
    
    return bcrypt.checkpw(plain_bytes, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Хэширование пароля"""
    password_bytes = password.encode('utf-8')

    if len(password_bytes) > 72: # поработать с паролем
        password_bytes = password_bytes[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Создание JWT токена"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Верификация JWT токена"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None