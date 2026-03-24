from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid


class MessageCreate(BaseModel):
    """Создание сообщения: только текст."""
    content: str = Field(..., min_length=1, max_length=10_000)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    author_user_id: uuid.UUID
    content: str
    created_at: datetime
