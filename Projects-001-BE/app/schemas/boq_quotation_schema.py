"""Phase 3 quotation lifecycle, snapshot, acceptance, and export contracts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


Quantity = Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=4)]


class BOQV2ExpectedVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


class BOQV2CreateAlternativeRequest(BOQV2ExpectedVersionRequest):
    alternative_group_id: UUID | None = None


class BOQV2DeductionLineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_revision_id: UUID
    target_logical_id: UUID
    quantity: Quantity


class BOQV2CreateChangeOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: UUID
    baseline_version: int = Field(ge=1)
    direction: Literal["ADD", "DEDUCT"]
    deductions: list[BOQV2DeductionLineRequest] = Field(
        default_factory=list, max_length=500
    )

    @model_validator(mode="after")
    def validate_direction_payload(self) -> "BOQV2CreateChangeOrderRequest":
        if self.direction == "ADD" and self.deductions:
            raise ValueError("ADD change orders cannot include deduction targets")
        if self.direction == "DEDUCT" and not self.deductions:
            raise ValueError("DEDUCT change orders require deduction targets")
        identities = [item.target_logical_id for item in self.deductions]
        if len(identities) != len(set(identities)):
            raise ValueError("deduction targets must be unique")
        return self


class BOQV2ReplacementDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: UUID
    baseline_version: int = Field(ge=1)
    retain_change_order_revision_ids: list[UUID] = Field(
        default_factory=list, max_length=500
    )
    absorb_change_order_revision_ids: list[UUID] = Field(
        default_factory=list, max_length=500
    )

    @model_validator(mode="after")
    def validate_membership(self) -> "BOQV2ReplacementDecision":
        retain = set(self.retain_change_order_revision_ids)
        absorb = set(self.absorb_change_order_revision_ids)
        if retain.intersection(absorb):
            raise ValueError("a change order cannot be both retained and absorbed")
        return self


class BOQV2RecordAcceptanceRequest(BOQV2ExpectedVersionRequest):
    agreed_date: date
    evidence_reference: str | None = Field(default=None, max_length=1000)
    note: str | None = Field(default=None, max_length=4000)
    replacement: BOQV2ReplacementDecision | None = None


class BOQV2TransitionRequest(BOQV2ExpectedVersionRequest):
    reason: str | None = Field(default=None, max_length=4000)


class BOQV2SnapshotSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    project_id: UUID
    document_id: UUID
    document_number: str
    revision_id: UUID
    revision_number: int
    source_version: int
    purpose: Literal["PREVIEW", "ISSUE"]
    lifecycle_status: Literal["DRAFT", "ISSUED"]
    calculation_version: str
    payload_sha256: str
    created_at: str


class BOQV2QuotationPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot: BOQV2SnapshotSummary
    document: dict[str, object]


class BOQV2ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    audience: Literal["CUSTOMER", "INTERNAL"]
    file_format: Literal["XLSX", "PDF"]

    @model_validator(mode="after")
    def validate_audience_format(self) -> "BOQV2ExportRequest":
        if self.audience == "INTERNAL" and self.file_format != "XLSX":
            raise ValueError("internal consolidated export is XLSX-only in Phase 3")
        return self


class BOQV2ExportArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID
    project_id: UUID
    document_id: UUID
    revision_id: UUID
    snapshot_id: UUID
    calculation_version: str
    audience: Literal["CUSTOMER", "INTERNAL"]
    file_format: Literal["XLSX", "PDF"]
    cost_plan_version: int | None = None
    status: Literal["PENDING", "READY", "FAILED"]
    filename: str
    mime_type: str
    sha256: str | None = None
    size_bytes: int | None = None
    created_at: str
    completed_at: str | None = None
    download_url: str | None = None
    download_expires_in_minutes: int | None = None


class BOQV2ActiveBaselineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_id: UUID
    baseline_version: int
    project_id: UUID
    main_revision_id: UUID
    main_snapshot_id: UUID
    accepted_change_order_revision_ids: list[UUID] = Field(default_factory=list)
    net_sell_ex_vat: str
    calculation_version: str
    activated_at: str


class BOQV2AcceptanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acceptance_id: UUID
    revision_id: UUID
    snapshot_id: UUID
    agreed_date: date
    actor: str
    evidence_reference: str | None = None
    note: str | None = None
    recorded_at: str
    baseline: BOQV2ActiveBaselineResponse
