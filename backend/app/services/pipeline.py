from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.adapters.base import ThesisQueryPlan, dedupe_thesis_queries
from app.adapters.clay_adapter import ClayAdapter
from app.adapters.exa_adapter import ExaAdapter
from app.adapters.github_adapter import GitHubAdapter
from app.adapters.specter_adapter import SpecterAdapter
from app.models.entities import Partner, Score, Signal, ThesisConfig, WatchlistEntry
from app.services import affinity as affinity_service
from app.services.normalize import ingest_candidates
from app.services.notes import generate_partner_line
from app.services.scoring import score_company


def _active_thesis_dicts(db: Session) -> List[dict]:
    rows = db.query(ThesisConfig).filter(ThesisConfig.is_active.is_(True)).all()
    return [
        {
            "id": t.id,
            "partner_id": t.partner_id,
            "name": t.name,
            "keywords": t.keywords or [],
            "exa_queries": t.exa_queries or [],
            "github_topics": t.github_topics or [],
            "is_shared": t.is_shared,
        }
        for t in rows
    ]


def _merge_candidates(groups: List[list]) -> list:
    by_key: Dict[str, Any] = {}
    for group in groups:
        for cand in group:
            key = f"{cand.source}:{cand.external_id or cand.url or cand.company_name}"
            if key not in by_key:
                by_key[key] = cand
            else:
                existing = by_key[key]
                merged = set(existing.matched_thesis_config_ids or [])
                merged.update(cand.matched_thesis_config_ids or [])
                existing.matched_thesis_config_ids = sorted(merged)
    return list(by_key.values())


async def run_sourcing_pipeline(db: Session, *, score: bool = True, push: bool = True) -> Dict[str, Any]:
    """
    Shared firm pipeline:
    union thesis configs → dedupe queries → pull adapters → normalize/dedupe
    → (optional) Clay enqueue → base score once → Affinity auto-push on base threshold.
    """
    thesis = _active_thesis_dicts(db)
    report: Dict[str, Any] = {
        "thesis_configs": len(thesis),
        "adapters": {},
        "ingest": {},
        "scored": [],
        "pushed": [],
        "skipped_no_keys": [],
    }

    # Deduped query plans per source field
    keyword_plans = dedupe_thesis_queries(thesis, field="keywords")
    exa_plans = dedupe_thesis_queries(thesis, field="exa_queries")
    github_plans = dedupe_thesis_queries(thesis, field="github_topics")
    # Specter uses keywords as search terms when present
    specter_plans = keyword_plans or [
        ThesisQueryPlan(
            query_key=str(t["name"]).lower(),
            query_payload={"query": t["name"]},
            thesis_config_ids=[t["id"]],
        )
        for t in thesis
    ]

    specter = SpecterAdapter()
    exa = ExaAdapter()
    github = GitHubAdapter()
    clay = ClayAdapter()

    candidates_groups = []
    for name, adapter, plans in (
        ("specter", specter, specter_plans),
        ("exa", exa, exa_plans),
        ("github", github, github_plans),
    ):
        if not plans:
            report["adapters"][name] = {"pulled": 0, "status": "no_queries"}
            continue
        if not await adapter.authenticate():
            report["adapters"][name] = {"pulled": 0, "status": "skipped_no_key"}
            report["skipped_no_keys"].append(name)
            continue
        pulled = await adapter.pull(plans)
        candidates_groups.append(pulled)
        report["adapters"][name] = {"pulled": len(pulled), "status": "ok", "plans": len(plans)}

    candidates = _merge_candidates(candidates_groups)
    report["ingest"] = ingest_candidates(db, candidates) if candidates else {
        "candidates": 0,
        "companies_created": 0,
        "signals_created": 0,
        "company_ids": [],
    }

    company_ids: List[int] = list(report["ingest"].get("company_ids") or [])

    # Enrichment enqueue (async; webhook returns later)
    for cid in company_ids:
        await clay.enqueue_enrichment(cid, {"company_id": cid})

    if score:
        for cid in company_ids:
            s = await score_company(db, cid)
            if s:
                report["scored"].append({"company_id": cid, "base_score": s.total_score})

                if push and affinity_service.should_auto_push(s.total_score):
                    from app.models.entities import Company

                    company = db.query(Company).filter(Company.id == cid).one()
                    partner_names = _relevant_partner_names(db, cid)
                    result = await affinity_service.push_company(
                        db,
                        company=company,
                        why_note=s.why_note or "",
                        relevant_partner_names=partner_names,
                    )
                    report["pushed"].append({"company_id": cid, **result})

    return report


def _relevant_partner_names(db: Session, company_id: int) -> List[str]:
    signals = db.query(Signal).filter(Signal.company_id == company_id).all()
    thesis_ids: Set[int] = set()
    for s in signals:
        thesis_ids.update(s.matched_thesis_config_ids or [])

    partner_ids: Set[int] = set()
    if thesis_ids:
        for t in db.query(ThesisConfig).filter(ThesisConfig.id.in_(thesis_ids)).all():
            if t.partner_id:
                partner_ids.add(t.partner_id)

    for wid in db.query(WatchlistEntry.partner_id).filter(WatchlistEntry.company_id == company_id):
        partner_ids.add(wid[0])

    if not partner_ids:
        return []
    partners = db.query(Partner).filter(Partner.id.in_(partner_ids)).all()
    return [p.name for p in partners]


async def score_all_unscored(db: Session) -> Dict[str, Any]:
    from app.models.entities import Company
    from app.services.scoring import load_active_rubric

    version, _, _ = load_active_rubric(db)
    scored_ids = {
        r[0]
        for r in db.query(Score.company_id).filter(Score.rubric_base_version == version).all()
    }
    companies = db.query(Company).all()
    results = []
    for c in companies:
        if c.id in scored_ids:
            continue
        s = await score_company(db, c.id)
        if s:
            results.append({"company_id": c.id, "base_score": s.total_score})
    return {"scored": results, "rubric_version": version}


def partner_lines_for_company(db: Session, company_id: int) -> List[str]:
    from app.models.entities import Company

    company = db.query(Company).filter(Company.id == company_id).one_or_none()
    if not company:
        return []
    signals = db.query(Signal).filter(Signal.company_id == company_id).all()
    thesis_ids = {tid for s in signals for tid in (s.matched_thesis_config_ids or [])}
    lines: List[str] = []
    if thesis_ids:
        theses = db.query(ThesisConfig).filter(ThesisConfig.id.in_(thesis_ids)).all()
        for t in theses:
            if not t.partner_id:
                continue
            partner = db.query(Partner).filter(Partner.id == t.partner_id).one_or_none()
            if not partner:
                continue
            line = generate_partner_line(
                partner=partner, thesis=t, company=company, signals=signals
            )
            if line:
                lines.append(line)
    return lines
