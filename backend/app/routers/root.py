from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(tags=["root"])


@router.get("/")
def read_root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "version": settings.app_version,
    }
