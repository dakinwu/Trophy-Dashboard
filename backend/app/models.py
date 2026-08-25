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
    is_dlc: bool = False


class GameTrophyDetail(BaseModel):
    game: str
    display_name: str
    platforms: list[Platform] = Field(default_factory=lambda: ["UNKNOWN"])
    trophies: list[Trophy] = Field(default_factory=list)
    complete: bool = False
    source: Literal["psn", "psnprofiles", "profile_log"] = "profile_log"


class PlatinumGame(BaseModel):
    game: str
    platforms: list[Platform] = Field(default_factory=lambda: ["UNKNOWN"])
    icon_url: str


class ProfileData(BaseModel):
    profile_summary: ProfileSummary
    trophy_log: list[Trophy] = Field(default_factory=list)
    platinum_games: list[PlatinumGame] = Field(default_factory=list)
    summary_only: bool = False
    profile_source: Literal["psn", "psnprofiles"] | None = None
    cache_status: Literal["live", "cached"] | None = None
    fetched_at: str | None = None
    # Game title -> real playtime in seconds (PSN API source only; empty otherwise).
    game_playtime_seconds: dict[str, int] = Field(default_factory=dict)


class AdvisorGame(BaseModel):
    title_id: str
    product_id: str | None = None
    concept_id: str | None = None
    name: str
    platform: Platform = "UNKNOWN"
    available_platforms: list[Platform] = Field(default_factory=list)
    image_url: str | None = None
    source: Literal["purchased", "ps_plus", "other"] = "other"
    is_downloadable: bool = False
    is_preorder: bool = False
    library_index: int
    played: bool = False
    status: Literal["unplayed", "in_progress", "completed"] = "unplayed"
    progress: int | None = None
    playtime_seconds: int | None = None
    earned_trophies: int | None = None
    defined_trophies: int | None = None
    earned_platinum: int | None = None
    trophy_title: str | None = None
    ps4_platinum_earned: bool = False
    ps4_to_ps5_autopop: Literal["full", "partial", "none", "unknown"] | None = None
    autopop_note: str | None = None
    autopop_source_url: str | None = None
    autopop_verified_at: str | None = None


class AdvisorLibrary(BaseModel):
    username: str
    games: list[AdvisorGame] = Field(default_factory=list)
    total_count: int = 0
    unplayed_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    excluded_trial_count: int = 0
    excluded_content_count: int = 0
    excluded_platinum_count: int = 0
    merged_platform_count: int = 0
    cache_status: Literal["live", "cached"] = "live"
    fetched_at: str | None = None
    source: Literal["official_psn"] = "official_psn"
    title_resolver: Literal["gemini", "source_title"] = "source_title"


class AdvisorCandidate(BaseModel):
    game: str = Field(min_length=1, max_length=200)
    platform: Platform | None = None
    aliases: list[str] = Field(default_factory=list, max_length=4)
    title_id: str | None = Field(default=None, max_length=100)
    product_id: str | None = Field(default=None, max_length=150)


class PsnprofilesAdvisorSignals(BaseModel):
    title: str
    platform: str
    game_url: str
    owners: int | None = None
    average_completion: float | None = None
    platinum_achievers: int | None = None
    platinum_rate: float | None = None


class AdvisorBundleChildResult(BaseModel):
    game: str
    platform: Platform | None = None
    signals: PsnprofilesAdvisorSignals | None = None
    error: str | None = None


class AdvisorBundleResult(BaseModel):
    source: Literal["curated", "gemini_grounding"]
    source_urls: list[str] = Field(default_factory=list)
    verified_at: str
    children: list[AdvisorBundleChildResult] = Field(default_factory=list)
    complete: bool = False


class AdvisorSignalResult(BaseModel):
    game: str
    platform: Platform | None = None
    signals: PsnprofilesAdvisorSignals | None = None
    bundle: AdvisorBundleResult | None = None
    error: str | None = None
    retryable: bool = True


class AdvisorBatchRequest(BaseModel):
    candidates: list[AdvisorCandidate] = Field(min_length=1, max_length=50)


class AdvisorBatchResponse(BaseModel):
    results: list[AdvisorSignalResult] = Field(default_factory=list)
