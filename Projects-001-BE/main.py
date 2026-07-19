"""
Project_001 Backend - The Hybrid Brain for Modern Construction Management
FastAPI Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.observability import (
    RequestObservabilityMiddleware,
    configure_structured_logging,
)
from app.core.rate_limit import RateLimitMiddleware, daily_report_rate_limit_rules
from app.api.v1 import (
    auth,
    bills,
    chat,
    daily_reports,
    dashboard,
    insights,
    inspection,
    input_requests,
    profile,
    projects,
    settings,
    subcontractor,
)

app_settings = get_settings()
configure_structured_logging(app_settings.log_level)

app = FastAPI(
    title="Project_001 API",
    description="The Hybrid Brain for Modern Construction Management",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# Security and observability middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    RateLimitMiddleware,
    enabled=app_settings.rate_limit_enabled,
    rules=daily_report_rate_limit_rules(app_settings),
)

cors_origins = app_settings.cors_origins
if not cors_origins and app_settings.is_development:
    cors_origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestObservabilityMiddleware)

# ---------------------------------------------------------------------------
# Register all API v1 Routers
# ---------------------------------------------------------------------------
API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)
app.include_router(insights.router, prefix=API_V1_PREFIX)
app.include_router(inspection.router, prefix=API_V1_PREFIX)
app.include_router(projects.router, prefix=API_V1_PREFIX)
app.include_router(bills.router, prefix=API_V1_PREFIX)
app.include_router(input_requests.router, prefix=API_V1_PREFIX)
app.include_router(profile.router, prefix=API_V1_PREFIX)
app.include_router(subcontractor.router, prefix=API_V1_PREFIX)
app.include_router(settings.router, prefix=API_V1_PREFIX)
app.include_router(chat.router, prefix=API_V1_PREFIX)
app.include_router(daily_reports.router, prefix=API_V1_PREFIX)
app.include_router(daily_reports.internal_router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health-check endpoint."""
    return {"status": "ok"}
