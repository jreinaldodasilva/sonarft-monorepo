"""
SonarFT API Configuration
All settings driven by environment variables with sensible defaults.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API
    api_title: str = "SonarFT API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    api_debug: bool = False

    # Auth — set NETLIFY_SITE_URL for Netlify JWT validation
    # or SONARFT_API_TOKEN for static token auth.
    netlify_site_url: str = ""
    sonarft_api_token: str = ""

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Bot limits
    max_bots_per_client: int = 5

    # Data directory (shared with bot package)
    data_dir: str = "sonarftdata"

    # Logging
    log_level: str = "INFO"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # ignore unknown env vars (e.g. system LOG_LEVEL, DEBUG)


@lru_cache
def get_settings() -> Settings:
    return Settings()
