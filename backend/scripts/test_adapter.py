#!/usr/bin/env python3
"""Smoke-test one adapter: authenticate + fetch one test record.

Usage:
  python scripts/test_adapter.py github
  python scripts/test_adapter.py specter
  python scripts/test_adapter.py exa
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.exa_adapter import ExaAdapter  # noqa: E402
from app.adapters.github_adapter import GitHubAdapter  # noqa: E402
from app.adapters.specter_adapter import SpecterAdapter  # noqa: E402

ADAPTERS = {
    "github": GitHubAdapter,
    "specter": SpecterAdapter,
    "exa": ExaAdapter,
}


async def run(source: str) -> None:
    cls = ADAPTERS[source]
    adapter = cls()
    ok = await adapter.authenticate()
    print(f"authenticate({source}) -> {ok}")
    if not ok:
        sys.exit(1)
    record = await adapter.fetch_test_record()
    print(json.dumps(record.__dict__, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=sorted(ADAPTERS.keys()))
    args = parser.parse_args()
    asyncio.run(run(args.source))


if __name__ == "__main__":
    main()
