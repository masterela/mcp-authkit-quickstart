"""Auth wiring — OAuthProvider + JwtAuthMiddleware.

Call register(app) once from main.py to attach everything to the FastAPI instance.
"""
from __future__ import annotations

import os
import ssl

from fastapi import FastAPI
from mcpauthkit import OAuthProvider
from mcpauthkit.auth_middleware import JwtAuthMiddleware
from mcpauthkit.auth_routes import oauth_meta_router

from config import settings
from app.shared import current_user


def _make_ssl_context() -> ssl.SSLContext:
    """Build an SSL context honouring REQUESTS_CA_BUNDLE / SSL_CERT_FILE."""
    ca_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    ctx = ssl.create_default_context(cafile=ca_bundle or None)
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT  # type: ignore[attr-defined]
    return ctx


_SSL_CTX = _make_ssl_context()

github = OAuthProvider.from_standard_oauth2(
    name="github",
    authorization_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    client_id=settings.github_oauth_app_client_id,
    client_secret=settings.github_oauth_app_client_secret,
    scope="read:user repo",
    redirect_uri=f"{settings.server_base_url}/github/callback",
    user_context=current_user,
    http_verify=_SSL_CTX,
)


def register(app: FastAPI) -> None:
    """Register auth routes and middleware onto *app*."""
    github.register(app)
    app.include_router(
        oauth_meta_router(
            server_base_url=settings.server_base_url,
            issuer_url=settings.keycloak_url,
            client_id=settings.mcp_client_id,
        )
    )
    app.add_middleware(
        JwtAuthMiddleware,
        issuer_url=settings.keycloak_url,
        current_user=current_user,
        server_base_url=settings.server_base_url,
        open_paths=(
            "/.well-known",
            "/health",
            "/register",
            github.callback_path,
        ),
    )
