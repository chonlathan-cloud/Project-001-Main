"""
Project_001 Backend - The Hybrid Brain for Modern Construction Management
FastAPI Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import (
    auth,
    bills,
    chat,
    dashboard,
    insights,
    input_requests,
    profile,
    projects,
    settings,
    subcontractor,
)

app_settings = get_settings()

app = FastAPI(
    title="Project_001 API",
    description="The Hybrid Brain for Modern Construction Management",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS Middleware (allow all origins for development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register all API v1 Routers
# ---------------------------------------------------------------------------
API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(dashboard.router, prefix=API_V1_PREFIX)
app.include_router(insights.router, prefix=API_V1_PREFIX)
app.include_router(projects.router, prefix=API_V1_PREFIX)
app.include_router(bills.router, prefix=API_V1_PREFIX)
app.include_router(input_requests.router, prefix=API_V1_PREFIX)
app.include_router(profile.router, prefix=API_V1_PREFIX)
app.include_router(subcontractor.router, prefix=API_V1_PREFIX)
app.include_router(settings.router, prefix=API_V1_PREFIX)
app.include_router(chat.router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health-check endpoint."""
    return {"status": "ok"}
