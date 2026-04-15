"""
Create any missing database tables without dropping existing data.

Usage:
  python scripts/create_missing_tables.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env")

from app.core.database import engine, Base
from app.models import BOQItem, InputRequest, Installment, Project, Transaction  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                ALTER TABLE IF EXISTS input_requests
                ADD COLUMN IF NOT EXISTS approved_amount NUMERIC(15, 2),
                ADD COLUMN IF NOT EXISTS review_note TEXT,
                ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS vendor_name VARCHAR,
                ADD COLUMN IF NOT EXISTS receipt_no VARCHAR,
                ADD COLUMN IF NOT EXISTS document_date DATE,
                ADD COLUMN IF NOT EXISTS is_duplicate_flag BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS duplicate_reason TEXT,
                ADD COLUMN IF NOT EXISTS duplicate_of_request_id UUID,
                ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS payment_reference VARCHAR
                """
            )
        )
    print("create_all completed. Missing tables have been created if needed.")


if __name__ == "__main__":
    asyncio.run(main())
