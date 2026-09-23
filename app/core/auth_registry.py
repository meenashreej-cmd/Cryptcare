from app.core.rbac import get_current_user

# Canonical set of valid auth dependency functions (by reference)
ALLOWED_AUTH_DEPENDENCIES = {
    get_current_user,
}

# Canonical set of valid auth dependency closures (by exact __qualname__)
# Factory functions return closures, so we must match their specific qualname.
ALLOWED_AUTH_QUALNAMES = {
    "require_role.<locals>._dependency",
    "get_preauth_user_for.<locals>._dependency",
}

# Routes that are legitimately public by design (unauthenticated)
PUBLIC_ALLOWLIST = {
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/emergency/access/{token}",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Routes where the authentication credential is provided via a verified refresh token cookie.
# Explicitly exempted from get_current_user because they securely verify the token themselves.
REFRESH_COOKIE_AUTHENTICATED = {
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
}

def is_auth_provider(dependency: callable) -> bool:
    """Strictly checks if a dependency function is a recognized authentication provider."""
    if dependency in ALLOWED_AUTH_DEPENDENCIES:
        return True
    
    qualname = getattr(dependency, "__qualname__", "")
    if qualname in ALLOWED_AUTH_QUALNAMES:
        return True
        
    return False
