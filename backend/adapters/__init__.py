"""Public adapter package path (/backend/adapters) — re-exports app.adapters."""

from app.adapters.base import BaseAdapter, NormalizedCandidate, ThesisQueryPlan, dedupe_thesis_queries
from app.adapters.clay_adapter import ClayAdapter
from app.adapters.exa_adapter import ExaAdapter
from app.adapters.github_adapter import GitHubAdapter
from app.adapters.specter_adapter import SpecterAdapter

__all__ = [
    "BaseAdapter",
    "NormalizedCandidate",
    "ThesisQueryPlan",
    "dedupe_thesis_queries",
    "SpecterAdapter",
    "ExaAdapter",
    "GitHubAdapter",
    "ClayAdapter",
]
