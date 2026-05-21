"""mcp-authkit quickstart — server entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import tools.github  # noqa: F401 — registers tools with mcp as a side-effect
from auth import register as register_auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared import mcp

logging.basicConfig(level=logging.INFO)
logging.getLogger("sse_starlette.sse").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="mcp-authkit quickstart", lifespan=lifespan)

register_auth(app)

# CORS must be added AFTER JwtAuthMiddleware so it wraps outermost and adds
# Access-Control-Allow-Origin even on 401 responses (Starlette: last added = first executed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# MCP mount — must come last
app.mount("/", app=mcp.streamable_http_app())
