from pydantic import BaseModel, Field
from typing import Any


class TripLayoutPayload(BaseModel):
    layouts: dict[str, Any] = Field(default_factory=dict)
    collapsed: dict[str, bool] = Field(default_factory=dict)

