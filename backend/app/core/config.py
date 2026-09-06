from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables or .env file."""

    # Application metadata
    PROJECT_NAME: str = "Peblo TV Mini API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & JWT configuration
    SECRET_KEY: str = "peblo-tv-mini-super-secret-jwt-signing-key-change-in-production-32bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS settings
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return ["*"]

    # Database configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "peblo_tv_mini"
    DATABASE_URL: Optional[str] = None

    # Local development storage. A future object-storage provider can use the
    # same StorageProvider interface without changing CMS upload logic.
    LOCAL_ARTWORK_STORAGE_DIR: str = "storage/artwork"
    LOCAL_ARTWORK_URL_PREFIX: str = "/media/artwork"
    LOCAL_CATALOGUE_STORAGE_DIR: str = "storage/catalogues"
    SEED_ASSETS_DIR: str = str(Path(__file__).resolve().parents[3] / "assets")

    @property
    def local_artwork_storage_path(self) -> Path:
        path = Path(self.LOCAL_ARTWORK_STORAGE_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path

    @property
    def local_catalogue_storage_path(self) -> Path:
        path = Path(self.LOCAL_CATALOGUE_STORAGE_DIR)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[2] / path

    @property
    def seed_assets_path(self) -> Path:
        return Path(self.SEED_ASSETS_DIR)

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """Construct SQLAlchemy database URI dynamically or use explicit DATABASE_URL."""
        if self.DATABASE_URL:
            # Normalize legacy postgres:// to postgresql+psycopg2://
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://") and "+psycopg" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url

        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton instance of application settings."""
    return Settings()


settings = get_settings()
