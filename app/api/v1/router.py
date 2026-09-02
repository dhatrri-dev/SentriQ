from fastapi import APIRouter
from app.api.v1.endpoints import analytics, blocklist, cases, health, rules, transactions

api_router = APIRouter()

# Register all endpoint modules
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(transactions.router)
api_router.include_router(rules.router)
api_router.include_router(cases.router)
api_router.include_router(blocklist.router)
api_router.include_router(analytics.router)
