from fastapi import APIRouter

from app.api.v1 import auth, assets, vulnerabilities, threats, controls, risks, financial_risk, compliance, investments, optimization, what_if, ml, assistant

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(vulnerabilities.router)
api_router.include_router(threats.router)
api_router.include_router(controls.router)
api_router.include_router(risks.router)
api_router.include_router(financial_risk.router)
api_router.include_router(compliance.router)
api_router.include_router(investments.router)
api_router.include_router(optimization.router)
api_router.include_router(what_if.router)
api_router.include_router(ml.router)
api_router.include_router(assistant.router)

# Phase 9+ will register additional routers here, e.g.:
# from app.api.v1 import dashboard
# api_router.include_router(dashboard.router)
