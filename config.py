from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Primary OIDC (Keycloak) ───────────────────────────────────────────────
    keycloak_url: str = "http://localhost:8889/realms/mcp-quickstart"
    server_base_url: str = "http://localhost:8005"
    mcp_client_id: str = "mcp-quickstart-vscode"

    # ── GitHub OAuth App ─────────────────────────────────────────────────────
    github_client_id: str
    github_client_secret: str

    # ── Storage ───────────────────────────────────────────────────────────────
    token_storage_mode: str = "redis"
    redis_url: str = "redis://localhost:6379"
    storage_encryption_key: str = ""   # auto-generated if empty (ephemeral)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
