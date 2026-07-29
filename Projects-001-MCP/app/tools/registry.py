"""Stable Product MCP domain and tool inventory."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.policy.models import AccessContext


class DomainName(StrEnum):
    SYSTEM_CATALOG = "system_catalog"
    GCP_OPERATIONS = "gcp_operations"
    PROJECTS_BOQ = "projects_boq"
    FINANCE_PAYMENTS = "finance_payments"
    USERS_ACCESS = "users_access"
    INSPECTION = "inspection"
    DAILY_REPORTS = "daily_reports"
    GCS_FILES = "gcs_files"
    DASHBOARD_INSIGHTS = "dashboard_insights"
    HISTORY_AUDIT = "history_audit"


@dataclass(frozen=True, slots=True)
class DomainDefinition:
    name: DomainName
    title: str
    description: str
    required_permissions: frozenset[str]
    requires_project_scope: bool = False


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    domain: DomainName
    required_permissions: frozenset[str]
    planned_phase: str
    implemented: bool = False
    requires_project_scope: bool = False
    sensitive: bool = False


DOMAINS = (
    DomainDefinition(
        DomainName.SYSTEM_CATALOG,
        "System Catalog",
        "Permission-filtered Product MCP capabilities and contracts.",
        frozenset({"mcp_access"}),
    ),
    DomainDefinition(
        DomainName.GCP_OPERATIONS,
        "GCP Operations",
        "Curated health, Cloud Run and bounded application-error facts.",
        frozenset({"mcp_access", "infrastructure_read"}),
    ),
    DomainDefinition(
        DomainName.PROJECTS_BOQ,
        "Projects and BOQ",
        "Authorized projects, BOQ current state and version history.",
        frozenset({"mcp_access"}),
        True,
    ),
    DomainDefinition(
        DomainName.FINANCE_PAYMENTS,
        "Finance and Payments",
        "Exact project financial summaries, records and payment state.",
        frozenset({"mcp_access", "financial_data_read"}),
        True,
    ),
    DomainDefinition(
        DomainName.USERS_ACCESS,
        "Users and Access",
        "Current access and authorized project membership views.",
        frozenset({"mcp_access"}),
    ),
    DomainDefinition(
        DomainName.INSPECTION,
        "Inspection",
        "Authorized rounds, defects, events and file metadata.",
        frozenset({"mcp_access"}),
        True,
    ),
    DomainDefinition(
        DomainName.DAILY_REPORTS,
        "Daily Reports",
        "Authorized daily reports, immutable versions and share status.",
        frozenset({"mcp_access"}),
        True,
    ),
    DomainDefinition(
        DomainName.GCS_FILES,
        "Documents and Files",
        "Opaque metadata and bounded content through the Document Gateway.",
        frozenset({"mcp_access"}),
        True,
    ),
    DomainDefinition(
        DomainName.DASHBOARD_INSIGHTS,
        "Dashboard and Insights",
        "Backend-derived summaries with calculation and source metadata.",
        frozenset({"mcp_access", "financial_data_read"}),
        True,
    ),
    DomainDefinition(
        DomainName.HISTORY_AUDIT,
        "History and Audit",
        "Authorized Product MCP audit events and version-aware history.",
        frozenset({"mcp_access", "audit_log_read"}),
    ),
)


def _tool(
    name: str,
    domain: DomainName,
    phase: str,
    *permissions: str,
    implemented: bool = False,
    project: bool = False,
    sensitive: bool = False,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        domain=domain,
        required_permissions=frozenset({"mcp_access", *permissions}),
        planned_phase=phase,
        implemented=implemented,
        requires_project_scope=project,
        sensitive=sensitive,
    )


TOOLS = (
    _tool("get_system_catalog", DomainName.SYSTEM_CATALOG, "foundation", implemented=True),
    _tool("describe_domain", DomainName.SYSTEM_CATALOG, "foundation", implemented=True),
    _tool("search", DomainName.SYSTEM_CATALOG, "core_pilot", implemented=True),
    _tool("fetch", DomainName.SYSTEM_CATALOG, "core_pilot", implemented=True),
    _tool("list_projects", DomainName.PROJECTS_BOQ, "core_pilot", implemented=True, project=True),
    _tool("get_project", DomainName.PROJECTS_BOQ, "core_pilot", implemented=True, project=True),
    _tool(
        "get_project_summary",
        DomainName.PROJECTS_BOQ,
        "core_pilot",
        implemented=True,
        project=True,
    ),
    _tool("get_boq_current", DomainName.PROJECTS_BOQ, "core_pilot", implemented=True, project=True),
    _tool(
        "list_boq_versions",
        DomainName.PROJECTS_BOQ,
        "core_pilot",
        implemented=True,
        project=True,
    ),
    _tool("get_boq_version", DomainName.PROJECTS_BOQ, "core_pilot", implemented=True, project=True),
    _tool(
        "compare_boq_versions",
        DomainName.PROJECTS_BOQ,
        "core_pilot",
        implemented=True,
        project=True,
    ),
    _tool(
        "get_project_financial_summary",
        DomainName.FINANCE_PAYMENTS,
        "finance_documents",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "search_financial_records",
        DomainName.FINANCE_PAYMENTS,
        "finance_documents",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "get_payment",
        DomainName.FINANCE_PAYMENTS,
        "finance_documents",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "get_payment_document_status",
        DomainName.FINANCE_PAYMENTS,
        "finance_documents",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool("get_current_access", DomainName.USERS_ACCESS, "foundation", implemented=True),
    _tool(
        "list_project_access",
        DomainName.USERS_ACCESS,
        "core_pilot",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "get_user_access",
        DomainName.USERS_ACCESS,
        "core_pilot",
        implemented=True,
        sensitive=True,
    ),
    _tool(
        "list_inspection_items",
        DomainName.INSPECTION,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "get_inspection_item",
        DomainName.INSPECTION,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "list_daily_reports",
        DomainName.DAILY_REPORTS,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "get_daily_report",
        DomainName.DAILY_REPORTS,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "list_daily_report_versions",
        DomainName.DAILY_REPORTS,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "get_report_share_status",
        DomainName.DAILY_REPORTS,
        "project_operations",
        implemented=True,
        project=True,
    ),
    _tool(
        "search_documents",
        DomainName.GCS_FILES,
        "finance_documents",
        implemented=True,
        project=True,
    ),
    _tool(
        "get_document_metadata",
        DomainName.GCS_FILES,
        "finance_documents",
        implemented=True,
        project=True,
    ),
    _tool(
        "read_document_content",
        DomainName.GCS_FILES,
        "finance_documents",
        "sensitive_documents_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "get_dashboard_summary",
        DomainName.DASHBOARD_INSIGHTS,
        "project_operations",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "get_project_insights",
        DomainName.DASHBOARD_INSIGHTS,
        "project_operations",
        "financial_data_read",
        implemented=True,
        project=True,
        sensitive=True,
    ),
    _tool(
        "search_audit_events",
        DomainName.HISTORY_AUDIT,
        "project_operations",
        "audit_log_read",
        implemented=True,
        sensitive=True,
    ),
    _tool(
        "get_audit_event",
        DomainName.HISTORY_AUDIT,
        "project_operations",
        "audit_log_read",
        implemented=True,
        sensitive=True,
    ),
    _tool(
        "get_system_health",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
    ),
    _tool(
        "get_gcp_resource_summary",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
    ),
    _tool(
        "get_cloud_run_status",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
    ),
    _tool(
        "search_application_errors",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
        sensitive=True,
    ),
    _tool(
        "get_data_source_health",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
    ),
    _tool(
        "get_processing_status",
        DomainName.GCP_OPERATIONS,
        "gcp_operations",
        "infrastructure_read",
    ),
)


class ToolRegistry:
    def __init__(self) -> None:
        self.domains = {domain.name: domain for domain in DOMAINS}
        self.tools = {tool.name: tool for tool in TOOLS}

    def tool(self, name: str) -> ToolDefinition:
        return self.tools[name]

    def domain_visible(self, domain: DomainDefinition, access: AccessContext) -> bool:
        if access.role == "owner":
            return True
        if not domain.required_permissions.issubset(access.permissions):
            return False
        if domain.requires_project_scope:
            return access.all_projects_read or bool(access.assigned_project_ids)
        return True

    def visible_domain_items(self, access: AccessContext) -> list[dict[str, object]]:
        return [
            self.domain_item(domain, access)
            for domain in DOMAINS
            if self.domain_visible(domain, access)
        ]

    def domain_item(
        self,
        domain: DomainDefinition,
        access: AccessContext,
    ) -> dict[str, object]:
        visible_tools = [
            tool
            for tool in TOOLS
            if tool.domain == domain.name and self._tool_visible(tool, access)
        ]
        return {
            "name": domain.name.value,
            "title": domain.title,
            "description": domain.description,
            "available_tools": [tool.name for tool in visible_tools if tool.implemented],
            "planned_tool_count": sum(not tool.implemented for tool in visible_tools),
        }

    @staticmethod
    def _tool_visible(tool: ToolDefinition, access: AccessContext) -> bool:
        if access.role == "owner":
            return True
        if not tool.required_permissions.issubset(access.permissions):
            return False
        if tool.requires_project_scope:
            return access.all_projects_read or bool(access.assigned_project_ids)
        return True
