"""Shared singletons — imported by auth.py and tools/*.

No imports from other project modules here to avoid circular dependencies.
"""
from __future__ import annotations

from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("quickstart")

# Populated by JwtAuthMiddleware on every authenticated request.
# OAuthProvider reads `sub` from it to key per-user token storage.
current_user: ContextVar[dict | None] = ContextVar("current_user", default=None)
