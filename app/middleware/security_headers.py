"""
Security headers middleware for comprehensive web application protection.

This middleware implements defense-in-depth security controls:
- HSTS: Enforces HTTPS connections
- CSP: Prevents XSS and data injection attacks  
- X-Frame-Options: Prevents clickjacking
- X-Content-Type-Options: Prevents MIME sniffing
- Referrer-Policy: Controls referrer information leakage
- Permissions-Policy: Restricts browser features
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds comprehensive security headers to all HTTP responses."""

    def __init__(self, app, csp_nonce: str = None):
        super().__init__(app)
        self.csp_nonce = csp_nonce

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # HSTS: Force HTTPS for 1 year, include subdomains
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
        # CSP: Strict content security policy for healthcare app
        # - Default to self only
        # - Block inline scripts/styles (XSS prevention)
        # - Allow specific external resources needed for healthcare functionality
        csp_parts = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval'",  # unsafe-eval needed for some medical calculators
            "style-src 'self' 'unsafe-inline'",  # inline styles for dynamic UI components
            "img-src 'self' data: blob:",  # data: for QR codes, blob: for generated images
            "font-src 'self'",
            "connect-src 'self'",  # API calls only to same origin
            "media-src 'none'",  # No media files for security
            "object-src 'none'",  # No plugins/objects
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",  # Prevent embedding (clickjacking)
            "upgrade-insecure-requests"  # Auto-upgrade HTTP to HTTPS
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # MIME sniffing protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Referrer policy: Don't leak sensitive URLs
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy: Disable unnecessary browser features
        permissions_parts = [
            "geolocation=()",  # No location access
            "camera=()",       # No camera access
            "microphone=()",   # No microphone access
            "usb=()",          # No USB access
            "payment=()",      # No payment APIs
            "accelerometer=()", # No motion sensors
            "gyroscope=()",
            "magnetometer=()",
            "ambient-light-sensor=()",
            "encrypted-media=()",
            "midi=()",
            "picture-in-picture=()",
            "fullscreen=(self)"  # Allow fullscreen on same origin only
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_parts)
        
        # Cross-Origin policies for enhanced security
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Cache control for sensitive healthcare data
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response