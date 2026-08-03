"""Exa (Websets / search) adapter — no-ops without EXA_API_KEY."""

from __future__ import annotations

from typing import List
from urllib.parse import urlparse

import httpx

from app.adapters.base import BaseAdapter, NormalizedCandidate, ThesisQueryPlan
from app.core.config import get_settings


class ExaAdapter(BaseAdapter):
    source = "exa"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def authenticate(self) -> bool:
        return bool(self.settings.exa_api_key)

    async def fetch_test_record(self) -> NormalizedCandidate:
        if not await self.authenticate():
            raise RuntimeError("EXA_API_KEY not set")
        results = await self.pull(
            [
                ThesisQueryPlan(
                    query_key="ai infrastructure startups",
                    query_payload={"query": "AI infrastructure startups"},
                    thesis_config_ids=[],
                )
            ]
        )
        if not results:
            raise RuntimeError("Exa returned no results for test query")
        return results[0]

    async def pull(self, query_plans: List[ThesisQueryPlan]) -> List[NormalizedCandidate]:
        if not self.settings.exa_api_key:
            return []

        out: List[NormalizedCandidate] = []
        async with httpx.AsyncClient(timeout=45.0) as client:
            for plan in query_plans:
                query = plan.query_payload.get("query") or plan.query_key
                resp = await client.post(
                    "https://api.exa.ai/search",
                    headers={
                        "x-api-key": self.settings.exa_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "type": "auto",
                        "numResults": 10,
                        "contents": {"text": {"maxCharacters": 500}},
                    },
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("results", []):
                    url = item.get("url")
                    domain = urlparse(url).netloc if url else None
                    out.append(
                        NormalizedCandidate(
                            source=self.source,
                            external_id=item.get("id") or url,
                            company_name=item.get("title"),
                            domain=domain,
                            title=item.get("title"),
                            summary=(item.get("text") or item.get("summary") or "")[:1000],
                            url=url,
                            payload=item,
                            matched_thesis_config_ids=list(plan.thesis_config_ids),
                        )
                    )
        return out
