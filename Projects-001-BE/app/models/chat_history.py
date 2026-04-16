"""
ORM model for persisted Chat AI history.

The table stores a snapshot of each successful exchange so the frontend can
rehydrate the latest Chat AI conversation without recomputing prior answers.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    project_name = Column(String, nullable=True)

    question = Column(Text, nullable=False)
    reply = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    intent = Column(String, nullable=True)

    sources = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    next_actions = Column(JSON, nullable=True)
    time_scope = Column(JSON, nullable=True)

    context_item_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
