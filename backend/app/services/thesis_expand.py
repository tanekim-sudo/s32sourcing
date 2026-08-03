from __future__ import annotations

from typing import Any, Dict, List


def expand_tracking_topics(topics: List[str]) -> Dict[str, List[Any]]:
    """
    Turn partner-friendly topic phrases into pipeline search fields.

    Partners never see Exa/GitHub jargon — we derive those here.
    """
    cleaned = []
    for raw in topics:
        t = str(raw).strip()
        if t and t not in cleaned:
            cleaned.append(t)

    keywords = list(cleaned)
    exa_queries = [f"{t} startups" for t in cleaned]
    github_topics = [
        t.lower().replace("&", " and ").replace("/", " ").replace("  ", " ").replace(" ", "-")
        for t in cleaned
    ]
    return {
        "keywords": keywords,
        "exa_queries": exa_queries,
        "github_topics": github_topics,
    }
