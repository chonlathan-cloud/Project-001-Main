"""Alembic environment with an explicit, safety-checked database target."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _migration_url() -> str:
    value = os.environ.get("ALEMBIC_DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "ALEMBIC_DATABASE_URL is required; migrations never load the backend .env"
        )
    parsed = urlparse(value.replace("postgresql+asyncpg://", "postgresql://", 1))
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    database = parsed.path.lstrip("/")
    if is_loopback and not database.endswith("_test"):
        raise RuntimeError("Local migration database name must end with _test")
    if not is_loopback and os.environ.get("ALEMBIC_ALLOW_NONLOCAL") != "1":
        raise RuntimeError(
            "Non-local migration target requires ALEMBIC_ALLOW_NONLOCAL=1 after preflight"
        )
    return value


database_url = _migration_url()
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# app.core.database reads DATABASE_URL during import. Use only the explicitly
# supplied migration URL, never an ambient backend .env target.
os.environ["DATABASE_URL"] = database_url
from app.core.database import Base  # noqa: E402
import app.models  # noqa: E402,F401

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Allow generating the immutable legacy baseline without V2 tables."""

    if os.environ.get("ALEMBIC_MODEL_SCOPE") != "legacy":
        return True
    table_name = name if type_ == "table" else getattr(object_, "table", None)
    if not isinstance(table_name, str):
        table_name = getattr(table_name, "name", "")
    return not table_name.startswith("boq_v2_")


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
