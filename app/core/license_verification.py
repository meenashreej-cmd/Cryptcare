"""
License Verification — Phase 1 automatic professional credential check.

Replaces the previous admin-manual verification step. When a professional
registers, their submitted license_number is looked up in the in-process
LICENSE_REGISTRY dataset. If it matches, the profile is immediately marked
verified=True and the account is fully activated after OTP confirmation.

If the license is NOT found, registration is rejected with HTTP 422 so the
user gets a clear, actionable error before any DB rows are written.

Upgrade path (Phase N):
    Replace `_lookup_in_registry()` with an async call to the national
    medical council / pharmacy board API. The public interface
    (verify_license_or_raise / is_license_valid) stays the same.
"""

import logging

from fastapi import HTTPException, status

from app.data.license_registry import LICENSE_REGISTRY, LICENSED_ROLES
from app.models.user import RoleEnum

logger = logging.getLogger(__name__)


def _normalize(license_number: str) -> str:
    """Strip surrounding whitespace and upper-case for case-insensitive matching."""
    return license_number.strip().upper()


def _lookup_in_registry(role: RoleEnum, license_number: str) -> bool:
    """Return True if *license_number* exists in the registry for *role*.

    O(1) set lookup — safe to call in a hot registration path.
    """
    role_registry = LICENSE_REGISTRY.get(role)
    if role_registry is None:
        # Role has no registry entry — treat as unverifiable (not an error).
        return False
    return _normalize(license_number) in role_registry


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def is_license_valid(role: RoleEnum, license_number: str) -> bool:
    """Non-raising check. Returns True/False without side effects.

    Use this when you need to branch on validity without stopping execution.
    """
    if role not in LICENSED_ROLES:
        # Non-professional roles (PATIENT, ADMIN) don't have licenses.
        return False
    return _lookup_in_registry(role, license_number)


def verify_license_or_raise(role: RoleEnum, license_number: str) -> None:
    """Validate *license_number* for *role* and raise HTTP 422 if invalid.

    Call this early in register_user(), before any DB writes, so an
    unrecognised license is rejected cleanly with a helpful message.

    Raises:
        HTTPException(422): license not found in the registry for this role.
    """
    if role not in LICENSED_ROLES:
        # PATIENT / ADMIN — no license needed, nothing to verify.
        return

    if not _lookup_in_registry(role, license_number):
        logger.warning(
            "License verification failed: role=%s license=%s",
            role.value,
            license_number,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"License number '{license_number}' is not recognised in the "
                f"{role.value.lower()} licensing registry. "
                "Please check your license number and try again, or contact "
                "your licensing authority if you believe this is an error."
            ),
        )

    logger.info(
        "License verified automatically: role=%s license=%s",
        role.value,
        license_number,
    )
