"""Import all ORM models so SQLAlchemy relationships resolve reliably."""

from app.models.boq import BOQItem, Project
from app.models.boq_v2 import (
    BOQV2AuditEvent,
    BOQV2BaselineChangeOrder,
    BOQV2CommandIdempotency,
    BOQV2CostComponent,
    BOQV2CostPlan,
    BOQV2Document,
    BOQV2ProjectBaseline,
    BOQV2ProjectBudgetSource,
    BOQV2Revision,
    BOQV2ScopeNode,
)
from app.models.chat_history import ChatHistory
from app.models.finance import Installment, Transaction
from app.models.funds import FundAllocation, FundAuditEvent, FundBucket, FundLedgerEntry
from app.models.input_request import (
    InputOptionSuggestion,
    InputPayment,
    InputPaymentConfirmation,
    InputPaymentReferenceCounter,
    InputRequest,
    InputRequestLineItem,
)

__all__ = [
    "Project",
    "BOQItem",
    "BOQV2Document",
    "BOQV2Revision",
    "BOQV2ScopeNode",
    "BOQV2CostPlan",
    "BOQV2CostComponent",
    "BOQV2ProjectBaseline",
    "BOQV2BaselineChangeOrder",
    "BOQV2ProjectBudgetSource",
    "BOQV2CommandIdempotency",
    "BOQV2AuditEvent",
    "Installment",
    "Transaction",
    "FundBucket",
    "FundAllocation",
    "FundLedgerEntry",
    "FundAuditEvent",
    "InputRequest",
    "InputRequestLineItem",
    "InputOptionSuggestion",
    "InputPayment",
    "InputPaymentConfirmation",
    "InputPaymentReferenceCounter",
    "ChatHistory",
]
