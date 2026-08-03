from __future__ import annotations

from typing import List, Optional, Set

import yaml
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.schemas import QueueCompanyOut
from app.core.config import REPO_ROOT
from app.models.entities import (
    Company,
    Partner,
    RubricBase,
    RubricOverlay,
    Score,
    Signal,
    ThesisConfig,
    WatchlistEntry,
)
from app.services.overlay_scoring import apply_overlay


def _active_base_weights(db: Session) -> tuple[Optional[str], dict]:
    active = (
        db.query(RubricBase)
        .filter(RubricBase.is_active.is_(True))
        .order_by(RubricBase.created_at.desc())
        .first()
    )
    if active is None:
        # Fall back to repo YAML until DB is seeded
        path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        weights = {k: float(v.get("weight", 0)) for k, v in (data.get("dimensions") or {}).items()}
        return data.get("version"), weights

    data = yaml.safe_load(active.yaml_content)
    weights = {k: float(v.get("weight", 0)) for k, v in (data.get("dimensions") or {}).items()}
    return active.version, weights


def _partner_thesis_ids(db: Session, partner: Partner) -> List[int]:
    rows = (
        db.query(ThesisConfig.id)
        .filter(
            ThesisConfig.is_active.is_(True),
            or_(
                ThesisConfig.partner_id == partner.id,
                ThesisConfig.is_shared.is_(True),
                ThesisConfig.partner_id.is_(None),
            ),
        )
        .all()
    )
    return [r[0] for r in rows]


def my_queue(db: Session, partner: Partner, limit: int = 50) -> List[QueueCompanyOut]:
    """Team queue filtered to partner thesis/watchlist, ranked by overlay score."""
    thesis_ids = _partner_thesis_ids(db, partner)
    watchlist_company_ids: Set[int] = {
        r[0]
        for r in db.query(WatchlistEntry.company_id)
        .filter(WatchlistEntry.partner_id == partner.id)
        .all()
    }

    # Companies with signals matching partner/shared thesis configs
    thesis_company_ids: Set[int] = set()
    if thesis_ids:
        signals = db.query(Signal.company_id, Signal.matched_thesis_config_ids).filter(
            Signal.company_id.isnot(None)
        )
        for company_id, matched in signals:
            if company_id and matched and any(t in matched for t in thesis_ids):
                thesis_company_ids.add(company_id)

    company_ids = watchlist_company_ids | thesis_company_ids
    if not company_ids:
        return []

    base_version, base_weights = _active_base_weights(db)
    overlay = (
        db.query(RubricOverlay)
        .filter(RubricOverlay.partner_id == partner.id, RubricOverlay.is_active.is_(True))
        .order_by(RubricOverlay.created_at.desc())
        .first()
    )

    companies = db.query(Company).filter(Company.id.in_(company_ids)).all()
    score_q = db.query(Score)
    if base_version:
        score_q = score_q.filter(Score.rubric_base_version == base_version)
    scores = {s.company_id: s for s in score_q.filter(Score.company_id.in_(company_ids)).all()}

    items: List[QueueCompanyOut] = []
    for company in companies:
        score = scores.get(company.id)
        base_total = score.total_score if score else None
        overlay_score = None
        if score and overlay:
            overlay_score, _ = apply_overlay(
                base_total=score.total_score,
                base_subscores=score.subscores or {},
                base_weights=base_weights,
                weight_adjustments=overlay.weight_adjustments or {},
                added_dimensions=overlay.added_dimensions or [],
            )
        elif score:
            overlay_score = score.total_score

        matched: List[int] = []
        for sig in company.signals:
            matched.extend(sig.matched_thesis_config_ids or [])
        matched = sorted(set(matched))

        items.append(
            QueueCompanyOut(
                company_id=company.id,
                name=company.name,
                domain=company.domain,
                description=company.description,
                base_score=base_total,
                overlay_score=overlay_score,
                rubric_base_version=score.rubric_base_version if score else base_version,
                why_note=score.why_note if score else None,
                matched_thesis_config_ids=matched,
                on_my_watchlist=company.id in watchlist_company_ids,
            )
        )

    items.sort(key=lambda x: (x.overlay_score is not None, x.overlay_score or 0), reverse=True)
    return items[:limit]


def team_queue(db: Session, partner: Partner, limit: int = 50) -> List[QueueCompanyOut]:
    """All scored companies ranked by shared base score."""
    base_version, _ = _active_base_weights(db)
    watchlist_company_ids = {
        r[0]
        for r in db.query(WatchlistEntry.company_id)
        .filter(WatchlistEntry.partner_id == partner.id)
        .all()
    }

    q = db.query(Score, Company).join(Company, Company.id == Score.company_id)
    if base_version:
        q = q.filter(Score.rubric_base_version == base_version)
    rows = q.order_by(Score.total_score.desc()).limit(limit).all()

    items: List[QueueCompanyOut] = []
    for score, company in rows:
        matched: List[int] = []
        for sig in company.signals:
            matched.extend(sig.matched_thesis_config_ids or [])
        items.append(
            QueueCompanyOut(
                company_id=company.id,
                name=company.name,
                domain=company.domain,
                description=company.description,
                base_score=score.total_score,
                overlay_score=None,
                rubric_base_version=score.rubric_base_version,
                why_note=score.why_note,
                matched_thesis_config_ids=sorted(set(matched)),
                on_my_watchlist=company.id in watchlist_company_ids,
            )
        )
    return items
