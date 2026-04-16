"""
Persistence helpers for Chat AI history.

The system keeps only the most recent exchanges to avoid unbounded storage
growth while still restoring useful conversational context on page load.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_history import ChatHistory

CHAT_HISTORY_RETENTION_LIMIT = 20


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_dict(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _clean_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value

    cleaned = _clean_text(value)
    if not cleaned:
        return None

    try:
        return UUID(cleaned)
    except (TypeError, ValueError):
        return None


def serialize_chat_history(item: ChatHistory) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "question": _clean_text(item.question),
        "reply": _clean_text(item.reply),
        "summary": _clean_text(item.summary),
        "intent": _clean_text(item.intent),
        "sources": _clean_list(item.sources),
        "metrics": _clean_list(item.metrics),
        "next_actions": _clean_list(item.next_actions),
        "time_scope": _clean_dict(item.time_scope),
        "project_id": str(item.project_id) if item.project_id else "",
        "project_name": _clean_text(item.project_name),
        "context_item_count": _to_int(item.context_item_count),
        "created_at": item.created_at.isoformat() if item.created_at else "",
    }


async def list_recent_chat_history(
    db: AsyncSession,
    *,
    limit: int = CHAT_HISTORY_RETENTION_LIMIT,
) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), CHAT_HISTORY_RETENTION_LIMIT))
    result = await db.execute(
        select(ChatHistory)
        .order_by(ChatHistory.created_at.desc(), ChatHistory.id.desc())
        .limit(safe_limit)
    )
    rows = list(reversed(result.scalars().all()))
    return [serialize_chat_history(row) for row in rows]


async def save_chat_history_exchange(
    db: AsyncSession,
    *,
    question: str,
    analysis: dict[str, Any],
) -> None:
    row = ChatHistory(
        question=_clean_text(question),
        reply=_clean_text(analysis.get("reply")),
        summary=_clean_text(analysis.get("summary")),
        intent=_clean_text(analysis.get("intent")),
        sources=_clean_list(analysis.get("sources")),
        metrics=_clean_list(analysis.get("metrics")),
        next_actions=_clean_list(analysis.get("next_actions")),
        time_scope=_clean_dict(analysis.get("time_scope")),
        project_id=_clean_uuid(analysis.get("project_id")),
        project_name=_clean_text(analysis.get("project_name")),
        context_item_count=_to_int(analysis.get("context_item_count")),
    )
    db.add(row)
    await db.flush()

    stale_id_result = await db.execute(
        select(ChatHistory.id)
        .order_by(ChatHistory.created_at.desc(), ChatHistory.id.desc())
        .offset(CHAT_HISTORY_RETENTION_LIMIT)
    )
    stale_ids = list(stale_id_result.scalars().all())
    if stale_ids:
        await db.execute(delete(ChatHistory).where(ChatHistory.id.in_(stale_ids)))

    await db.commit()


async def clear_chat_history(db: AsyncSession) -> int:
    result = await db.execute(delete(ChatHistory))
    await db.commit()
    return int(result.rowcount or 0)
