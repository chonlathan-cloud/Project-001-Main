"""
Delete abandoned temp receipt uploads from GCS that are not referenced in input_requests.

Usage:
  ./venv/bin/python scripts/cleanup_temp_receipts.py
  ./venv/bin/python scripts/cleanup_temp_receipts.py 48
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.database import AsyncSessionLocal
from app.services.input_receipt_cleanup_service import cleanup_orphan_temp_receipts


async def main() -> None:
    older_than_hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    async with AsyncSessionLocal() as session:
        result = await cleanup_orphan_temp_receipts(
            db=session,
            older_than_hours=older_than_hours,
        )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
