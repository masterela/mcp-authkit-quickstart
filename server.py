"""
mcp-authkit-quickstart — example FastMCP server.

Tools:
  list_repos   — list the authenticated user's GitHub repositories
  get_repo     — fetch metadata for a specific repo
  list_prs     — list open (or closed) pull requests for a repo
  list_issues  — list open issues for a repo

Primary auth:  Keycloak OIDC JWT (leg 1)
Secondary auth: GitHub OAuth 2.0 via mcp-authkit OAuthProvider (leg 2)
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any

import httpx
from fastapi import FastAPI
from mcp.server.fastmcp import Context, FastMCP

from mcpauthkit import OAuthProvider
from mcpauthkit.auth_middleware import JwtAuthMiddleware
from mcpauthkit.auth_routes import oauth_meta_router

from config import settings

logging.basicConfig(level=logging.INFO)
logging.getLogger("sse_starlette.sse").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── Shared state ──────────────────────────────────────────────────────────────

# Populated by JwtAuthMiddleware on every authenticated request.
current_user: ContextVar[dict | None] = ContextVar("current_user", default=None)

app = FastAPI(title="mcp-authkit quickstart")
mcp = FastMCP("quickstart")

# ── GitHub OAuth provider ─────────────────────────────────────────────────────

github = OAuthProvider.from_standard_oauth2(
    name="github",
    authorization_url="https://github.com/login/oauth/authorize",
    token_url="https://github.com/login/oauth/access_token",
    client_id=settings.github_client_id,
    client_secret=settings.github_client_secret,
    scope="read:user repo",
    redirect_uri=f"{settings.server_base_url}/github/callback",
    user_context=current_user,
)
github.register(app)  # registers GET /github/callback

# ── Primary auth (Keycloak JWT) ───────────────────────────────────────────────

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

# ── MCP tools ─────────────────────────────────────────────────────────────────

_GH_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _auth(token: str) -> dict:
    return {**_GH_HEADERS, "Authorization": f"Bearer {token}"}


@mcp.tool(description="List your GitHub repositories, sorted by most recently updated.")
@github.require_token()
async def list_repos(ctx: Context, per_page: int = 15) -> list[dict[str, Any]]:
    token = github.get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers=_auth(token),  # type: ignore[arg-type]
            params={"per_page": per_page, "sort": "updated"},
        )
        resp.raise_for_status()
    return [
        {
            "name": r["full_name"],
            "description": r["description"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "url": r["html_url"],
        }
        for r in resp.json()
    ]


@mcp.tool(description="Get details about a GitHub repository (owner/repo).")
@github.require_token()
async def get_repo(ctx: Context, repo: str) -> dict[str, Any]:
    token = github.get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}",
            headers=_auth(token),  # type: ignore[arg-type]
        )
        resp.raise_for_status()
        r = resp.json()
    return {
        "name": r["full_name"],
        "description": r["description"],
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "open_issues": r["open_issues_count"],
        "default_branch": r["default_branch"],
        "url": r["html_url"],
    }


@mcp.tool(description="List pull requests for a GitHub repository.")
@github.require_token()
async def list_prs(ctx: Context, repo: str, state: str = "open") -> list[dict[str, Any]]:
    """state: 'open' | 'closed' | 'all'"""
    token = github.get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}/pulls",
            headers=_auth(token),  # type: ignore[arg-type]
            params={"state": state, "per_page": 20},
        )
        resp.raise_for_status()
    return [
        {
            "number": p["number"],
            "title": p["title"],
            "author": p["user"]["login"],
            "state": p["state"],
            "url": p["html_url"],
        }
        for p in resp.json()
    ]


@mcp.tool(description="List open issues for a GitHub repository.")
@github.require_token()
async def list_issues(ctx: Context, repo: str, per_page: int = 20) -> list[dict[str, Any]]:
    token = github.get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{repo}/issues",
            headers=_auth(token),  # type: ignore[arg-type]
            params={"state": "open", "per_page": per_page},
        )
        resp.raise_for_status()
    return [
        {
            "number": i["number"],
            "title": i["title"],
            "author": i["user"]["login"],
            "labels": [lb["name"] for lb in i["labels"]],
            "url": i["html_url"],
        }
        for i in resp.json()
        if "pull_request" not in i  # issues endpoint also returns PRs
    ]


# ── Utility ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ── MCP mount — must come last ────────────────────────────────────────────────

app.mount("/", app=mcp.streamable_http_app())
