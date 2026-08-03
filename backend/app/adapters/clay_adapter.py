"""Clay enrichment — async webhook in/out only (no search schedule)."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict, Optional

from app.core.config import get_settings


class ClayAdapter:
    source = "clay"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def enqueue_enrichment(self, company_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.settings.clay_api_key:
            return {
                "status": "dry_run",
                "reason": "CLAY_API_KEY not set",
                "company_id": company_id,
                "payload": payload,
            }
        # Clay table/webhook URLs are workspace-specific; store intent until configured.
        return {
            "status": "queued_local",
            "company_id": company_id,
            "note": "Configure Clay table webhook URL in env when ready.",
            "payload": payload,
        }

    def verify_signature(self, body: bytes, signature: Optional[str]) -> bool:
        secret = self.settings.clay_webhook_secret
        if not secret:
            return True  # allow in scaffold; tighten when secret is set
        if not signature:
            return False
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature.replace("sha256=", ""))

    async def handle_webhook(self, body: Dict[str, Any], signature: Optional[str] = None) -> Dict[str, Any]:
        return {
            "status": "accepted",
            "company_domain": body.get("domain") or body.get("company_domain"),
            "enrichment": body.get("enrichment") or body,
        }
