from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint, Integer, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from db.db import Base


class Poll(Base):
    """Опрос в рамках поездки (например: «Какой отель выбрать?»)."""
    __tablename__ = "polls"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    trip_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    question = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class PollOption(Base):
    """Вариант ответа в опросе."""
    __tablename__ = "poll_options"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    poll_id = Column(
        UUID(as_uuid=True),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(String(500), nullable=False)
    position = Column(Integer, default=0)


class PollVote(Base):
    """Голос участника за вариант. Один голос на пользователя за опрос."""
    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "user_id", name="uq_poll_user"),)

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    poll_id = Column(
        UUID(as_uuid=True),
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_id = Column(
        UUID(as_uuid=True),
        ForeignKey("poll_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
