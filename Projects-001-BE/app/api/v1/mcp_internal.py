"""Service-authenticated, read-only Product MCP Backend contracts."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.service_auth import ServicePrincipal, require_mcp_service
from app.core.database import get_db
from app.schemas.mcp_schema import (
    McpAccessContext,
    McpBOQCompareRequest,
    McpBOQVersionRequest,
    McpBOQVersionsRequest,
    McpFetchRequest,
    McpDocumentContentRequest,
    McpDocumentRequest,
    McpDocumentSearchRequest,
    McpFinancialSearchRequest,
    McpDailyReportRequest,
    McpDailyReportsListRequest,
    McpDailyReportVersionsRequest,
    McpDashboardSummaryRequest,
    McpInspectionListRequest,
    McpInspectionRequest,
    McpPaymentRequest,
    McpPrincipalRequest,
    McpProjectAccessRequest,
    McpProjectListRequest,
    McpProjectRequest,
    McpProjectSummaryRequest,
    McpProjectFinancialSummaryRequest,
    McpProjectInsightsRequest,
    McpProcessingStatusRequest,
    McpSearchRequest,
    McpUserAccessRequest,
)
from app.schemas.responses import StandardResponse
from app.services import mcp_read_service
from app.services import mcp_finance_document_service
from app.services import mcp_project_operations_service
from app.services import mcp_processing_service
from app.services.mcp_access_service import resolve_mcp_access

router = APIRouter(prefix="/internal/mcp", tags=["Internal Product MCP"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="The requested record was not found.",
    )


async def _read(operation: Callable[[], Awaitable[dict[str, Any]]]) -> StandardResponse[dict]:
    try:
        return StandardResponse(data=await operation())
    except mcp_read_service.McpNotFoundOrForbidden as exc:
        raise _not_found() from exc
    except mcp_read_service.McpInvalidInput as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/access-context:resolve",
    response_model=StandardResponse[McpAccessContext],
)
async def resolve_access_context(
    request: McpPrincipalRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
) -> StandardResponse[McpAccessContext]:
    return StandardResponse(data=resolve_mcp_access(request))


@router.post("/search", response_model=StandardResponse[dict])
async def search(
    request: McpSearchRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.search(db, request))


@router.post("/fetch", response_model=StandardResponse[dict])
async def fetch(
    request: McpFetchRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.fetch(db, request))


@router.post("/projects:list", response_model=StandardResponse[dict])
async def list_projects(
    request: McpProjectListRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.list_projects(db, request))


@router.post("/projects:get", response_model=StandardResponse[dict])
async def get_project(
    request: McpProjectRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.get_project(db, request))


@router.post("/projects:summary", response_model=StandardResponse[dict])
async def get_project_summary(
    request: McpProjectSummaryRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.get_project_summary(db, request))


@router.post("/boq:current", response_model=StandardResponse[dict])
async def get_boq_current(
    request: McpProjectRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.get_boq_current(db, request))


@router.post("/boq/versions:list", response_model=StandardResponse[dict])
async def list_boq_versions(
    request: McpBOQVersionsRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.list_boq_versions(db, request))


@router.post("/boq/versions:get", response_model=StandardResponse[dict])
async def get_boq_version(
    request: McpBOQVersionRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.get_boq_version(db, request))


@router.post("/boq/versions:compare", response_model=StandardResponse[dict])
async def compare_boq_versions(
    request: McpBOQCompareRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.compare_boq_versions(db, request))


@router.post("/project-access:list", response_model=StandardResponse[dict])
async def list_project_access(
    request: McpProjectAccessRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.list_project_access(request))


@router.post("/user-access:get", response_model=StandardResponse[dict])
async def get_user_access(
    request: McpUserAccessRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_read_service.get_user_access(request))


@router.post("/finance/projects:summary", response_model=StandardResponse[dict])
async def get_project_financial_summary(
    request: McpProjectFinancialSummaryRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.get_project_financial_summary(db, request)
    )


@router.post("/finance/records:search", response_model=StandardResponse[dict])
async def search_financial_records(
    request: McpFinancialSearchRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.search_financial_records(db, request)
    )


@router.post("/payments:get", response_model=StandardResponse[dict])
async def get_payment(
    request: McpPaymentRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_finance_document_service.get_payment(db, request))


@router.post("/payments/document-status:get", response_model=StandardResponse[dict])
async def get_payment_document_status(
    request: McpPaymentRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.get_payment_document_status(db, request)
    )


@router.post("/documents:search", response_model=StandardResponse[dict])
async def search_documents(
    request: McpDocumentSearchRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_finance_document_service.search_documents(db, request))


@router.post("/documents/metadata:get", response_model=StandardResponse[dict])
async def get_document_metadata(
    request: McpDocumentRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.get_document_metadata(db, request)
    )


@router.post("/documents/content:read", response_model=StandardResponse[dict])
async def read_document_content(
    request: McpDocumentContentRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.read_document_content(db, request)
    )


@router.post("/daily-reports/share-status:get", response_model=StandardResponse[dict])
async def get_report_share_status(
    request: McpProjectRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_finance_document_service.get_report_share_status(db, request)
    )


@router.post("/inspection/items:list", response_model=StandardResponse[dict])
async def list_inspection_items(
    request: McpInspectionListRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.list_inspection_items(db, request)
    )


@router.post("/inspection/items:get", response_model=StandardResponse[dict])
async def get_inspection_item(
    request: McpInspectionRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.get_inspection_item(db, request)
    )


@router.post("/daily-reports:list", response_model=StandardResponse[dict])
async def list_daily_reports(
    request: McpDailyReportsListRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.list_daily_reports(db, request)
    )


@router.post("/daily-reports:get", response_model=StandardResponse[dict])
async def get_daily_report(
    request: McpDailyReportRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.get_daily_report(db, request)
    )


@router.post("/daily-reports/versions:list", response_model=StandardResponse[dict])
async def list_daily_report_versions(
    request: McpDailyReportVersionsRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.list_daily_report_versions(db, request)
    )


@router.post("/dashboard:summary", response_model=StandardResponse[dict])
async def get_dashboard_summary(
    request: McpDashboardSummaryRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.get_dashboard_summary(db, request)
    )


@router.post("/projects/insights:get", response_model=StandardResponse[dict])
async def get_project_insights(
    request: McpProjectInsightsRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(
        lambda: mcp_project_operations_service.get_project_insights(db, request)
    )


@router.post("/processing/status:get", response_model=StandardResponse[dict])
async def get_processing_status(
    request: McpProcessingStatusRequest,
    _caller: ServicePrincipal = Depends(require_mcp_service),
    db: AsyncSession = Depends(get_db),
) -> StandardResponse[dict]:
    return await _read(lambda: mcp_processing_service.get_processing_status(db, request))
