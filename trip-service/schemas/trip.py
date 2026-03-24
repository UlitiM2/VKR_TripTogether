from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from typing import Optional
import uuid


class TripCreate(BaseModel):
    title: str
    destination: Optional[str] = None
    start_date: date
    end_date: date
    budget: Optional[float] = None
    description: Optional[str] = None


class TripUpdate(BaseModel):
    title: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    destination: Optional[str] = None
    start_date: date
    end_date: date
    budget: Optional[float] = None
    description: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_organizer: bool = False