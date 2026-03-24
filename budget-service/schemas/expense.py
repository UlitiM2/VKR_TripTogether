from pydantic import BaseModel, ConfigDict, Field, field_serializer
from datetime import datetime
from typing import Optional
from decimal import Decimal
import uuid


class ExpenseCreate(BaseModel):
    """Создание расхода: сумма, категория, между кем делим (user_ids)."""
    amount: float = Field(..., gt=0)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    paid_by_user_id: Optional[uuid.UUID] = None
    split_between: list[uuid.UUID] = Field(..., min_length=1)


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    paid_by_user_id: uuid.UUID
    amount: Decimal
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    share_count: int = 0

    @field_serializer("amount")
    def serialize_amount(self, v: Decimal):
        return float(v)


class DebtItem(BaseModel):
    """Один долг: кто кому сколько должен."""
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    amount: float


class DebtsSummary(BaseModel):
    """Итог по долгам: минимальный набор переводов для закрытия расчётов."""
    debts: list[DebtItem] = []
