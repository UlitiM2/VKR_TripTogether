import uuid

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.db import Base


class UserTripLayout(Base):
    __tablename__ = "user_trip_layouts"
    __table_args__ = (
        UniqueConstraint("user_id", "trip_id", name="uq_user_trip_layout_user_trip"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    trip_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    layout_json = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

