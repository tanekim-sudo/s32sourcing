"""Specter adapter — no-ops without SPECTER_API_KEY.

Specter's public API surface varies by plan; this uses a conventional
Bearer + /v1/companies search path and degrades cleanly when unavailable.
"""

from __future__ import annotations

from typing import List

import httpx

from app.adapters.base import BaseAdapter, NormalizedCandidate, ThesisQueryPlan
from app.core.config import get_settings


class SpecterAdapter(BaseAdapter):
    source = "specter"
    base_url = "https://api.specter.co"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.settings.specter_api_key}",
            "Accept": "application/json",
        }

    async def authenticate(self) -> bool:
        if not self.settings.specter_api_key:
            return False
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Soft check — 401 means bad key; other errors still mean "configured"
            resp = await client.get(f"{self.base_url}/v1/me", headers=self._headers())
            return resp.status_code in (200, 404)  # 404 if /me absent but key accepted elsewhere

    async def fetch_test_record(self) -> NormalizedCandidate:
        if not self.settings.specter_api_key:
            raise RuntimeError("SPECTER_API_KEY not set")
        results = await self.pull(
            [
                ThesisQueryPlan(
                    query_key="artificial intelligence",
                    query_payload={"query": "artificial intelligence"},
                    thesis_config_ids=[],
                )
            ]
        )
        if not results:
            raise RuntimeError(
                "Specter returned no results — confirm API base path for your plan, or check key."
            )
        return results[0]

    async def pull(self, query_plans: List[ThesisQueryPlan]) -> List[NormalizedCandidate]:
        if not self.settings.specter_api_key:
            return []

        out: List[NormalizedCandidate] = []
        async with httpx.AsyncClient(timeout=45.0) as client:
            for plan in query_plans:
                query = plan.query_payload.get("query") or plan.query_key
                resp = await client.get(
                    f"{self.base_url}/v1/companies",
                    headers=self._headers(),
                    params={"q": query, "limit": 10},
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data") or data.get("companies") or []
                for item in items:
                    out.append(
                        NormalizedCandidate(
                            source=self.source,
                            external_id=str(item.get("id") or item.get("company_id") or ""),
                            company_name=item.get("name") or item.get("company_name"),
                            domain=item.get("domain") or item.get("website"),
                            title=item.get("name"),
                            summary=item.get("description") or item.get("tagline"),
                            url=item.get("website") or item.get("url"),
                            payload=item,
                            matched_thesis_config_ids=list(plan.thesis_config_ids),
                        )
                    )
        return out
