from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import base  # noqa: F401  # registers all ORM models before first request

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "AI-Powered Continuous Cyber Risk Quantification and Investment "
        "Optimization Platform — SIH 2026 (SIH26105). Phase 1: project "
        "setup, database, authentication and RBAC."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["health"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX,
    }
