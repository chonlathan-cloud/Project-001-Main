"""Create the frozen pre-Alembic schema in an isolated PostgreSQL database."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _test_url() -> str:
    value = (
        os.environ.get("TEST_DATABASE_URL", "").strip()
        or os.environ.get("PHASE0_DATABASE_URL", "").strip()
    )
    if not value:
        raise SystemExit("TEST_DATABASE_URL is required; backend .env is not allowed")
    parsed = urlparse(value)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing non-loopback test database")
    database = parsed.path.lstrip("/")
    if not database.endswith("_test"):
        raise SystemExit("Refusing database whose name does not end with _test")
    return value


def _asyncpg_url(value: str) -> str:
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> None:
    database_url = _test_url()
    connection = await asyncpg.connect(_asyncpg_url(database_url))
    try:
        existing_tables = await connection.fetchval(
            """
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        if existing_tables:
            raise SystemExit(
                f"Refusing to bootstrap non-empty database ({existing_tables} public tables)"
            )
        await connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await connection.close()

    # app.core.database reads settings at import. Set the already-validated URL
    # before importing any application module so the backend .env cannot win.
    os.environ["DATABASE_URL"] = database_url
    from app.core.database import Base, engine
    import app.models  # noqa: F401

    legacy_tables = [
        table
        for table in Base.metadata.sorted_tables
        if not table.name.startswith("boq_v2_")
    ]

    def create_legacy_tables(sql_connection) -> None:
        for table in legacy_tables:
            table.create(sql_connection)

    async with engine.begin() as sql_connection:
        await sql_connection.run_sync(create_legacy_tables)
    await engine.dispose()
    print(f"Created {len(legacy_tables)} pre-Alembic tables in isolated test database")


if __name__ == "__main__":
    asyncio.run(main())
