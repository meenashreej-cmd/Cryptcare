"""
Role-based access control dependencies for FastAPI routes.

Usage in an endpoint:

    @router.post("/vault/prescriptions")
    def create_prescription(
        payload: PrescriptionCreate,
        current_user: CurrentUser = Depends(require_role("DOCTOR")),
    ):
        ...
"""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import TokenError, verify_access_token
from app.db.session import get_db
from app.models.user import User, UserStatusEnum

# NOTE: This project uses a custom JSON login (email/password/otp_code) —
# not the OAuth2 "Resource Owner Password Credentials" grant. OAuth2PasswordBearer
# tells Swagger to implement that grant's form-urlencoded flow on the Authorize
# dialog (username/password/client_id/client_secret), which doesn't match
# POST /auth/login's actual JSON contract and causes a 422 there. HTTPBearer
# just asks Swagger for a raw bearer token (paste the access_token you got back
# from /auth/login) — that matches this API's real flow.
bearer_scheme = HTTPBearer()


@dataclass
class CurrentUser:
    id: str
    role: str
    permissions: list[str]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type, expected access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.user_id == payload["sub"]).first()
    if not user or user.status != UserStatusEnum.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Use the role directly from the DB as the single source of truth
    # rather than trusting the JWT role which might be stale or tampered.
    db_role = user.role.value
    
    return CurrentUser(
        id=user.user_id,
        role=db_role,
        permissions=payload.get("permissions", []),
    )

def get_preauth_user_for(purpose: str):
    def _dependency(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> dict:
        token = credentials.credentials
        try:
            from app.core.security import verify_preauth_token
            payload = verify_preauth_token(token, expected_purpose=purpose)
        except TokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    return _dependency

def require_role(*allowed_roles: str):
    """Returns a FastAPI dependency that enforces the caller's role is in allowed_roles."""

    def _dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform this action",
            )
        return current_user

    return _dependency
