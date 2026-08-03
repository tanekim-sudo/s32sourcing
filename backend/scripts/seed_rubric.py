#!/usr/bin/env python3
"""Seed active rubric_base from /rubric/rubric_base.v1.yaml if none exists."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import REPO_ROOT  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.entities import RubricBase  # noqa: E402


def main() -> None:
    path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
    yaml_content = path.read_text(encoding="utf-8")
    db = SessionLocal()
    try:
        existing = db.query(RubricBase).filter(RubricBase.version == "1.0.0").one_or_none()
        if existing:
            print(f"rubric_base v{existing.version} already present (active={existing.is_active})")
            return
        db.query(RubricBase).update({RubricBase.is_active: False})
        row = RubricBase(
            version="1.0.0",
            yaml_content=yaml_content,
            is_active=True,
            changelog="Initial firm base rubric scaffold.",
        )
        db.add(row)
        db.commit()
        print("Seeded rubric_base v1.0.0 as active.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
