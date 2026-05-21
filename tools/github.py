"""GitHub MCP tools — list_repos, get_repo, list_prs, list_issues."""
from __future__ import annotations

from typing import Any

import httpx
from mcp.server.fastmcp import Context

from auth import _SSL_CTX, github
from app.shared import mcp

_GH_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def _auth(token: str) -> dict:
    return {**_GH_HEADERS, "Authorization": f"Bearer {token}"}


def _gh_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=_SSL_CTX, follow_redirects=True, timeout=15)


@mcp.tool(description="List your GitHub repositories, sorted by most recently updated.")
@github.require_token()
async def list_repos(ctx: Context, per_page: int = 15) -> list[dict[str, Any]]:
    token = github.get_token()
    async with _gh_client() as client:
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
    async with _gh_client() as client:
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
    async with _gh_client() as client:
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
    async with _gh_client() as client:
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
