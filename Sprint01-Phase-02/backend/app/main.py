from fastapi import FastAPI

from app.config.settings import settings
from app.routers import health, root

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sprint 1 API foundation for SecureGate AI.",
)

app.include_router(root.router)
app.include_router(health.router)
