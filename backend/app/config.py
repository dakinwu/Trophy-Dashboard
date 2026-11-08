from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Read the repo-root .env first (where the PSN NPSSO token lives), then
    # allow an optional backend/.env to override it. Later files win.
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), str(_REPO_ROOT / "backend" / ".env")),
        extra="ignore",
    )

    psn_npsso: str | None = None
    # Absolute so the cache location doesn't depend on the process's CWD.
    cache_dir: str = str(_REPO_ROOT / "backend" / "data_cache")
    cors_origins: list[str] = ["http://localhost:5174"]
    scrape_user_agent: str = "TrophyHunter/2.0 (local; hello@example.com)"
    # Headed Chrome is intentional: PSNProfiles' Cloudflare challenge detects
    # headless automation.
    psnprofiles_headless: bool = False
    psnprofiles_browser_timeout: float = 180.0
    # Optional: resolves localized PlayStation titles to canonical English names
    # before Trophy Advisor searches PSNProfiles. Kept backend-only.
    gemini_api_key: str | None = None
    # Search-grounded bundle/collection research is deliberately separated
    # from PSNProfiles scraping while reusing the same backend-only key.
    gemini_grounding_model: str = "gemini-2.5-flash"
    gemini_timeout: float = 60.0


settings = Settings()
