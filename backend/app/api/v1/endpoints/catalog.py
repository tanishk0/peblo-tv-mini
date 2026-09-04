"""Unauthenticated public catalogue endpoints backed only by published snapshots."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.catalogue_storage import CatalogueStorageProvider, LocalCatalogueStorageProvider
from app.services.public_catalogue import PublicCatalogueService


router = APIRouter()


def get_public_catalogue_storage() -> CatalogueStorageProvider:
    """Public reads use the same atomic current-pointer mechanism as publishing."""
    return LocalCatalogueStorageProvider()


def public_catalogue_service(storage: CatalogueStorageProvider = Depends(get_public_catalogue_storage)) -> PublicCatalogueService:
    return PublicCatalogueService(storage)


@router.get("/search")
def search_catalogue(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    section: str | None = Query(default=None),
    catalogue: PublicCatalogueService = Depends(public_catalogue_service),
) -> dict:
    """Case-insensitively search/filter the current published JSON snapshot."""
    try:
        return catalogue.search(q=q, category=category, language=language, section=section)
    except LookupError as error:
        raise HTTPException(404, detail=str(error))


@router.get("")
def get_catalogue(catalogue: PublicCatalogueService = Depends(public_catalogue_service)) -> dict:
    """Return the complete current published snapshot, never CMS table data."""
    try:
        return catalogue.current()
    except LookupError as error:
        raise HTTPException(404, detail=str(error))
