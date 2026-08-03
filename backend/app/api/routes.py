from __future__ import annotations

from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.schemas import (
    CompanyCreate,
    CompanyDetailOut,
    FeedbackCreate,
    FeedbackOut,
    HealthOut,
    PartnerOut,
    PipelineRunOut,
    QueueResponse,
    RubricBaseCreate,
    RubricBaseOut,
    RubricOverlayOut,
    RubricOverlayUpsert,
    ThesisConfigCreate,
    ThesisConfigOut,
    ThesisConfigUpdate,
    WatchlistCreate,
    WatchlistEntryOut,
)
from app.core.auth import get_current_partner, require_admin
from app.core.config import REPO_ROOT, get_settings
from app.core.database import get_db
from app.models.entities import (
    Company,
    Feedback,
    Partner,
    PartnerRole,
    RubricBase,
    RubricOverlay,
    Score,
    ThesisConfig,
    WatchlistEntry,
)
from app.services import pipeline as pipeline_service
from app.services import queue as queue_service
from app.services.entity_resolution import upsert_company
from app.services.overlay_scoring import apply_overlay
from app.services.scoring import load_active_rubric, score_company

router = APIRouter()


def _partner_out(partner: Partner) -> PartnerOut:
    return PartnerOut(
        id=partner.id,
        name=partner.name,
        email=partner.email,
        role=partner.role.value if hasattr(partner.role, "value") else str(partner.role),
    )


@router.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    settings = get_settings()
    return HealthOut(
        status="ok",
        auth_mode="dev_bypass" if settings.auth_dev_bypass else "clerk",
    )


@router.get("/me", response_model=PartnerOut)
def me(partner: Partner = Depends(get_current_partner)) -> PartnerOut:
    return _partner_out(partner)


# ── Queues ──────────────────────────────────────────────────────────────────


@router.get("/queue/mine", response_model=QueueResponse)
def my_queue(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> QueueResponse:
    setup_required = not queue_service.partner_has_tracking(db, partner)
    items = [] if setup_required else queue_service.my_queue(db, partner)
    return QueueResponse(
        partner=_partner_out(partner),
        items=items,
        total=len(items),
        setup_required=setup_required,
    )


@router.get("/queue/team", response_model=QueueResponse)
def team_queue(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> QueueResponse:
    setup_required = not queue_service.partner_has_tracking(db, partner)
    items = [] if setup_required else queue_service.team_queue(db, partner)
    return QueueResponse(
        partner=_partner_out(partner),
        items=items,
        total=len(items),
        setup_required=setup_required,
    )


# ── Thesis ──────────────────────────────────────────────────────────────────


@router.get("/me/thesis", response_model=List[ThesisConfigOut])
def list_my_thesis(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> List[ThesisConfig]:
    return (
        db.query(ThesisConfig)
        .filter(ThesisConfig.partner_id == partner.id)
        .order_by(ThesisConfig.created_at.desc())
        .all()
    )


@router.get("/thesis/shared", response_model=List[ThesisConfigOut])
def list_shared_thesis(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> List[ThesisConfig]:
    return (
        db.query(ThesisConfig)
        .filter(
            ThesisConfig.is_active.is_(True),
            (ThesisConfig.is_shared.is_(True)) | (ThesisConfig.partner_id.is_(None)),
        )
        .order_by(ThesisConfig.created_at.desc())
        .all()
    )


@router.post("/me/thesis", response_model=ThesisConfigOut, status_code=201)
def create_thesis(
    body: ThesisConfigCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> ThesisConfig:
    from app.services.thesis_expand import expand_tracking_topics

    is_admin = partner.role == PartnerRole.admin
    # Shared/firm-wide configs: partner_id null — admin only
    if body.is_shared:
        if not is_admin:
            raise HTTPException(status_code=403, detail="Only admins create shared thesis configs")
        partner_id = None
        is_shared = True
    else:
        partner_id = partner.id
        is_shared = False

    # Prefer partner-facing topics; fall back to explicit advanced fields.
    topics = body.topics or [str(k) for k in (body.keywords or [])]
    expanded = expand_tracking_topics(topics)
    keywords = body.keywords or expanded["keywords"]
    exa_queries = body.exa_queries or expanded["exa_queries"]
    github_topics = body.github_topics or expanded["github_topics"]

    row = ThesisConfig(
        partner_id=partner_id,
        name=body.name,
        keywords=keywords,
        exa_queries=exa_queries,
        github_topics=github_topics,
        is_shared=is_shared,
        is_active=body.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/me/thesis/{thesis_id}", response_model=ThesisConfigOut)
def update_thesis(
    thesis_id: int,
    body: ThesisConfigUpdate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> ThesisConfig:
    row = db.query(ThesisConfig).filter(ThesisConfig.id == thesis_id).one_or_none()
    if not row:
        raise HTTPException(404, "Thesis not found")
    is_admin = partner.role == PartnerRole.admin
    if row.partner_id != partner.id and not (is_admin and (row.is_shared or row.partner_id is None)):
        raise HTTPException(403, "Not your thesis config")

    from app.services.thesis_expand import expand_tracking_topics

    if body.name is not None:
        row.name = body.name
    if body.topics is not None:
        expanded = expand_tracking_topics(body.topics)
        row.keywords = expanded["keywords"]
        row.exa_queries = expanded["exa_queries"]
        row.github_topics = expanded["github_topics"]
    else:
        if body.keywords is not None:
            row.keywords = body.keywords
        if body.exa_queries is not None:
            row.exa_queries = body.exa_queries
        if body.github_topics is not None:
            row.github_topics = body.github_topics
    if body.is_active is not None:
        row.is_active = body.is_active
    if body.is_shared is not None:
        if body.is_shared and not is_admin:
            raise HTTPException(403, "Only admins can mark thesis as shared")
        row.is_shared = body.is_shared

    db.commit()
    db.refresh(row)
    return row


@router.delete("/me/thesis/{thesis_id}", status_code=204)
def delete_thesis(
    thesis_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> None:
    row = db.query(ThesisConfig).filter(ThesisConfig.id == thesis_id).one_or_none()
    if not row:
        raise HTTPException(404, "Thesis not found")
    if row.partner_id != partner.id and partner.role != PartnerRole.admin:
        raise HTTPException(403, "Not your thesis config")
    db.delete(row)
    db.commit()


# ── Watchlist ───────────────────────────────────────────────────────────────


@router.get("/me/watchlist", response_model=List[WatchlistEntryOut])
def list_watchlist(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> List[WatchlistEntryOut]:
    rows = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.partner_id == partner.id)
        .order_by(WatchlistEntry.created_at.desc())
        .all()
    )
    out = []
    for r in rows:
        item = WatchlistEntryOut.model_validate(r)
        item.company_name = r.company.name if r.company else None
        out.append(item)
    return out


@router.post("/me/watchlist", response_model=WatchlistEntryOut, status_code=201)
def add_watchlist(
    body: WatchlistCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> WatchlistEntryOut:
    company = db.query(Company).filter(Company.id == body.company_id).one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")
    existing = (
        db.query(WatchlistEntry)
        .filter(
            WatchlistEntry.partner_id == partner.id,
            WatchlistEntry.company_id == body.company_id,
        )
        .one_or_none()
    )
    if existing:
        existing.note = body.note
        db.commit()
        db.refresh(existing)
        out = WatchlistEntryOut.model_validate(existing)
        out.company_name = company.name
        return out

    row = WatchlistEntry(partner_id=partner.id, company_id=body.company_id, note=body.note)
    db.add(row)
    db.commit()
    db.refresh(row)
    out = WatchlistEntryOut.model_validate(row)
    out.company_name = company.name
    return out


@router.delete("/me/watchlist/{entry_id}", status_code=204)
def remove_watchlist(
    entry_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> None:
    row = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.id == entry_id, WatchlistEntry.partner_id == partner.id)
        .one_or_none()
    )
    if not row:
        raise HTTPException(404, "Watchlist entry not found")
    db.delete(row)
    db.commit()


# ── Rubric overlay ──────────────────────────────────────────────────────────


@router.get("/me/rubric-overlay", response_model=Optional[RubricOverlayOut])
def get_overlay(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> Optional[RubricOverlay]:
    return (
        db.query(RubricOverlay)
        .filter(RubricOverlay.partner_id == partner.id, RubricOverlay.is_active.is_(True))
        .order_by(RubricOverlay.created_at.desc())
        .first()
    )


@router.put("/me/rubric-overlay", response_model=RubricOverlayOut)
def upsert_overlay(
    body: RubricOverlayUpsert,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> RubricOverlay:
    db.query(RubricOverlay).filter(RubricOverlay.partner_id == partner.id).update(
        {RubricOverlay.is_active: False}
    )
    row = RubricOverlay(
        partner_id=partner.id,
        version=body.version,
        base_rubric_version=body.base_rubric_version,
        weight_adjustments=body.weight_adjustments,
        added_dimensions=body.added_dimensions,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Firm rubric (admin write) ───────────────────────────────────────────────


@router.get("/rubric/base", response_model=List[RubricBaseOut])
def list_base_rubrics(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> List[RubricBase]:
    rows = db.query(RubricBase).order_by(RubricBase.created_at.desc()).all()
    if rows:
        return rows
    # Fallback: expose file-backed rubric as virtual row
    path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
    content = path.read_text(encoding="utf-8")
    return [
        RubricBase(
            id=0,
            version="1.0.0",
            yaml_content=content,
            is_active=True,
            changelog="File-backed scaffold (not yet in DB)",
        )
    ]


@router.post("/rubric/base", response_model=RubricBaseOut, status_code=201)
def create_base_rubric(
    body: RubricBaseCreate,
    admin: Partner = Depends(require_admin),
    db: Session = Depends(get_db),
) -> RubricBase:
    try:
        yaml.safe_load(body.yaml_content)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"Invalid YAML: {e}") from e

    if body.activate:
        db.query(RubricBase).update({RubricBase.is_active: False})
    row = RubricBase(
        version=body.version,
        yaml_content=body.yaml_content,
        is_active=body.activate,
        created_by=admin.id,
        changelog=body.changelog,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Companies ───────────────────────────────────────────────────────────────


@router.get("/companies/{company_id}", response_model=CompanyDetailOut)
def company_detail(
    company_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> CompanyDetailOut:
    company = db.query(Company).filter(Company.id == company_id).one_or_none()
    if not company:
        raise HTTPException(404, "Company not found")

    version, rubric, _ = load_active_rubric(db)
    base_weights = {k: float(v.get("weight", 0)) for k, v in (rubric.get("dimensions") or {}).items()}
    score = (
        db.query(Score)
        .filter(Score.company_id == company_id, Score.rubric_base_version == version)
        .one_or_none()
    )
    overlay = (
        db.query(RubricOverlay)
        .filter(RubricOverlay.partner_id == partner.id, RubricOverlay.is_active.is_(True))
        .order_by(RubricOverlay.created_at.desc())
        .first()
    )

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

    watchers = (
        db.query(Partner.name)
        .join(WatchlistEntry, WatchlistEntry.partner_id == Partner.id)
        .filter(WatchlistEntry.company_id == company_id)
        .all()
    )
    on_mine = (
        db.query(WatchlistEntry)
        .filter(WatchlistEntry.partner_id == partner.id, WatchlistEntry.company_id == company_id)
        .first()
        is not None
    )

    feedback_rows = (
        db.query(Feedback, Partner)
        .join(Partner, Partner.id == Feedback.partner_id)
        .filter(Feedback.company_id == company_id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    feedback_out = [
        FeedbackOut(
            id=f.id,
            partner_id=f.partner_id,
            partner_name=p.name,
            company_id=f.company_id,
            thumbs=f.thumbs,
            comment=f.comment,
            created_at=f.created_at,
        )
        for f, p in feedback_rows
    ]

    signals = [
        {
            "id": s.id,
            "source": s.source,
            "title": s.title,
            "summary": s.summary,
            "url": s.url,
            "matched_thesis_config_ids": s.matched_thesis_config_ids or [],
            "observed_at": s.observed_at.isoformat() if s.observed_at else None,
        }
        for s in company.signals
    ]

    return CompanyDetailOut(
        id=company.id,
        name=company.name,
        domain=company.domain,
        description=company.description,
        affinity_org_id=company.affinity_org_id,
        base_score=score.total_score if score else None,
        overlay_score=overlay_score,
        rubric_base_version=score.rubric_base_version if score else version,
        subscores=score.subscores if score else {},
        evidence=score.evidence if score else {},
        why_note=score.why_note if score else None,
        partner_lines=pipeline_service.partner_lines_for_company(db, company_id),
        watchlisted_by=[w[0] for w in watchers],
        signals=signals,
        feedback=feedback_out,
        on_my_watchlist=on_mine,
    )


@router.post("/companies", response_model=CompanyDetailOut, status_code=201)
async def create_company(
    body: CompanyCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> CompanyDetailOut:
    company, _ = upsert_company(
        db, name=body.name, domain=body.domain, description=body.description
    )
    db.commit()
    await score_company(db, company.id)
    return company_detail(company.id, partner, db)


@router.post("/companies/{company_id}/feedback", response_model=FeedbackOut)
def upsert_feedback(
    company_id: int,
    body: FeedbackCreate,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> FeedbackOut:
    if body.thumbs not in (-1, 1):
        raise HTTPException(400, "thumbs must be 1 or -1")
    if not db.query(Company).filter(Company.id == company_id).first():
        raise HTTPException(404, "Company not found")

    row = (
        db.query(Feedback)
        .filter(Feedback.partner_id == partner.id, Feedback.company_id == company_id)
        .one_or_none()
    )
    if row:
        row.thumbs = body.thumbs
        row.comment = body.comment
    else:
        row = Feedback(
            partner_id=partner.id,
            company_id=company_id,
            thumbs=body.thumbs,
            comment=body.comment,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackOut(
        id=row.id,
        partner_id=row.partner_id,
        partner_name=partner.name,
        company_id=row.company_id,
        thumbs=row.thumbs,
        comment=row.comment,
        created_at=row.created_at,
    )


# ── Pipeline / scoring ──────────────────────────────────────────────────────


@router.post("/pipeline/run", response_model=PipelineRunOut)
async def run_pipeline(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> PipelineRunOut:
    report = await pipeline_service.run_sourcing_pipeline(db)
    return PipelineRunOut(report=report)


@router.post("/pipeline/score-unscored", response_model=PipelineRunOut)
async def score_unscored(
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> PipelineRunOut:
    report = await pipeline_service.score_all_unscored(db)
    return PipelineRunOut(report=report)


@router.post("/companies/{company_id}/score", response_model=Dict[str, Any])
async def rescore_company(
    company_id: int,
    partner: Partner = Depends(get_current_partner),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    score = await score_company(db, company_id, force=True)
    if not score:
        raise HTTPException(404, "Company not found")
    return {
        "company_id": company_id,
        "total_score": score.total_score,
        "rubric_base_version": score.rubric_base_version,
        "why_note": score.why_note,
    }


# ── Clay webhook ────────────────────────────────────────────────────────────


@router.post("/webhooks/clay")
async def clay_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    from app.adapters.clay_adapter import ClayAdapter
    from app.services.entity_resolution import upsert_company
    from app.services.scoring import score_company as score_fn

    raw = await request.body()
    adapter = ClayAdapter()
    sig = request.headers.get("x-clay-signature") or request.headers.get("x-signature")
    if not adapter.verify_signature(raw, sig):
        raise HTTPException(401, "Invalid Clay signature")

    body = await request.json()
    result = await adapter.handle_webhook(body, sig)
    domain = result.get("company_domain")
    name = body.get("name") or body.get("company_name") or domain or "Unknown"
    company, _ = upsert_company(
        db,
        name=name,
        domain=domain,
        description=body.get("description"),
        raw_payload={"clay": body},
    )
    db.commit()
    await score_fn(db, company.id, force=True)
    return {"ok": True, "company_id": company.id}
