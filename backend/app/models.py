from pydantic import BaseModel, Field


class TrophyCounts(BaseModel):
    total: int = 0
    platinum: int = 0
    gold: int = 0
    silver: int = 0
    bronze: int = 0


class ProfileSummary(BaseModel):
    username: str
    avatar_url: str | None = None
    total_trophies: TrophyCounts = Field(default_factory=TrophyCounts)
    stats: dict[str, str] = Field(default_factory=dict)


class Trophy(BaseModel):
    game: str
    icon_url: str
    title: str
    timestamp: str
    rarity_percent: str
    grade: str


class ProfileData(BaseModel):
    profile_summary: ProfileSummary
    trophy_log: list[Trophy] = Field(default_factory=list)
