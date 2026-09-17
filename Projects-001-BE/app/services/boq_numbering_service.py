"""Concurrency-safe BOQ V2 document and revision numbering."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.boq_v2 import BOQV2Document, BOQV2DocumentSequence
from app.services.boq_domain_service import BOQDomainError


async def next_document_number(
    db: AsyncSession,
    *,
    document_kind: str,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now(UTC)
    prefix = "CO" if document_kind == "CHANGE_ORDER" else "QT"
    sequence_key = f"{prefix}:{current.year}"
    statement = (
        insert(BOQV2DocumentSequence)
        .values(sequence_key=sequence_key, next_value=2)
        .on_conflict_do_update(
            index_elements=[BOQV2DocumentSequence.sequence_key],
            set_={
                "next_value": BOQV2DocumentSequence.next_value + 1,
                "updated_at": current,
            },
        )
        .returning(BOQV2DocumentSequence.next_value)
    )
    next_value = int((await db.execute(statement)).scalar_one())
    allocated = next_value - 1
    return f"{prefix}-{current.year}-{allocated:06d}"


async def next_revision_number(
    db: AsyncSession,
    *,
    document_id: UUID,
) -> int:
    statement = (
        update(BOQV2Document)
        .where(BOQV2Document.id == document_id)
        .values(revision_counter=BOQV2Document.revision_counter + 1)
        .returning(BOQV2Document.revision_counter)
    )
    next_value = (await db.execute(statement)).scalar_one_or_none()
    if next_value is None:
        raise BOQDomainError("BOQ_DOCUMENT_NOT_FOUND", "BOQ document does not exist")
    return int(next_value)
