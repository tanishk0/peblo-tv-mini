from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("", summary="Health Check")
def health_check() -> dict:
    """Returns the API health status and basic environment info."""
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }
