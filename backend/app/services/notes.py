from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.models.entities import Company, Partner, Signal, ThesisConfig


def generate_why_note(
    *,
    company: Company,
    score: Dict[str, Any],
    signals: List[Signal],
) -> str:
    """Shared evidence-grounded note — one per company off the base score pass."""
    total = score.get("total_score")
    subscores = score.get("subscores") or {}
    evidence = score.get("evidence") or {}

    # Pick top positive-contributing dimensions by subscore
    ranked = sorted(
        (
            (dim, float(v.get("score", 0) if isinstance(v, dict) else v or 0))
            for dim, v in subscores.items()
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    top = [d for d, _ in ranked[:2]]
    cites: List[str] = []
    for dim in top:
        ev = evidence.get(dim) or {}
        for c in (ev.get("citations") or [])[:2]:
            if c and c not in cites:
                cites.append(str(c))

    if not cites:
        for s in signals[:2]:
            if s.title:
                cites.append(s.title)
            elif s.url:
                cites.append(s.url)

    cite_str = "; ".join(cites[:3]) if cites else "limited public signal so far"
    top_str = " and ".join(top) if top else "overall fit"
    return (
        f"{company.name} scores {total} on the firm base rubric, led by {top_str}. "
        f"Evidence: {cite_str}."
    )


def generate_partner_line(
    *,
    partner: Partner,
    thesis: ThesisConfig,
    company: Company,
    signals: List[Signal],
) -> Optional[str]:
    """One short extra line when a company strongly matches a partner thesis/watchlist."""
    keywords = [str(k).lower() for k in (thesis.keywords or [])]
    blob = " ".join(
        filter(
            None,
            [company.name, company.description]
            + [f"{s.title} {s.summary}" for s in signals],
        )
    ).lower()
    hits = [k for k in keywords if k and k in blob]
    if not hits and thesis.id not in {
        tid for s in signals for tid in (s.matched_thesis_config_ids or [])
    }:
        return None

    reason = hits[0] if hits else thesis.name
    return f"Also fits {partner.name}'s thesis on {thesis.name} because of {reason}."
