from fastapi import Header, HTTPException, status

from app.config.settings import settings


def require_pipeline_api_key(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.securegate_api_key}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing SecureGate API key")
