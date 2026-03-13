from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional
import uuid


class InviteCreate(BaseModel):
    """Тело запроса приглашения по email."""
    email: EmailStr


class ParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None


class InviteResponse(BaseModel):
    """Ответ после успешного приглашения."""
    message: str
    participant: ParticipantResponse
