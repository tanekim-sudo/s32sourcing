#!/usr/bin/env python3
"""Background worker: refresh research for partners on their chosen schedule."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.services.pipeline import refresh_due_partners  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline-worker")


async def once() -> None:
    db = SessionLocal()
    try:
        report = await refresh_due_partners(db)
        log.info("due-partner refresh: %s", report)
    finally:
        db.close()


async def main() -> None:
    # Check often; each partner's refresh_interval_hours gates actual runs
    interval = int(os.getenv("PIPELINE_INTERVAL_SECONDS", "300"))
    log.info("starting partner refresh worker poll=%ss", interval)
    while True:
        try:
            await once()
        except Exception:
            log.exception("refresh loop failed")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
