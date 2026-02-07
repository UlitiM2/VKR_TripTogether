from sqlalchemy import Column, String, Text, Date, Numeric, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.db import Base

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4, 
        index=True
    )
    title = Column(String(255), nullable=False)
    destination = Column(String(255))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Numeric(10, 2)) 
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())