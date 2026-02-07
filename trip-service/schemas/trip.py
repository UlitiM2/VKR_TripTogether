from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
import uuid

class TripCreate(BaseModel):
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: Optional[float] = None
    description: Optional[str] = None

class TripResponse(BaseModel):
    id: uuid.UUID
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: Optional[float] = None
    description: Optional[str] = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True