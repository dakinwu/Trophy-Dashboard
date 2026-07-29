from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal["PS3", "PS4", "PS5", "PSVITA", "PSPC", "UNKNOWN"]


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
    platforms: list[Platform] = Field(default_factory=lambda: ["UNKNOWN"])
    icon_url: str
    title: str
    description: str | None = None
    timestamp: str
    earned: bool = True
    rarity_percent: str
    rarity_source: Literal["psn", "psnprofiles", "unknown"] = "unknown"
    rarity_label: str | None = None
    psn_rarity_percent: str | None = None
    psnprofiles_rarity_percent: str | None = None
    grade: str
    trophy_id: int | None = None


class GameTrophyDetail(BaseModel):
    game: str
    display_name: str
    platforms: list[Platform] = Field(default_factory=lambda: ["UNKNOWN"])
    trophies: list[Trophy] = Field(default_factory=list)
    complete: bool = False
    source: Literal["psn", "psnprofiles", "profile_log"] = "profile_log"


class ProfileData(BaseModel):
    profile_summary: ProfileSummary
    trophy_log: list[Trophy] = Field(default_factory=list)
    # Game title -> real playtime in seconds (PSN API source only; empty otherwise).
    game_playtime_seconds: dict[str, int] = Field(default_factory=dict)
