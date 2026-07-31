from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.models.database import init_database
from app.routers import ai, alerts, health, metrics, monitoring, notifications, pipeline, projects, reports, root, scans

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="SecureGate AI workflow automation, report ingestion, security decision, notification, and export API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root.router)
app.include_router(ai.router)
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(scans.router)
app.include_router(pipeline.router)
app.include_router(projects.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(alerts.router)
app.include_router(monitoring.router)


@app.on_event("startup")
def startup() -> None:
    init_database()
