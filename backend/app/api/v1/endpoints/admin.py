"""Admin-only CMS operations."""
from datetime import datetime, timezone
from hashlib import sha256
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.enums import PublishRunStatus
from app.models.publish_run import PublishRun
from app.models.user import User
from app.schemas.catalogue import PublishCatalogueResponse
from app.schemas.validation import ValidationReport
from app.services.catalogue import CatalogueBuilder
from app.services.catalogue_storage import CatalogueStorageProvider, LocalCatalogueStorageProvider
from app.services.validation import ValidationService


router = APIRouter()


def get_catalogue_storage() -> CatalogueStorageProvider:
    """Dependency seam for an R2-backed catalogue store in a future phase."""
    return LocalCatalogueStorageProvider()


@router.get("/validation-report", response_model=ValidationReport)
def validation_report(
    db: Session = Depends(get_db),
    _=Depends(require_admin),
) -> ValidationReport:
    """Return every current blocker that prevents a safe catalogue publish."""
    return ValidationReport.model_validate(ValidationService(db).report())


@router.post("/catalog/publish", response_model=PublishCatalogueResponse, status_code=status.HTTP_201_CREATED)
def publish_catalogue(
    db: Session = Depends(get_db),
    storage: CatalogueStorageProvider = Depends(get_catalogue_storage),
    admin_user: User = Depends(require_admin),
) -> PublishCatalogueResponse:
    """Validate, build, and atomically activate one immutable catalogue version."""
    run = PublishRun(triggered_by_user_id=admin_user.id, status=PublishRunStatus.PENDING)
    db.add(run)
    db.commit()
    db.refresh(run)

    validation = ValidationService(db).report()
    if not validation["can_publish"]:
        run.status = PublishRunStatus.FAILED
        run.error_message = f"Publishing blocked by {validation['total_issues']} validation issue(s)."
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=422,
            detail={"message": run.error_message, "validation_report": validation},
        )

    try:
        run.status = PublishRunStatus.RUNNING
        db.commit()
        builder = CatalogueBuilder(db)
        catalogue = builder.build()
        payload = json.dumps(catalogue, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        catalogue_version = "v-" + sha256(payload).hexdigest()[:16]
        storage_key = storage.write_version(catalogue_version, payload)
        storage.switch_current(catalogue_version, storage_key)

        run.status = PublishRunStatus.SUCCESS
        run.show_count = builder.show_count
        run.episode_count = builder.episode_count
        run.catalogue_version = catalogue_version
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
    except Exception:
        db.rollback()
        run.status = PublishRunStatus.FAILED
        run.error_message = "Catalogue could not be published. The previous live catalogue is still active."
        run.completed_at = datetime.now(timezone.utc)
        db.add(run)
        db.commit()
        raise HTTPException(500, detail=run.error_message)

    return PublishCatalogueResponse(
        status=run.status,
        publish_run_id=run.id,
        catalogue_version=run.catalogue_version,
        show_count=run.show_count,
        episode_count=run.episode_count,
        completed_at=run.completed_at,
    )
