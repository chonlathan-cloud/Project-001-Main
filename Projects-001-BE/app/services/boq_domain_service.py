"""BOQ V2 identity, hierarchy, version, locking, and request-hash primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BOQDomainError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ScopeIdentity:
    row_id: UUID
    logical_id: UUID
    project_id: UUID
    revision_id: UUID
    parent_row_id: UUID | None
    node_kind: Literal["SECTION", "CATEGORY", "SUBCATEGORY", "ITEM"]
    position: int


def assert_expected_version(*, current: int, expected: int) -> None:
    if expected != current:
        raise BOQDomainError(
            "STALE_BOQ_VERSION",
            f"BOQ version changed; expected {expected}, current {current}",
        )


def assert_mutable_draft(status: str) -> None:
    if str(status).upper() != "DRAFT":
        raise BOQDomainError(
            "IMMUTABLE_BOQ_REVISION",
            "Only a DRAFT revision can be edited",
        )


def validate_scope_hierarchy(nodes: Iterable[ScopeIdentity]) -> None:
    node_list = list(nodes)
    by_row_id = {node.row_id: node for node in node_list}
    if len(by_row_id) != len(node_list):
        raise BOQDomainError("DUPLICATE_SCOPE_ROW", "Scope row IDs must be unique")
    identities = {(node.revision_id, node.logical_id) for node in node_list}
    if len(identities) != len(node_list):
        raise BOQDomainError(
            "DUPLICATE_LOGICAL_ID", "Logical IDs must be unique within a revision"
        )
    sibling_positions: set[tuple[UUID, UUID | None, int]] = set()
    for node in node_list:
        if node.position < 0:
            raise BOQDomainError(
                "INVALID_SCOPE_POSITION", "Position cannot be negative"
            )
        position_key = (node.revision_id, node.parent_row_id, node.position)
        if position_key in sibling_positions:
            raise BOQDomainError(
                "DUPLICATE_SCOPE_POSITION", "Sibling positions must be unique"
            )
        sibling_positions.add(position_key)
        if node.parent_row_id is None:
            continue
        parent = by_row_id.get(node.parent_row_id)
        if parent is None:
            raise BOQDomainError("ORPHAN_SCOPE_NODE", "Parent node does not exist")
        if (
            parent.project_id != node.project_id
            or parent.revision_id != node.revision_id
        ):
            raise BOQDomainError(
                "CROSS_SCOPE_PARENT",
                "Parent must belong to the same project and revision",
            )
        if parent.node_kind == "ITEM":
            raise BOQDomainError(
                "ITEM_CANNOT_PARENT", "An ITEM cannot contain children"
            )

    for node in node_list:
        visited: set[UUID] = set()
        current = node
        while current.parent_row_id is not None:
            if current.row_id in visited:
                raise BOQDomainError("SCOPE_CYCLE", "Scope hierarchy contains a cycle")
            visited.add(current.row_id)
            parent = by_row_id.get(current.parent_row_id)
            if parent is None:
                break
            current = parent


def canonical_request_hash(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def advisory_lock_name(project_id: UUID) -> str:
    return f"boq-v2:project-budget:{project_id}"


async def acquire_project_budget_locks(
    db: AsyncSession,
    project_ids: Iterable[UUID],
) -> None:
    for project_id in sorted(set(project_ids), key=str):
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
            {"lock_name": advisory_lock_name(project_id)},
        )
