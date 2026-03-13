from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from db.db import Base


class ParticipantRole(str, enum.Enum):
    organizer = "organizer"
    member = "member"


class TripParticipant(Base):
    """Участник поездки. Создатель поездки добавляется как organizer при создании поездки."""
    __tablename__ = "trip_participants"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String(20), nullable=False, default=ParticipantRole.member.value)
    invited_at = Column(DateTime, server_default=func.now())
    accepted_at = Column(DateTime, nullable=True)  # None = приглашение не принято

    def __repr__(self):
        return f"<TripParticipant(trip_id={self.trip_id}, user_id={self.user_id}, role={self.role})>"
