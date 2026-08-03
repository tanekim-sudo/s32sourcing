from __future__ import annotations

from typing import List, Optional, Set

import yaml
from sqlalchemy.orm import Session

from app.api.schemas import QueueCompanyOut
from app.core.config import REPO_ROOT
from app.models.entities import (
    Company,
    CompanyFlag,
    Partner,
    RubricBase,
    RubricOverlay,
    Score,
    Signal,
    TeamShare,
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
        path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        weights = {k: float(v.get("weight", 0)) for k, v in (data.get("dimensions") or {}).items()}
        return data.get("version"), weights

    data = yaml.safe_load(active.yaml_content)
    weights = {k: float(v.get("weight", 0)) for k, v in (data.get("dimensions") or {}).items()}
    return active.version, weights


def partner_has_tracking(db: Session, partner: Partner) -> bool:
    has_area = (
        db.query(ThesisConfig.id)
        .filter(ThesisConfig.partner_id == partner.id, ThesisConfig.is_active.is_(True))
        .first()
        is not None
    )
    if has_area:
        return True
    return (
        db.query(WatchlistEntry.id)
        .filter(WatchlistEntry.partner_id == partner.id)
        .first()
        is not None
    )


def _own_thesis_ids(db: Session, partner: Partner) -> List[int]:
    rows = (
        db.query(ThesisConfig.id)
        .filter(ThesisConfig.partner_id == partner.id, ThesisConfig.is_active.is_(True))
        .all()
    )
    return [r[0] for r in rows]


def _build_item(
    db: Session,
    partner: Partner,
    company: Company,
    score: Optional[Score],
    base_version: Optional[str],
    base_weights: dict,
    overlay: Optional[RubricOverlay],
    watchlist_company_ids: Set[int],
    *,
    shared_by: Optional[str] = None,
) -> QueueCompanyOut:
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

    my_flag = (
        db.query(CompanyFlag)
        .filter(CompanyFlag.partner_id == partner.id, CompanyFlag.company_id == company.id)
        .one_or_none()
    )
    on_team = (
        db.query(TeamShare.id)
        .filter(TeamShare.partner_id == partner.id, TeamShare.company_id == company.id)
        .first()
        is not None
    )

    return QueueCompanyOut(
        company_id=company.id,
        name=company.name,
        domain=company.domain,
        description=company.description,
        base_score=score.total_score if score else None,
        overlay_score=overlay_score,
        rubric_base_version=score.rubric_base_version if score else base_version,
        why_note=score.why_note if score else None,
        matched_thesis_config_ids=sorted(set(matched)),
        on_my_watchlist=company.id in watchlist_company_ids,
        my_flag=my_flag.flag if my_flag else None,
        shared_to_team=on_team,
        shared_by=shared_by,
    )


def my_queue(db: Session, partner: Partner, limit: int = 50) -> List[QueueCompanyOut]:
    if not partner_has_tracking(db, partner):
        return []

    thesis_ids = _own_thesis_ids(db, partner)
    watchlist_company_ids: Set[int] = {
        r[0]
        for r in db.query(WatchlistEntry.company_id)
        .filter(WatchlistEntry.partner_id == partner.id)
        .all()
    }

    thesis_company_ids: Set[int] = set()
    if thesis_ids:
        for company_id, matched in db.query(Signal.company_id, Signal.matched_thesis_config_ids).filter(
            Signal.company_id.isnot(None)
        ):
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

    items = [
        _build_item(
            db,
            partner,
            c,
            scores.get(c.id),
            base_version,
            base_weights,
            overlay,
            watchlist_company_ids,
        )
        for c in companies
    ]
    # Rank by THIS partner's overlay weights (not base)
    items.sort(key=lambda x: (x.overlay_score is not None, x.overlay_score or 0), reverse=True)
    return items[:limit]


def team_queue(db: Session, partner: Partner, limit: int = 50) -> List[QueueCompanyOut]:
    """Only companies someone explicitly shared to the team."""
    if not partner_has_tracking(db, partner):
        return []

    shares = (
        db.query(TeamShare, Company, Partner)
        .join(Company, Company.id == TeamShare.company_id)
        .join(Partner, Partner.id == TeamShare.partner_id)
        .order_by(TeamShare.created_at.desc())
        .limit(limit * 3)
        .all()
    )
    if not shares:
        return []

    base_version, base_weights = _active_base_weights(db)
    overlay = (
        db.query(RubricOverlay)
        .filter(RubricOverlay.partner_id == partner.id, RubricOverlay.is_active.is_(True))
        .order_by(RubricOverlay.created_at.desc())
        .first()
    )
    watchlist_company_ids = {
        r[0]
        for r in db.query(WatchlistEntry.company_id)
        .filter(WatchlistEntry.partner_id == partner.id)
        .all()
    }

    company_ids = list({c.id for _, c, _ in shares})
    score_q = db.query(Score)
    if base_version:
        score_q = score_q.filter(Score.rubric_base_version == base_version)
    scores = {s.company_id: s for s in score_q.filter(Score.company_id.in_(company_ids)).all()}

    # Dedupe companies; keep first sharer name
    seen: Set[int] = set()
    items: List[QueueCompanyOut] = []
    for _share, company, sharer in shares:
        if company.id in seen:
            continue
        seen.add(company.id)
        items.append(
            _build_item(
                db,
                partner,
                company,
                scores.get(company.id),
                base_version,
                base_weights,
                overlay,
                watchlist_company_ids,
                shared_by=sharer.name,
            )
        )
        if len(items) >= limit:
            break

    items.sort(key=lambda x: (x.overlay_score is not None, x.overlay_score or 0), reverse=True)
    return items
