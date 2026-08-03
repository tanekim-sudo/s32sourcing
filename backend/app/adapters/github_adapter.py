"""GitHub adapter — topic/search pulls; smoke-test works with GITHUB_TOKEN."""

from __future__ import annotations

from typing import List

import httpx

from app.adapters.base import BaseAdapter, NormalizedCandidate, ThesisQueryPlan
from app.core.config import get_settings


class GitHubAdapter(BaseAdapter):
    source = "github"

    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    async def authenticate(self) -> bool:
        if not self.settings.github_token:
            return False
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.github.com/user", headers=self._headers())
            return resp.status_code == 200

    async def fetch_test_record(self) -> NormalizedCandidate:
        token = self.settings.github_token
        if not token:
            raise RuntimeError("GITHUB_TOKEN not set")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.github.com/user", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return NormalizedCandidate(
            source=self.source,
            external_id=str(data.get("id")),
            company_name=data.get("company") or data.get("login"),
            domain=None,
            title=f"GitHub user @{data.get('login')}",
            summary=data.get("bio"),
            url=data.get("html_url"),
            payload=data,
            matched_thesis_config_ids=[],
        )

    async def pull(self, query_plans: List[ThesisQueryPlan]) -> List[NormalizedCandidate]:
        if not self.settings.github_token:
            return []

        out: List[NormalizedCandidate] = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for plan in query_plans:
                topic = plan.query_payload.get("query") or plan.query_key
                # Search repositories by topic / keywords
                q = f"topic:{topic}" if " " not in topic else topic
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    headers=self._headers(),
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": 10},
                )
                if resp.status_code != 200:
                    continue
                for repo in resp.json().get("items", []):
                    out.append(
                        NormalizedCandidate(
                            source=self.source,
                            external_id=str(repo.get("id")),
                            company_name=(repo.get("owner") or {}).get("login") or repo.get("name"),
                            domain=None,
                            title=repo.get("full_name"),
                            summary=repo.get("description"),
                            url=repo.get("html_url"),
                            payload=repo,
                            matched_thesis_config_ids=list(plan.thesis_config_ids),
                        )
                    )
        return out
