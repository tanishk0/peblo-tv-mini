from fastapi import APIRouter

from app.api.v1.endpoints import admin, artwork, auth, catalog, health
from app.api.v1.endpoints.content import episodes_router, seasons_router, shows_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["cms-admin"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["public-catalogue"])
api_router.include_router(artwork.router, tags=["cms-artwork"])
api_router.include_router(shows_router, prefix="/shows", tags=["cms-shows"])
api_router.include_router(seasons_router, tags=["cms-seasons"])
api_router.include_router(episodes_router, prefix="/episodes", tags=["cms-episodes"])
