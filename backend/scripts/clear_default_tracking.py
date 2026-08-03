#!/usr/bin/env python3
"""Remove scaffold demo tracking so partners start blank."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.entities import Company, ThesisConfig, WatchlistEntry  # noqa: E402

DEMO_THESIS_NAMES = {
    "Firm: AI Infra",
    "Healthcare workflows",
}
DEMO_DOMAINS = {
    "latticeforge.ai",
    "harborline.health",
    "crowdedround.io",
}


def main() -> None:
    db = SessionLocal()
    try:
        removed_thesis = (
            db.query(ThesisConfig)
            .filter(ThesisConfig.name.in_(DEMO_THESIS_NAMES))
            .delete(synchronize_session=False)
        )
        demo_company_ids = [
            c.id
            for c in db.query(Company.id).filter(Company.domain.in_(DEMO_DOMAINS)).all()
        ]
        removed_wl = 0
        if demo_company_ids:
            removed_wl = (
                db.query(WatchlistEntry)
                .filter(WatchlistEntry.company_id.in_(demo_company_ids))
                .delete(synchronize_session=False)
            )
        db.commit()
        print(
            f"Cleared scaffold tracking thesis={removed_thesis} "
            f"demo_watchlist={removed_wl}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
