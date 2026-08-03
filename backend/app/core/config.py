from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
THRESHOLDS_PATH = REPO_ROOT / "config" / "thresholds.yaml"


def _normalize_database_url(url: str) -> str:
    """Render/Heroku give postgres:// — SQLAlchemy+psycopg needs postgresql+psycopg://."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://s32:s32@localhost:5432/s32sourcing"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # Adapter keys (populated later; adapters stay stubbed until set)
    specter_api_key: str = ""
    exa_api_key: str = ""
    github_token: str = ""
    clay_api_key: str = ""
    clay_webhook_secret: str = ""
    anthropic_api_key: str = ""
    affinity_api_key: str = ""
    affinity_base_url: str = "https://api.affinity.co"

    # Dev-only: skip Clerk JWT verification and use this partner email
    auth_dev_bypass: bool = False
    auth_dev_partner_email: str = "dev@s32.com"

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Convenience: allow all Vercel preview/prod URLs when wildcard marker set
        if "*" in origins:
            return ["*"]
        return origins


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_url = _normalize_database_url(settings.database_url)
    return settings


@lru_cache
def get_thresholds() -> dict:
    with THRESHOLDS_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
