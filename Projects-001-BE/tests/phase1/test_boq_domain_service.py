from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.services.boq_domain_service import (
    BOQDomainError,
    ScopeIdentity,
    acquire_project_budget_locks,
    assert_expected_version,
    assert_mutable_draft,
    canonical_request_hash,
    validate_scope_hierarchy,
)


def _node(*, project_id, revision_id, parent_id=None, kind="CATEGORY", position=0):
    return ScopeIdentity(
        row_id=uuid4(),
        logical_id=uuid4(),
        project_id=project_id,
        revision_id=revision_id,
        parent_row_id=parent_id,
        node_kind=kind,
        position=position,
    )


def test_valid_hierarchy_supports_item_directly_under_category() -> None:
    project_id = uuid4()
    revision_id = uuid4()
    category = _node(project_id=project_id, revision_id=revision_id)
    item = _node(
        project_id=project_id,
        revision_id=revision_id,
        parent_id=category.row_id,
        kind="ITEM",
    )
    validate_scope_hierarchy([category, item])


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("orphan", "ORPHAN_SCOPE_NODE"),
        ("cross_revision", "CROSS_SCOPE_PARENT"),
        ("item_parent", "ITEM_CANNOT_PARENT"),
        ("cycle", "SCOPE_CYCLE"),
        ("duplicate_position", "DUPLICATE_SCOPE_POSITION"),
    ],
)
def test_invalid_hierarchy_is_rejected(mutation: str, code: str) -> None:
    project_id = uuid4()
    revision_id = uuid4()
    parent = _node(project_id=project_id, revision_id=revision_id)
    child = _node(
        project_id=project_id,
        revision_id=revision_id,
        parent_id=parent.row_id,
        position=1,
    )
    nodes = [parent, child]
    if mutation == "orphan":
        nodes[1] = ScopeIdentity(**{**child.__dict__, "parent_row_id": uuid4()})
    elif mutation == "cross_revision":
        nodes[1] = ScopeIdentity(**{**child.__dict__, "revision_id": uuid4()})
    elif mutation == "item_parent":
        nodes[0] = ScopeIdentity(**{**parent.__dict__, "node_kind": "ITEM"})
    elif mutation == "cycle":
        nodes[0] = ScopeIdentity(**{**parent.__dict__, "parent_row_id": child.row_id})
    else:
        nodes[1] = ScopeIdentity(
            **{**child.__dict__, "parent_row_id": None, "position": parent.position}
        )
    with pytest.raises(BOQDomainError) as exc_info:
        validate_scope_hierarchy(nodes)
    assert exc_info.value.code == code


def test_version_state_and_idempotency_hash_primitives() -> None:
    assert_expected_version(current=3, expected=3)
    assert_mutable_draft("draft")
    with pytest.raises(BOQDomainError) as stale:
        assert_expected_version(current=4, expected=3)
    assert stale.value.code == "STALE_BOQ_VERSION"
    with pytest.raises(BOQDomainError) as immutable:
        assert_mutable_draft("ISSUED")
    assert immutable.value.code == "IMMUTABLE_BOQ_REVISION"
    assert canonical_request_hash({"b": 2, "a": 1}) == canonical_request_hash(
        {"a": 1, "b": 2}
    )


def test_advisory_locks_are_acquired_in_stable_project_order() -> None:
    first = uuid4()
    second = uuid4()
    expected = sorted([first, second], key=str)

    class RecordingSession:
        def __init__(self) -> None:
            self.lock_names: list[str] = []

        async def execute(self, statement, parameters):
            self.lock_names.append(parameters["lock_name"])

    session = RecordingSession()
    asyncio.run(acquire_project_budget_locks(session, [second, first, second]))
    assert session.lock_names == [
        f"boq-v2:project-budget:{project_id}" for project_id in expected
    ]
