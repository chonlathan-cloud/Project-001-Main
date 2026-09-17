"""Public Phase 2 contracts for the native BOQ draft workspace."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


Quantity = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]


class BOQV2CostComponentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    component_type: Literal["MATERIAL", "LABOR"]
    quantity_basis: Literal["INHERITED", "OVERRIDDEN"] = "INHERITED"
    quantity: Quantity | None = None
    unit: str | None = Field(default=None, max_length=120)
    specification: str | None = Field(default=None, max_length=4000)
    cost_state: Literal["UNKNOWN", "PRICED", "NOT_APPLICABLE"] = "UNKNOWN"
    unit_rate: Quantity | None = None
    explicit_zero_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_state(self) -> "BOQV2CostComponentDraft":
        if self.quantity_basis == "INHERITED" and self.quantity is not None:
            raise ValueError("inherited component quantity must be omitted")
        if self.quantity_basis == "OVERRIDDEN" and self.quantity is None:
            raise ValueError("overridden component quantity is required")
        if self.cost_state in {"UNKNOWN", "NOT_APPLICABLE"}:
            if self.unit_rate is not None:
                raise ValueError(f"{self.cost_state} cost cannot include a unit rate")
        elif self.unit_rate is None:
            raise ValueError("priced cost requires a unit rate")
        elif self.unit_rate == 0 and not str(self.explicit_zero_reason or "").strip():
            raise ValueError("explicit zero cost requires a reason")
        return self


class BOQV2ScopeNodeDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    logical_id: UUID
    parent_logical_id: UUID | None = None
    node_kind: Literal["SECTION", "CATEGORY", "SUBCATEGORY", "ITEM"]
    inclusion_state: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"] = "REQUIRED"
    position: int = Field(ge=0)
    item_code: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    specification: str | None = Field(default=None, max_length=4000)
    quantity: Quantity | None = None
    unit: str | None = Field(default=None, max_length=120)
    sell_material_unit_rate: Quantity | None = None
    sell_labor_unit_rate: Quantity | None = None
    components: list[BOQV2CostComponentDraft] = Field(default_factory=list, max_length=2)
    confirm_financial_discard: bool = False

    @model_validator(mode="after")
    def validate_node_shape(self) -> "BOQV2ScopeNodeDraft":
        component_types = [item.component_type for item in self.components]
        if len(component_types) != len(set(component_types)):
            raise ValueError("component types must be unique within an item")
        if self.node_kind != "ITEM" and any(
            value is not None
            for value in (
                self.quantity,
                self.unit,
                self.sell_material_unit_rate,
                self.sell_labor_unit_rate,
            )
        ):
            raise ValueError("structural nodes cannot contain financial fields")
        if self.node_kind != "ITEM" and self.components:
            raise ValueError("structural nodes cannot contain cost components")
        return self


class BOQV2CreateDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_kind: Literal["MAIN"] = "MAIN"


class BOQV2SaveDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    nodes: list[BOQV2ScopeNodeDraft] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def validate_node_identity(self) -> "BOQV2SaveDraftRequest":
        logical_ids = [node.logical_id for node in self.nodes]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("logical IDs must be unique within a revision")
        row_ids = [node.id for node in self.nodes if node.id is not None]
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("revision row IDs must be unique")
        return self


class BOQV2CostComponentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    component_type: Literal["MATERIAL", "LABOR"]
    quantity_basis: Literal["INHERITED", "OVERRIDDEN"]
    quantity: str
    unit: str | None = None
    specification: str | None = None
    basis_version: int
    cost_state: Literal["UNKNOWN", "PRICED", "NOT_APPLICABLE"]
    unit_rate: str | None = None
    total: str | None = None
    explicit_zero_reason: str | None = None


class BOQV2ScopeNodeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    logical_id: UUID
    parent_logical_id: UUID | None = None
    node_kind: Literal["SECTION", "CATEGORY", "SUBCATEGORY", "ITEM"]
    inclusion_state: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"]
    position: int
    depth: int
    display_path: str
    item_code: str | None = None
    description: str | None = None
    specification: str | None = None
    quantity: str | None = None
    unit: str | None = None
    sell_material_unit_rate: str | None = None
    sell_labor_unit_rate: str | None = None
    sell_total: str
    components: list[BOQV2CostComponentResponse] = Field(default_factory=list)


class BOQV2CompletenessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["COMPLETE", "INCOMPLETE"]
    required_count: int = Field(ge=0)
    priced_count: int = Field(ge=0)
    missing_component_ids: list[UUID] = Field(default_factory=list)


class BOQV2RevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    project_name: str
    document_id: UUID
    revision_id: UUID
    predecessor_revision_id: UUID | None = None
    document_kind: Literal["MAIN", "ALTERNATIVE", "CHANGE_ORDER"]
    status: Literal["DRAFT", "ISSUED", "ACCEPTED", "WITHDRAWN", "REJECTED", "SUPERSEDED"]
    revision_number: int
    version: int
    calculation_version: str
    net_sell_ex_vat: str
    known_estimated_cost: str
    forecast_cost: str | None = None
    forecast_margin: str | None = None
    completeness: BOQV2CompletenessResponse
    nodes: list[BOQV2ScopeNodeResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class BOQV2RevisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    document_id: UUID
    document_kind: Literal["MAIN", "ALTERNATIVE", "CHANGE_ORDER"]
    revision_number: int
    status: str
    version: int
    net_sell_ex_vat: str
    completeness_state: str
    updated_at: str


class BOQV2ReuseSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    project_name: str
    revision_id: UUID
    document_id: UUID
    revision_number: int
    status: str
    net_sell_ex_vat: str
    updated_at: str


class BOQV2WorkspaceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    project_name: str
    rollout_enabled: bool
    can_edit: bool
    active_source_kind: Literal["LEGACY", "V2"]
    legacy_available: bool
    legacy_row_count: int
    revisions: list[BOQV2RevisionSummary] = Field(default_factory=list)
    reuse_sources: list[BOQV2ReuseSource] = Field(default_factory=list)

