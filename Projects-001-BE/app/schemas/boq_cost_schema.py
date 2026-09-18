"""Phase 4 vendor cost, cost-plan, and price database contracts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


Quantity = Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=4)]
Rate = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]
Money = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=2)]
TaxBasis = Literal["EXCLUSIVE_VAT", "INCLUSIVE_VAT", "NO_VAT", "UNKNOWN"]
ComponentType = Literal["MATERIAL", "LABOR"]


class BOQV2VendorCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=500)
    commercial_reference: str | None = Field(default=None, max_length=255)
    linked_party_reference: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=64)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_detail: str | None = Field(default=None, max_length=1000)


class BOQV2VendorResponse(BOQV2VendorCreateRequest):
    id: UUID
    project_id: UUID
    status: Literal["ACTIVE", "ARCHIVED"]
    created_at: str
    updated_at: str


class BOQV2OfferLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: UUID
    component_type: ComponentType
    offered_quantity: Quantity
    unit: str | None = Field(default=None, max_length=120)
    specification: str | None = Field(default=None, max_length=4000)
    unit_rate: Rate
    discount_amount: Money = Decimal("0")
    charges_amount: Money = Decimal("0")


class BOQV2OfferCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vendor_id: UUID
    quotation_reference: str | None = Field(default=None, max_length=255)
    quotation_date: date
    valid_until: date | None = None
    currency: Literal["THB"] = "THB"
    tax_basis: TaxBasis
    tax_rate: Rate | None = None
    discount_type: Literal["NONE", "PERCENT", "FIXED"] = "NONE"
    discount_value: Rate = Decimal("0")
    included_charges: str | None = Field(default=None, max_length=4000)
    charges_amount: Money = Decimal("0")
    evidence_storage_key: str | None = Field(default=None, max_length=2000)
    evidence_filename: str | None = Field(default=None, max_length=255)
    evidence_content_type: str | None = Field(default=None, max_length=120)
    evidence_size_bytes: int | None = Field(default=None, ge=1, le=25 * 1024 * 1024)
    notes: str | None = Field(default=None, max_length=4000)
    lines: list[BOQV2OfferLineRequest] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_offer(self) -> "BOQV2OfferCreateRequest":
        if self.valid_until is not None and self.valid_until < self.quotation_date:
            raise ValueError("valid-until date cannot precede quotation date")
        if self.tax_basis in {"EXCLUSIVE_VAT", "INCLUSIVE_VAT"} and self.tax_rate is None:
            raise ValueError("VAT tax basis requires an explicit tax rate")
        if self.tax_basis in {"NO_VAT", "UNKNOWN"} and self.tax_rate is not None:
            raise ValueError("NO_VAT/UNKNOWN tax basis cannot include a tax rate")
        if self.discount_type == "NONE" and self.discount_value != 0:
            raise ValueError("NONE discount requires zero discount value")
        if self.discount_type == "PERCENT" and self.discount_value > 100:
            raise ValueError("percentage discount cannot exceed 100")
        component_ids = [line.component_id for line in self.lines]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("offer component lines must be unique")
        return self


class BOQV2OfferLineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    component_id: UUID
    scope_node_id: UUID
    component_type: ComponentType
    basis_version: int
    required_quantity: str
    offered_quantity: str
    required_unit: str | None = None
    offered_unit: str | None = None
    required_specification: str | None = None
    offered_specification: str | None = None
    unit_rate: str
    subtotal: str
    discount_amount: str
    charges_amount: str
    original_total: str
    normalized_unit_rate_ex_vat: str | None = None
    normalized_total_ex_vat: str | None = None
    coverage_state: Literal["FULL", "PARTIAL", "EXCESS"]
    comparison_state: Literal[
        "EQUIVALENT", "UNIT_MISMATCH", "SPEC_MISMATCH", "UNIT_AND_SPEC_MISMATCH"
    ]
    basis_fingerprint: str


class BOQV2OfferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    revision_id: UUID
    vendor: BOQV2VendorResponse
    quotation_reference: str | None = None
    quotation_date: date
    valid_until: date | None = None
    expired: bool
    currency: Literal["THB"]
    tax_basis: TaxBasis
    tax_rate: str | None = None
    discount_type: Literal["NONE", "PERCENT", "FIXED"]
    discount_value: str
    included_charges: str | None = None
    charges_amount: str
    evidence_filename: str | None = None
    evidence_content_type: str | None = None
    evidence_size_bytes: int | None = None
    notes: str | None = None
    status: Literal["ACTIVE", "SUPERSEDED", "WITHDRAWN"]
    lines: list[BOQV2OfferLineResponse]
    created_at: str


class BOQV2SelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_line_id: UUID
    expected_cost_plan_version: int = Field(ge=1)
    acknowledge_warning: bool = False
    reason: str | None = Field(default=None, max_length=4000)


class BOQV2SelectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    revision_id: UUID
    scope_node_id: UUID
    component_type: ComponentType
    offer_line_id: UUID
    status: Literal["DRAFT", "CONFIRMED", "STALE", "REPLACED"]
    current: bool
    stale: bool
    warnings: list[str]
    warning_reason: str | None = None
    selected_by: str
    selected_at: str
    confirmed_at: str | None = None


class BOQV2CostEstimatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: UUID
    cost_state: Literal["UNKNOWN", "PRICED", "NOT_APPLICABLE"]
    unit_rate: Rate | None = None
    explicit_zero_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_state(self) -> "BOQV2CostEstimatePatch":
        if self.cost_state == "PRICED" and self.unit_rate is None:
            raise ValueError("priced estimate requires a unit rate")
        if self.cost_state != "PRICED" and self.unit_rate is not None:
            raise ValueError("UNKNOWN/N/A estimate cannot include a unit rate")
        if self.cost_state == "PRICED" and self.unit_rate == 0 and not str(self.explicit_zero_reason or "").strip():
            raise ValueError("explicit zero estimate requires a reason")
        return self


class BOQV2CostEstimateUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    components: list[BOQV2CostEstimatePatch] = Field(min_length=1, max_length=2000)


class BOQV2CostComponentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source_component_id: UUID | None = None
    scope_node_id: UUID
    component_type: ComponentType
    quantity: str
    unit: str | None = None
    specification: str | None = None
    basis_version: int
    cost_state: Literal["UNKNOWN", "PRICED", "NOT_APPLICABLE"]
    original_unit_rate: str | None = None
    original_total: str | None = None
    estimate_unit_rate: str | None = None
    estimate_total: str | None = None
    agreed_unit_rate: str | None = None
    agreed_total: str | None = None
    forecast_total: str | None = None
    selected_vendor_id: UUID | None = None
    selected_offer_line_id: UUID | None = None
    selection_status: str | None = None


class BOQV2CostPlanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    source_baseline_id: UUID | None = None
    version: int
    expected_version: int
    status: Literal["WORKING", "PUBLISHED", "SUPERSEDED"]
    completeness_state: Literal["COMPLETE", "INCOMPLETE"]
    required_count: int
    priced_count: int
    original_estimated_cost: str | None = None
    estimated_cost: str | None = None
    agreed_cost: str | None = None
    forecast_cost: str | None = None
    forecast_margin: str | None = None
    components: list[BOQV2CostComponentResponse]
    published_at: str | None = None
    published_by: str | None = None
    publish_reason: str | None = None


class BOQV2CostPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    expected_baseline_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=4000)
    effective_at: datetime | None = None


class BOQV2CostPublishResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cost_plan: BOQV2CostPlanResponse
    baseline_id: UUID
    baseline_version: int
    source_version: int
    forecast_impact: str | None = None
    completeness_state: Literal["COMPLETE", "INCOMPLETE"]


class BOQV2CatalogPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: UUID | None = None
    source_node_id: UUID | None = None
    code: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=1000)
    specification: str | None = Field(default=None, max_length=4000)
    unit: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=50)
    price_kind: Literal["MATERIAL_SELL", "LABOR_SELL", "MATERIAL_COST", "LABOR_COST"] | None = None
    reference_amount: Rate | None = None
    tax_basis: TaxBasis = "UNKNOWN"
    effective_date: date | None = None
    reason: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def validate_reference(self) -> "BOQV2CatalogPromoteRequest":
        if (self.price_kind is None) != (self.reference_amount is None):
            raise ValueError("price kind and reference amount must be provided together")
        if self.observation_id is None and self.source_node_id is None:
            raise ValueError("promotion requires an observation or project node source")
        return self


class BOQV2ReferencePriceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    expected_item_version: int = Field(ge=1)
    price_kind: Literal["MATERIAL_SELL", "LABOR_SELL", "MATERIAL_COST", "LABOR_COST"]
    amount: Rate
    tax_basis: TaxBasis
    effective_date: date
    source_observation_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=4000)


class BOQV2CatalogItemUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    expected_version: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=1000)
    specification: str | None = Field(default=None, max_length=4000)
    unit: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=50)
    status: Literal["ACTIVE", "ARCHIVED"]
    reason: str = Field(min_length=1, max_length=4000)


class BOQV2CatalogPriceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    price_kind: str
    version: int
    amount: str
    tax_basis: TaxBasis
    effective_date: date
    source_observation_id: UUID | None = None
    reason: str
    current: bool
    created_at: str


class BOQV2CatalogItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    code: str
    name: str
    specification: str | None = None
    unit: str
    category: str | None = None
    tags: list[str]
    status: Literal["ACTIVE", "ARCHIVED"]
    version: int
    current_prices: list[BOQV2CatalogPriceResponse]
    distinct_sample_count: int
    observation_count: int
    created_at: str
    updated_at: str


class BOQV2CatalogPageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BOQV2CatalogItemResponse]
    page: int
    page_size: int
    total: int


class BOQV2PriceObservationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    observation_kind: str
    sample_key: str
    project_id: UUID
    document_id: UUID | None = None
    revision_id: UUID | None = None
    scope_node_id: UUID | None = None
    logical_item_id: UUID | None = None
    component_type: str | None = None
    source_event_type: str
    source_event_id: UUID
    observed_at: str
    quantity: str | None = None
    unit: str | None = None
    specification: str | None = None
    tax_basis: str | None = None
    unit_rate: str
    total: str
    vendor_id: UUID | None = None
    lineage_root_id: UUID


class BOQV2CatalogHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: BOQV2CatalogItemResponse
    prices: list[BOQV2CatalogPriceResponse]
    observations: list[BOQV2PriceObservationResponse]
    distinct_sample_count: int


class BOQV2CatalogReuseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision_version: int = Field(ge=1)
    parent_logical_id: UUID | None = None
    position: int = Field(ge=0)
    quantity: Quantity
    inclusion_state: Literal["REQUIRED", "OPTIONAL", "EXCLUDED"] = "REQUIRED"
    use_reference_prices: bool = True
