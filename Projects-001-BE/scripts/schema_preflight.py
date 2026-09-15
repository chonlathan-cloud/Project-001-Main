"""Read-only PostgreSQL schema inventory and deterministic fingerprint."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from urllib.parse import urlparse

import asyncpg


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-nonlocal-readonly",
        action="store_true",
        help=(
            "Permit a non-loopback target for an authorized read-only audit. "
            "This flag is not production-access authorization."
        ),
    )
    parser.add_argument(
        "--expected",
        help="Optional JSON result containing a fingerprint to compare",
    )
    return parser.parse_args()


def validate_target(value: str, *, allow_nonlocal_readonly: bool) -> tuple[str, str]:
    if not value:
        raise ValueError("PHASE0_DATABASE_URL is required; backend .env is not read")
    parsed = urlparse(value)
    if parsed.scheme not in {"postgresql", "postgresql+asyncpg"}:
        raise ValueError("PHASE0_DATABASE_URL must be a PostgreSQL URL")
    if not parsed.hostname or not parsed.path.lstrip("/"):
        raise ValueError("PHASE0_DATABASE_URL requires a host and database name")
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    database = parsed.path.lstrip("/")
    if not allow_nonlocal_readonly and not is_loopback:
        raise ValueError("Refusing non-loopback target without --allow-nonlocal-readonly")
    if not allow_nonlocal_readonly and not database.endswith("_test"):
        raise ValueError("Refusing local database whose name does not end with _test")
    port = parsed.port or 5432
    return value.replace("postgresql+asyncpg://", "postgresql://", 1), (
        f"{parsed.hostname}:{port}/{database}"
    )


async def inventory(database_url: str, masked_target: str) -> dict[str, object]:
    connection = await asyncpg.connect(database_url)
    try:
        async with connection.transaction(readonly=True):
            server_version = await connection.fetchval("SHOW server_version")
            extensions = [
                dict(row)
                for row in await connection.fetch(
                    "SELECT extname AS name, extversion AS version "
                    "FROM pg_extension ORDER BY extname"
                )
            ]
            tables = [
                dict(row)
                for row in await connection.fetch(
                    """
                    SELECT table_name AS name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
            ]
            columns = [
                dict(row)
                for row in await connection.fetch(
                    """
                    SELECT table_name, ordinal_position, column_name,
                           data_type, udt_name, is_nullable,
                           numeric_precision, numeric_scale, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                    """
                )
            ]
            constraints = [
                dict(row)
                for row in await connection.fetch(
                    """
                    SELECT rel.relname AS table_name,
                           con.conname AS constraint_name,
                           con.contype AS constraint_type,
                           pg_get_constraintdef(con.oid, true) AS definition
                    FROM pg_constraint con
                    JOIN pg_class rel ON rel.oid = con.conrelid
                    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                    WHERE nsp.nspname = 'public'
                    ORDER BY rel.relname, con.conname
                    """
                )
            ]
            indexes = [
                dict(row)
                for row in await connection.fetch(
                    """
                    SELECT tablename AS table_name, indexname AS index_name,
                           indexdef AS definition
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                    """
                )
            ]
    finally:
        await connection.close()

    schema = {
        "extensions": extensions,
        "tables": tables,
        "columns": columns,
        "constraints": constraints,
        "indexes": indexes,
    }
    canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"), default=str)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "target": masked_target,
        "server_version": server_version,
        "fingerprint_sha256": fingerprint,
        "table_count": len(tables),
        "boq_v2_table_count": sum(
            1 for table in tables if str(table["name"]).startswith("boq_v2_")
        ),
        "schema": schema,
    }


async def main() -> int:
    args = _arguments()
    raw_url = os.environ.get("PHASE0_DATABASE_URL", "").strip()
    try:
        database_url, masked_target = validate_target(
            raw_url,
            allow_nonlocal_readonly=args.allow_nonlocal_readonly,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    result = await inventory(database_url, masked_target)
    if args.expected:
        with open(args.expected, encoding="utf-8") as handle:
            expected = json.load(handle)
        expected_fingerprint = expected.get("fingerprint_sha256")
        result["expected_fingerprint_sha256"] = expected_fingerprint
        result["fingerprint_matches"] = (
            result["fingerprint_sha256"] == expected_fingerprint
        )
        if not result["fingerprint_matches"]:
            print(json.dumps(result, indent=2, sort_keys=True, default=str))
            return 1
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
