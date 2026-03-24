from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional
import uuid


class PollOptionCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class PollCreate(BaseModel):
    """Создание опроса с вопросом и списком вариантов."""
    question: str = Field(..., min_length=1, max_length=1000)
    options: list[str] = Field(..., min_length=1, max_length=20)


class PollOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    poll_id: uuid.UUID
    text: str
    position: int = 0
    vote_count: int = 0


class PollResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    created_by: uuid.UUID
    question: str
    created_at: datetime
    options: list[PollOptionResponse] = []
    my_option_id: Optional[uuid.UUID] = None


class PollVoteCreate(BaseModel):
    option_id: uuid.UUID
