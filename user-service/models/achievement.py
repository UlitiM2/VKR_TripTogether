import uuid

from sqlalchemy import Column, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from db.db import Base


class UserAchievementProgress(Base):
    __tablename__ = "user_achievement_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_achievement_progress_user"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    progress_json = Column(JSONB, nullable=False, server_default="{}")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

