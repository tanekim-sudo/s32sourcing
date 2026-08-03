#!/usr/bin/env python3
"""Continuous shared sourcing loop for the firm pipeline.

Runs forever: pull → normalize → score → Affinity push (when configured).
Interval from PIPELINE_INTERVAL_SECONDS (default 3600).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.services.pipeline import run_sourcing_pipeline  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("pipeline-worker")


async def once() -> None:
    db = SessionLocal()
    try:
        report = await run_sourcing_pipeline(db, score=True, push=True)
        log.info(
            "pipeline done thesis=%s adapters=%s ingest=%s scored=%s pushed=%s skipped=%s",
            report.get("thesis_configs"),
            report.get("adapters"),
            report.get("ingest"),
            len(report.get("scored") or []),
            len(report.get("pushed") or []),
            report.get("skipped_no_keys"),
        )
    finally:
        db.close()


async def main() -> None:
    interval = int(os.getenv("PIPELINE_INTERVAL_SECONDS", "3600"))
    log.info("starting pipeline worker interval=%ss", interval)
    while True:
        try:
            await once()
        except Exception:
            log.exception("pipeline run failed")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
