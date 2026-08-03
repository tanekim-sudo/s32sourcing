from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class NormalizedCandidate:
    """Source-agnostic candidate before firm-wide entity resolution."""

    source: str
    external_id: Optional[str]
    company_name: Optional[str]
    domain: Optional[str]
    title: Optional[str]
    summary: Optional[str]
    url: Optional[str]
    payload: Dict[str, Any] = field(default_factory=dict)
    matched_thesis_config_ids: List[int] = field(default_factory=list)


@dataclass
class ThesisQueryPlan:
    """Deduped query plan across partners' overlapping thesis configs."""

    query_key: str
    query_payload: Dict[str, Any]
    thesis_config_ids: List[int]


def dedupe_thesis_queries(
    thesis_configs: Sequence[Dict[str, Any]],
    *,
    field: str,
) -> List[ThesisQueryPlan]:
    """
    Collapse near-identical thesis queries so we don't pay twice for the same pull.

    Groups by normalized string equality of each query string in `field`
    (keywords / exa_queries / github_topics).
    """
    buckets: Dict[str, ThesisQueryPlan] = {}
    for cfg in thesis_configs:
        cfg_id = int(cfg["id"])
        for raw in cfg.get(field) or []:
            if isinstance(raw, dict):
                key = str(raw.get("query") or raw.get("topic") or raw).strip().lower()
                payload = dict(raw)
            else:
                key = str(raw).strip().lower()
                payload = {"query": str(raw).strip()}
            if not key:
                continue
            if key not in buckets:
                buckets[key] = ThesisQueryPlan(
                    query_key=key,
                    query_payload=payload,
                    thesis_config_ids=[cfg_id],
                )
            elif cfg_id not in buckets[key].thesis_config_ids:
                buckets[key].thesis_config_ids.append(cfg_id)
    return list(buckets.values())


class BaseAdapter(ABC):
    source: str

    @abstractmethod
    async def authenticate(self) -> bool:
        """Validate credentials; return True if usable."""

    @abstractmethod
    async def fetch_test_record(self) -> NormalizedCandidate:
        """Pull one record to prove auth + parsing works."""

    @abstractmethod
    async def pull(
        self,
        query_plans: List[ThesisQueryPlan],
    ) -> List[NormalizedCandidate]:
        """Pull candidates for a deduped thesis query plan."""
