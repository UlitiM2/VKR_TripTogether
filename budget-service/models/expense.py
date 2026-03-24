from sqlalchemy import Column, String, Text, Numeric, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from db.db import Base


class Expense(Base):
    """Расход по поездке: кто оплатил, сумма, категория, между кем делим."""
    __tablename__ = "expenses"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    trip_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    paid_by_user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ExpenseShare(Base):
    """Участник расхода: между кем делим (включая плательщика)."""
    __tablename__ = "expense_shares"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    expense_id = Column(
        UUID(as_uuid=True),
        ForeignKey("expenses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
