from pydantic import BaseModel, Field


class AchievementItem(BaseModel):
    id: str
    icon: str
    title: str
    requirement: str
    current: int = Field(ge=0)
    target: int = Field(gt=0)
    progress: int = Field(ge=0, le=100)
    unlocked: bool


class AchievementListResponse(BaseModel):
    achievements: list[AchievementItem]

