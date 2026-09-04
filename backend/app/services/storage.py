"""Storage interface and local implementation for CMS artwork assets."""
from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath

from app.core.config import settings


class StorageProvider(ABC):
    """Interface used by artwork business logic, independent of a storage vendor."""

    @abstractmethod
    def save(self, content: bytes, storage_key: str) -> str:
        """Persist content and return its storage key."""

    @abstractmethod
    def get_url(self, storage_key: str) -> str:
        """Return a URL suitable for displaying a stored object."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete an object when a database operation cannot be completed."""


class LocalStorageProvider(StorageProvider):
    """Filesystem implementation for development and this assignment."""

    def __init__(self, root: Path | None = None, url_prefix: str | None = None):
        self.root = (root or settings.local_artwork_storage_path).resolve()
        self.url_prefix = (url_prefix or settings.LOCAL_ARTWORK_URL_PREFIX).rstrip("/")

    def _path_for(self, storage_key: str) -> Path:
        key_path = PurePosixPath(storage_key)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise ValueError("Invalid storage key")
        path = (self.root / Path(*key_path.parts)).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def save(self, content: bytes, storage_key: str) -> str:
        destination = self._path_for(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.write_bytes(content)
        except OSError:
            # A failed write can still leave a partial file on some filesystems.
            try:
                destination.unlink()
            except FileNotFoundError:
                pass
            raise
        return storage_key

    def get_url(self, storage_key: str) -> str:
        self._path_for(storage_key)  # Apply the same traversal protection.
        return f"{self.url_prefix}/{storage_key}"

    def delete(self, storage_key: str) -> None:
        try:
            self._path_for(storage_key).unlink()
        except FileNotFoundError:
            pass
