"""CMS artwork upload endpoint with server-side image validation."""
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_editor
from app.models.artwork import Artwork
from app.models.enums import ArtworkType
from app.models.episode import Episode
from app.schemas.artwork import ArtworkResponse
from app.services.reference import reference_data
from app.services.storage import LocalStorageProvider, StorageProvider


router = APIRouter()


def get_storage_provider() -> StorageProvider:
    """Dependency seam for replacing local disk with R2 in a future phase."""
    return LocalStorageProvider()


def artwork_spec(artwork_type: str) -> dict:
    spec = reference_data()["artwork_specs"].get(artwork_type)
    if not spec:
        choices = ", ".join(sorted(reference_data()["artwork_specs"]))
        raise HTTPException(422, detail=f"Artwork type must be one of: {choices}.")
    return spec


def inspect_image(content: bytes, artwork_type: str, spec: dict) -> tuple[int, int, str]:
    try:
        image = Image.open(BytesIO(content))
        image.load()
        width, height = image.size
        image_format = image.format or "image"
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, detail="Please upload a valid image file.")

    expected_width, expected_height = spec["target_px"]
    label = artwork_type.capitalize()
    uploaded = f"{width}\u00d7{height}"
    if width * expected_height != height * expected_width:
        raise HTTPException(
            422,
            detail=(f"{label} must be {expected_width}\u00d7{expected_height} ({spec['aspect']}). "
                    f"Uploaded image is {uploaded}."),
        )
    if (width, height) != (expected_width, expected_height):
        raise HTTPException(
            422,
            detail=f"{label} must be {expected_width}\u00d7{expected_height}. Uploaded image is {uploaded}.",
        )
    return width, height, image_format


def image_extension(image_format: str) -> str:
    return {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif", "BMP": "bmp", "TIFF": "tiff"}.get(image_format.upper(), "img")


def remove_stored_file(storage: StorageProvider, storage_key: str) -> None:
    """Best-effort cleanup that never masks the editor-facing database error."""
    try:
        storage.delete(storage_key)
    except OSError:
        pass


@router.post("/episodes/{episode_id}/artwork", response_model=ArtworkResponse, status_code=status.HTTP_201_CREATED)
async def upload_artwork(
    episode_id: str,
    artwork_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
    _=Depends(require_editor),
) -> ArtworkResponse:
    """Validate and save one required artwork variant for an episode."""
    spec = artwork_spec(artwork_type)
    episode = db.get(Episode, episode_id)
    if not episode:
        raise HTTPException(404, detail="Episode not found")

    max_bytes = int(spec["max_kb"]) * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(422, detail=f"{artwork_type.capitalize()} must be no larger than {spec['max_kb']} KB.")
    if not content:
        raise HTTPException(422, detail="Please choose an image file to upload.")

    width, height, file_format = inspect_image(content, artwork_type, spec)
    artwork_enum = ArtworkType(artwork_type)
    if db.query(Artwork).filter(Artwork.episode_id == episode_id, Artwork.type == artwork_enum).first():
        raise HTTPException(409, detail=f"This episode already has {artwork_type} artwork. Replace or remove it before uploading another.")

    storage_key = f"episodes/{episode_id}/{artwork_type}-{uuid4().hex}.{image_extension(file_format)}"
    try:
        saved_key = storage.save(content, storage_key)
    except (OSError, ValueError):
        raise HTTPException(500, detail="Artwork could not be saved. Please try again.")

    artwork = Artwork(
        episode_id=episode_id,
        type=artwork_enum,
        storage_key=saved_key,
        width=width,
        height=height,
        file_size_bytes=len(content),
    )
    try:
        db.add(artwork)
        db.commit()
        db.refresh(artwork)
    except IntegrityError:
        db.rollback()
        remove_stored_file(storage, saved_key)
        raise HTTPException(409, detail=f"This episode already has {artwork_type} artwork. Replace or remove it before uploading another.")
    except SQLAlchemyError:
        db.rollback()
        remove_stored_file(storage, saved_key)
        raise HTTPException(500, detail="Artwork details could not be saved. Please try again.")

    return ArtworkResponse(
        id=artwork.id,
        episode_id=artwork.episode_id,
        type=artwork.type,
        storage_key=artwork.storage_key,
        url=storage.get_url(artwork.storage_key),
        width=artwork.width,
        height=artwork.height,
        file_size_bytes=artwork.file_size_bytes,
        created_at=artwork.created_at,
    )
