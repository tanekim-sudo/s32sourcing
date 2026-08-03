#!/usr/bin/env python3
"""Seed demo partners, thesis, companies, signals, scores for local UI development."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import REPO_ROOT  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.entities import (  # noqa: E402
    Company,
    Partner,
    PartnerRole,
    RubricBase,
    RubricOverlay,
    Signal,
    ThesisConfig,
    WatchlistEntry,
)
from app.services.entity_resolution import upsert_company  # noqa: E402
from app.services.scoring import score_company  # noqa: E402


DEMO_COMPANIES = [
    {
        "name": "LatticeForge",
        "domain": "latticeforge.ai",
        "description": "AI infrastructure for real-time feature stores. Founded by ex-Databricks engineers.",
        "signals": [
            {
                "source": "exa",
                "title": "LatticeForge launches feature store for LLM apps",
                "summary": "Early revenue, hiring ML infra engineers, low VC attention so far.",
                "url": "https://example.com/latticeforge",
            },
            {
                "source": "github",
                "title": "latticeforge/feature-runtime",
                "summary": "2.1k stars, strong commit velocity, Apache-2.0.",
                "url": "https://github.com/example/latticeforge",
            },
        ],
    },
    {
        "name": "Harborline Health",
        "domain": "harborline.health",
        "description": "Workflow automation for specialty clinics. Repeat founder, warm Affinity path.",
        "signals": [
            {
                "source": "specter",
                "title": "Harborline Health — Series seed rumors",
                "summary": "Growing clinic customers, alumni network intro available via Affinity.",
                "url": "https://example.com/harborline",
            }
        ],
    },
    {
        "name": "CrowdedRound",
        "domain": "crowdedround.io",
        "description": "Devtools with heavy recent VC attention from top-tier funds.",
        "signals": [
            {
                "source": "exa",
                "title": "CrowdedRound raises from Sequoia and a16z",
                "summary": "Series A crowded round, lots of press velocity.",
                "url": "https://example.com/crowdedround",
            }
        ],
    },
]


def seed_rubric(db) -> None:
    path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
    yaml_content = path.read_text(encoding="utf-8")
    existing = db.query(RubricBase).filter(RubricBase.version == "1.0.0").one_or_none()
    if existing:
        return
    db.query(RubricBase).update({RubricBase.is_active: False})
    db.add(
        RubricBase(
            version="1.0.0",
            yaml_content=yaml_content,
            is_active=True,
            changelog="Initial firm base rubric scaffold.",
        )
    )
    db.commit()


async def main() -> None:
    db = SessionLocal()
    try:
        seed_rubric(db)

        admin = db.query(Partner).filter(Partner.email == "admin@s32.com").one_or_none()
        if not admin:
            admin = Partner(name="S32 Admin", email="admin@s32.com", role=PartnerRole.admin)
            db.add(admin)
            db.flush()

        you = db.query(Partner).filter(Partner.email == "dev@s32.com").one_or_none()
        if not you:
            you = Partner(
                name="Dev Partner",
                email="dev@s32.com",
                # Admin in demo so Firm Rubric page is writable without Clerk
                role=PartnerRole.admin,
                clerk_user_id="dev_bypass",
            )
            db.add(you)
            db.flush()
        elif you.role != PartnerRole.admin:
            you.role = PartnerRole.admin
            db.add(you)
            db.flush()

        shared = (
            db.query(ThesisConfig)
            .filter(ThesisConfig.name == "Firm: AI Infra", ThesisConfig.partner_id.is_(None))
            .one_or_none()
        )
        if not shared:
            shared = ThesisConfig(
                partner_id=None,
                name="Firm: AI Infra",
                keywords=["ai infrastructure", "feature store", "llm infra"],
                exa_queries=["AI infrastructure startups feature store"],
                github_topics=["machine-learning", "mlops"],
                is_shared=True,
                is_active=True,
            )
            db.add(shared)
            db.flush()

        personal = (
            db.query(ThesisConfig)
            .filter(ThesisConfig.partner_id == you.id, ThesisConfig.name == "Healthcare workflows")
            .one_or_none()
        )
        if not personal:
            personal = ThesisConfig(
                partner_id=you.id,
                name="Healthcare workflows",
                keywords=["healthcare", "clinic", "workflow"],
                exa_queries=["healthcare workflow automation startups"],
                github_topics=["healthcare"],
                is_shared=False,
                is_active=True,
            )
            db.add(personal)
            db.flush()

        db.commit()

        company_ids = []
        for spec in DEMO_COMPANIES:
            company, _ = upsert_company(
                db,
                name=spec["name"],
                domain=spec["domain"],
                description=spec["description"],
            )
            db.commit()
            company_ids.append(company.id)

            thesis_ids = [shared.id]
            if "Health" in spec["name"] or "health" in (spec["description"] or "").lower():
                thesis_ids.append(personal.id)

            for sig in spec["signals"]:
                exists = (
                    db.query(Signal)
                    .filter(Signal.source == sig["source"], Signal.url == sig["url"])
                    .one_or_none()
                )
                if exists:
                    continue
                db.add(
                    Signal(
                        company_id=company.id,
                        source=sig["source"],
                        external_id=sig["url"],
                        title=sig["title"],
                        summary=sig["summary"],
                        url=sig["url"],
                        payload=sig,
                        matched_thesis_config_ids=thesis_ids,
                    )
                )
            db.commit()
            await score_company(db, company.id, force=True)

        harbor_co = db.query(Company).filter(Company.domain == "harborline.health").one()
        wl = (
            db.query(WatchlistEntry)
            .filter(
                WatchlistEntry.partner_id == you.id,
                WatchlistEntry.company_id == harbor_co.id,
            )
            .one_or_none()
        )
        if not wl:
            db.add(
                WatchlistEntry(
                    partner_id=you.id,
                    company_id=harbor_co.id,
                    note="Warm intro available",
                )
            )
            db.commit()

        overlay = (
            db.query(RubricOverlay)
            .filter(RubricOverlay.partner_id == you.id, RubricOverlay.is_active.is_(True))
            .first()
        )
        if not overlay:
            db.add(
                RubricOverlay(
                    partner_id=you.id,
                    version="1",
                    base_rubric_version="1.0.0",
                    weight_adjustments={"founder_quality": 0.1, "traction_signal": -0.05},
                    added_dimensions=[],
                    is_active=True,
                )
            )
            db.commit()

        print(f"Seeded demo data. Partner={you.email} companies={company_ids}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
