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
    cors_origins: list[str] = ["http://localhost:5173"]
    scrape_user_agent: str = "TrophyHunter/2.0 (local; hello@example.com)"
    # Headed Chrome is intentional: PSNProfiles' Cloudflare challenge detects
    # headless automation.
    psnprofiles_headless: bool = False
    psnprofiles_browser_timeout: float = 180.0


settings = Settings()
