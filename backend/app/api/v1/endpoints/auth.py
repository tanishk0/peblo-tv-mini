from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="User login")
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email and password, returning a signed JWT access token."""
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile information for the authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/admin-check", summary="Admin authorization check")
def admin_check(
    admin_user: User = Depends(require_admin),
) -> dict:
    """Probe endpoint restricted exclusively to users with admin role."""
    return {
        "status": "ok",
        "message": "Admin authorization confirmed",
        "email": admin_user.email,
        "role": admin_user.role.value,
    }
