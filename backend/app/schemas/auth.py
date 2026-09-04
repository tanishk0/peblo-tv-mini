from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    """Payload for user credentials login."""
    email: str
    password: str


class UserResponse(BaseModel):
    """Public user profile representation."""
    id: int
    email: str
    role: UserRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT access token response model."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
