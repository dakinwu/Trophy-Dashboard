from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    psn_npsso: str | None = None
    cache_dir: str = "data_cache"
    cors_origins: list[str] = ["http://localhost:5173"]
    scrape_user_agent: str = "TrophyHunter/2.0 (local; hello@example.com)"


settings = Settings()
