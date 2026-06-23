from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.models.database import init_database
from app.routers import health, reports, root, scans

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SecureGate AI report ingestion, security decision, recommendation, and export API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root.router)
app.include_router(health.router)
app.include_router(scans.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup() -> None:
    init_database()
