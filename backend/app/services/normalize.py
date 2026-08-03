from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.adapters.base import NormalizedCandidate
from app.models.entities import Signal
from app.services.entity_resolution import upsert_company


def ingest_candidates(
    db: Session,
    candidates: List[NormalizedCandidate],
) -> dict:
    """Normalize candidates into firm-wide companies + signals. Dedupes companies."""
    created_companies = 0
    created_signals = 0
    company_ids: List[int] = []

    for cand in candidates:
        name = cand.company_name or cand.title or "Unknown"
        company, created = upsert_company(
            db,
            name=name,
            domain=cand.domain,
            description=cand.summary,
            raw_payload={"source": cand.source, "external_id": cand.external_id},
        )
        if created:
            created_companies += 1
        company_ids.append(company.id)

        if cand.external_id:
            existing = (
                db.query(Signal)
                .filter(Signal.source == cand.source, Signal.external_id == cand.external_id)
                .one_or_none()
            )
            if existing:
                # Merge thesis tags
                merged = set(existing.matched_thesis_config_ids or [])
                merged.update(cand.matched_thesis_config_ids or [])
                existing.matched_thesis_config_ids = sorted(merged)
                existing.company_id = company.id
                if cand.summary and not existing.summary:
                    existing.summary = cand.summary
                db.add(existing)
                continue

        signal = Signal(
            company_id=company.id,
            source=cand.source,
            external_id=cand.external_id,
            title=cand.title,
            summary=cand.summary,
            url=cand.url,
            payload=cand.payload or {},
            matched_thesis_config_ids=list(cand.matched_thesis_config_ids or []),
            observed_at=datetime.now(timezone.utc),
        )
        db.add(signal)
        created_signals += 1

    db.commit()
    return {
        "candidates": len(candidates),
        "companies_created": created_companies,
        "signals_created": created_signals,
        "company_ids": sorted(set(company_ids)),
    }
