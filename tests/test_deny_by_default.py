import pytest
from fastapi import Depends, APIRouter
from app.main import app
from app.core.auth_registry import PUBLIC_ALLOWLIST, REFRESH_COOKIE_AUTHENTICATED, is_auth_provider

def has_auth_dependency(dependant, seen=None) -> bool:
    """Recursively search the dependency tree for an approved auth provider."""
    if seen is None:
        seen = set()
    if not dependant or id(dependant) in seen:
        return False
    seen.add(id(dependant))
    
    if not hasattr(dependant, "dependencies") or not dependant.dependencies:
        return False
    
    for dep in dependant.dependencies:
        if is_auth_provider(dep.call):
            return True
        # Recursively check nested dependencies
        if has_auth_dependency(dep, seen):
            return True
            
    return False

def test_all_routes_have_auth_dependency():
    from fastapi.routing import APIRoute
    missing_auth = []
    
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
            
        path = route.path
        
        # OpenAPI docs and special public endpoints
        if path in PUBLIC_ALLOWLIST or path in REFRESH_COOKIE_AUTHENTICATED:
            continue
            
        if not has_auth_dependency(route.dependant):
            missing_auth.append(f"{route.methods} {path} - {route.name}")
            
    assert not missing_auth, f"The following routes are missing an explicit auth dependency: {missing_auth}"

def test_refresh_cookie_authenticated_routes_actually_verify():
    import inspect
    from fastapi.routing import APIRoute
    from app.services import auth_service
    
    # Map the expected path to the actual service function that performs the work
    SERVICE_MAPPING = {
        "/api/v1/auth/refresh": auth_service.refresh_access_token,
        "/api/v1/auth/logout": auth_service.logout,
    }
    
    verified_paths = set()
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path in REFRESH_COOKIE_AUTHENTICATED:
            assert route.path in SERVICE_MAPPING, f"No service function mapped for {route.path}"
            service_func = SERVICE_MAPPING[route.path]
            source = inspect.getsource(service_func)
            
            # The service function MUST actually cryptographically verify the token
            assert "verify_refresh_token" in source, \
                f"Service function {service_func.__name__} for route {route.path} claims to be REFRESH_COOKIE_AUTHENTICATED but does not call verify_refresh_token!"
            verified_paths.add(route.path)
            
    assert verified_paths == REFRESH_COOKIE_AUTHENTICATED, "Some paths in REFRESH_COOKIE_AUTHENTICATED were not found in app.routes!"

def test_recursive_auth_dependency_resolution():
    from app.core.rbac import require_role
    
    def nested_dep1(user = Depends(require_role("ADMIN"))):
        return user
        
    def nested_dep2(user = Depends(nested_dep1)):
        return user
        
    def deeply_nested_dep(user = Depends(nested_dep2)):
        return user
        
    test_router = APIRouter()
    
    @test_router.get("/test-nested")
    def test_endpoint(user = Depends(deeply_nested_dep)):
        return "ok"
        
    # Manually check the generated route
    route = test_router.routes[0]
    
    assert has_auth_dependency(route.dependant), "Recursive dependency walker failed to find nested require_role"
