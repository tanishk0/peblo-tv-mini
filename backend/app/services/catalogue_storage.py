"""Immutable-version catalogue storage with an atomic current-pointer switch."""
from abc import ABC, abstractmethod
import json
import os
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile

from app.core.config import settings


class CatalogueStorageProvider(ABC):
    """Storage boundary for atomic catalogue publishing (local disk now, R2 later)."""

    @abstractmethod
    def write_version(self, version: str, payload: bytes) -> str:
        """Write a complete immutable version and return its storage key."""

    @abstractmethod
    def switch_current(self, version: str, storage_key: str) -> None:
        """Atomically make an already-written version the reader-visible one."""

    @abstractmethod
    def read_current(self) -> dict | None:
        """Return the complete current catalogue, or None before any publish."""


class LocalCatalogueStorageProvider(CatalogueStorageProvider):
    """Filesystem provider using replace-only immutable files and pointer swaps."""

    CURRENT_POINTER = "current.json"

    def __init__(self, root: Path | None = None):
        self.root = (root or settings.local_catalogue_storage_path).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise ValueError("Invalid catalogue storage key")
        path = (self.root / Path(*key.parts)).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("Invalid catalogue storage key")
        return path

    def _atomic_write(self, destination: Path, payload: bytes) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with NamedTemporaryFile(mode="wb", dir=destination.parent, prefix=".catalogue-", suffix=".tmp", delete=False) as temp_file:
                temp_file.write(payload)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)
            os.replace(temp_path, destination)
        except OSError:
            if temp_path:
                try:
                    temp_path.unlink()
                except FileNotFoundError:
                    pass
            raise

    def write_version(self, version: str, payload: bytes) -> str:
        storage_key = f"catalogue_{version}.json"
        destination = self._path_for(storage_key)
        if destination.exists():
            # Content-addressed versions are immutable. Reusing one makes a
            # repeat publish of identical data idempotent.
            if destination.read_bytes() != payload:
                raise ValueError("Catalogue version already exists with different content")
            return storage_key
        self._atomic_write(destination, payload)
        return storage_key

    def switch_current(self, version: str, storage_key: str) -> None:
        if not self._path_for(storage_key).is_file():
            raise ValueError("Cannot point to a catalogue version that does not exist")
        pointer = json.dumps({"version": version, "storage_key": storage_key}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self._atomic_write(self._path_for(self.CURRENT_POINTER), pointer)

    def read_current(self) -> dict | None:
        pointer_path = self._path_for(self.CURRENT_POINTER)
        if not pointer_path.is_file():
            return None
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        catalogue_path = self._path_for(pointer["storage_key"])
        return json.loads(catalogue_path.read_text(encoding="utf-8"))
