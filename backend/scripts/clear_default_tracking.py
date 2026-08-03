#!/usr/bin/env python3
"""Remove scaffold demo tracking areas only (not partner-saved settings)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.entities import ThesisConfig  # noqa: E402

DEMO_THESIS_NAMES = {
    "Firm: AI Infra",
    "Healthcare workflows",
}


def main() -> None:
    db = SessionLocal()
    try:
        removed = (
            db.query(ThesisConfig)
            .filter(ThesisConfig.name.in_(DEMO_THESIS_NAMES))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Cleared scaffold demo thesis rows: {removed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
