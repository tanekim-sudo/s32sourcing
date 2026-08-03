from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("s32sourcing")

settings = get_settings()

app = FastAPI(
    title="S32 Sourcing Pipeline",
    description="Shared sourcing + partner-scoped queues, rubric overlays, Affinity push.",
    version="0.1.0",
)

_cors = settings.cors_origin_list
_allow_all = _cors == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    if settings.auth_dev_bypass:
        log.warning(
            "AUTH_DEV_BYPASS is enabled — do not use in production. "
            "All requests authenticate as %s",
            settings.auth_dev_partner_email,
        )
    elif not settings.clerk_secret_key:
        log.warning("CLERK_SECRET_KEY is empty — authenticated API routes will fail")

    configured = [
        name
        for name, val in (
            ("github", settings.github_token),
            ("exa", settings.exa_api_key),
            ("specter", settings.specter_api_key),
            ("anthropic", settings.anthropic_api_key),
            ("affinity", settings.affinity_api_key),
            ("clay", settings.clay_api_key),
        )
        if val
    ]
    log.info("configured source keys: %s", configured or ["none"])


@app.get("/")
def root() -> dict:
    return {"service": "s32sourcing", "docs": "/docs"}
