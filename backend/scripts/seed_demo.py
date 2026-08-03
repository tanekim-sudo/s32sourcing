#!/usr/bin/env python3
"""Minimal seed: firm rubric + empty partner shell. No default tracking areas."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import REPO_ROOT  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.entities import Partner, PartnerRole, RubricBase  # noqa: E402


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

        # Shell partners only — no thesis, watchlist, or demo companies.
        for email, name, role in (
            ("admin@s32.com", "S32 Admin", PartnerRole.admin),
            ("dev@s32.com", "Dev Partner", PartnerRole.admin),
        ):
            row = db.query(Partner).filter(Partner.email == email).one_or_none()
            if not row:
                db.add(
                    Partner(
                        name=name,
                        email=email,
                        role=role,
                        clerk_user_id="dev_bypass" if email == "dev@s32.com" else None,
                    )
                )
        db.commit()
        print("Seeded rubric + empty partners (no default tracking).")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
