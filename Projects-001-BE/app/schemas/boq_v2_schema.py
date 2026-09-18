"""Public Phase 2 contracts for the native BOQ draft workspace."""

from __future__ import annotations

from decimal import Decimal
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


Quantity = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]


class BOQV2PaymentScheduleDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=500)
    percentage: Quantity | None = None
    fixed_amount: Annotated[
        Decimal, Field(ge=0, max_digits=20, decimal_places=2)
    ] | None = None

    @model_validator(mode="after")
    def validate_basis(self) -> "BOQV2PaymentScheduleDraft":
        if (self.percentage is None) == (self.fixed_amount is None):
            raise ValueError(
                "payment schedule row requires exactly one percentage or fixed amount"
            )
        return self


class BOQV2QuotationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)
    customer_name: str | None = Field(default=None, max_length=500)
    customer_address: str | None = Field(default=None, max_length=4000)
    customer_tax_id: str | None = Field(default=None, max_length=64)
    customer_contact: str | None = Field(default=None, max_length=255)
    quotation_date: date | None = None
    valid_until: date | None = None
    currency: Literal["THB"] = "THB"
    vat_rate: Quantity = Decimal("7.0000")
    discount_type: Literal["NONE", "PERCENT", "FIXED"] = "NONE"
    discount_value: Quantity = Decimal("0.0000")
    payment_schedule: list[BOQV2PaymentScheduleDraft] = Field(
        default_factory=list, max_length=20
    )
    commercial_terms: list[str] = Field(default_factory=list, max_length=50)
    document_pages: list[
        Literal["BOQ", "PAYMENT_TERMS", "COMMERCIAL_TERMS"]
    ] = Field(
        default_factory=lambda: ["BOQ", "PAYMENT_TERMS", "COMMERCIAL_TERMS"],
        min_length=1,
        max_length=3,
    )

    @model_validator(mode="after")
    def validate_document_terms(self) -> "BOQV2QuotationDraft":
        if (
            self.quotation_date is not None
            and self.valid_until is not None
            and self.valid_until < self.quotation_date
        ):
            raise ValueError("valid-until date cannot precede quotation date")
        if self.discount_type == "NONE" and self.discount_value != 0:
            raise ValueError("NONE discount requires a zero value")
        if self.discount_type == "PERCENT" and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        percentages = [
            item.percentage
            for item in self.payment_schedule
            if item.percentage is not None
        ]
        fixed = [
            item.fixed_amount
            for item in self.payment_schedule
            if item.fixed_amount is not None
        ]
        if percentages and fixed:
            raise ValueError("payment schedule cannot mix percentage and fixed rows")
        if percentages and sum(percentages, Decimal("0")) != Decimal("100"):
            raise ValueError("payment schedule percentages must total 100")
        if len(self.document_pages) != len(set(self.document_pages)):
            raise ValueError("document pages must be unique")
        if "BOQ" not in self.document_pages:
            raise ValueError("document pages must include BOQ")
        for term in self.commercial_terms:
            if not str(term).strip() or len(term) > 2000:
                raise ValueError("commercial terms must be non-empty and <= 2000 chars")
        return self


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
    catalog_item_id: UUID | None = None
    catalog_item_version: int | None = Field(default=None, ge=1)
    source_logical_id: UUID | None = None
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
    quotation: BOQV2QuotationDraft | None = None

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
    catalog_item_id: UUID | None = None
    catalog_item_version: int | None = None
    source_logical_id: UUID | None = None
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


class BOQV2PaymentScheduleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    percentage: str | None = None
    fixed_amount: str | None = None
    amount: str


class BOQV2QuotationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    customer_tax_id: str | None = None
    customer_contact: str | None = None
    quotation_date: date | None = None
    valid_until: date | None = None
    currency: Literal["THB"]
    vat_rate: str
    discount_type: Literal["NONE", "PERCENT", "FIXED"]
    discount_value: str
    subtotal: str
    discount_amount: str
    net_sell_ex_vat: str
    vat_amount: str
    grand_total: str
    payment_schedule: list[BOQV2PaymentScheduleResponse] = Field(default_factory=list)
    commercial_terms: list[str] = Field(default_factory=list)
    document_pages: list[str] = Field(default_factory=list)


class BOQV2RevisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    project_name: str
    document_id: UUID
    document_number: str
    revision_id: UUID
    predecessor_revision_id: UUID | None = None
    document_kind: Literal["MAIN", "ALTERNATIVE", "CHANGE_ORDER"]
    direction: Literal["ADD", "DEDUCT"] | None = None
    alternative_group_id: UUID | None = None
    base_baseline_id: UUID | None = None
    base_baseline_version: int | None = None
    status: Literal["DRAFT", "ISSUED", "ACCEPTED", "WITHDRAWN", "REJECTED", "SUPERSEDED"]
    revision_number: int
    version: int
    calculation_version: str
    net_sell_ex_vat: str
    known_estimated_cost: str
    forecast_cost: str | None = None
    forecast_margin: str | None = None
    completeness: BOQV2CompletenessResponse
    quotation: BOQV2QuotationResponse
    issued_at: str | None = None
    issued_by: str | None = None
    issued_snapshot_id: UUID | None = None
    accepted_at: str | None = None
    accepted_by: str | None = None
    accepted_agreed_date: date | None = None
    acceptance_evidence_reference: str | None = None
    nodes: list[BOQV2ScopeNodeResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class BOQV2RevisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    document_id: UUID
    document_number: str
    document_kind: Literal["MAIN", "ALTERNATIVE", "CHANGE_ORDER"]
    direction: Literal["ADD", "DEDUCT"] | None = None
    alternative_group_id: UUID | None = None
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
    document_number: str
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
    active_baseline_id: UUID | None = None
    active_baseline_version: int | None = None
    active_main_revision_id: UUID | None = None
    active_change_order_revision_ids: list[UUID] = Field(default_factory=list)
    revisions: list[BOQV2RevisionSummary] = Field(default_factory=list)
    reuse_sources: list[BOQV2ReuseSource] = Field(default_factory=list)
