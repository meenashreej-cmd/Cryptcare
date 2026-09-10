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

from app.core.security import TokenError, verify_access_token

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
    return CurrentUser(
        id=payload["sub"],
        role=payload["role"],
        permissions=payload.get("permissions", []),
    )


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
