# mcp-authkit-quickstart

A complete working example of [mcp-authkit](https://github.com/masterela/mcp-authkit) showing:

- **Leg 1** — Keycloak OIDC JWT validation on every MCP session
- **Leg 2** — GitHub OAuth 2.0 token collection via MCP elicitation

Tools exposed: `list_repos`, `get_repo`, `list_prs`, `list_issues`.

---

## Prerequisites

- Docker + Docker Compose
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- A GitHub account

---

## 1 — Create a GitHub OAuth App

1. Go to **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**
2. Fill in:
   - **Application name**: `mcp-authkit-quickstart` (or anything)
   - **Homepage URL**: `http://localhost:8005`
   - **Authorization callback URL**: `http://localhost:8005/github/callback`
3. Click **Register application**, then **Generate a new client secret**
4. Copy the **Client ID** and **Client secret** — you'll need them in step 3

---

## 2 — Start Keycloak and Redis

```bash
docker compose up -d
```

Wait ~20 seconds for Keycloak to import the realm. Check it's ready:

```bash
curl -s http://localhost:8889/realms/mcp-quickstart | python3 -m json.tool | grep realm
# → "realm": "mcp-quickstart"
```

Admin console: http://localhost:8889 → `admin` / `admin`

---

## 3 — Configure the server

```bash
cp .env.example .env
```

Edit `.env` and set your GitHub credentials:

```
GITHUB_CLIENT_ID=<your client id>
GITHUB_CLIENT_SECRET=<your client secret>
```

---

## 4 — Install dependencies and run

```bash
# Install mcp-authkit from PyPI
uv sync

# Or install from source if developing mcp-authkit itself:
# uv add --editable ../auth-lib

uv run uvicorn server:app --reload --port 8005
```

---

## 5 — Connect VS Code Copilot

1. Open VS Code → **GitHub Copilot** extension → **MCP servers** → **Add server**
2. Enter `http://localhost:8005/mcp`
3. Copilot will redirect you to Keycloak — log in as `alice` / `alice123` (or `bob` / `bob123`)
4. On the first tool call that uses GitHub, Copilot opens the GitHub login page — authorise the OAuth app

---

## 6 — Try the tools

In the Copilot chat:

```
List my GitHub repositories
```
```
Show open PRs for torvalds/linux
```
```
What issues are open in microsoft/vscode?
```

---

## Project structure

```
server.py          # FastMCP server wiring
config.py          # Pydantic settings (reads .env)
docker-compose.yml # Keycloak + Redis
keycloak-realm.json # Pre-configured realm (imported automatically)
.env.example       # Template for .env
```

---

## Customising

### Add a Confluence credentials tool

```python
from mcpauthkit import CredentialsProvider

confluence = CredentialsProvider(
    name="confluence",
    variables={
        "pat": {"label": "Personal Access Token", "type": "password"},
        "base_url": {"label": "Confluence base URL", "type": "url"},
    },
    user_context=current_user,
    server_base_url=settings.server_base_url,
)
confluence.register(app)

@mcp.tool(description="Search Confluence pages")
@confluence.require_credentials()
async def search_confluence(ctx: Context, query: str) -> list[dict]:
    creds = confluence.get_credentials()
    # use creds["pat"] and creds["base_url"]
    ...
```

### Use a different OAuth provider

`OAuthProvider.from_standard_oauth2` works with any standard provider:

```python
google = OAuthProvider.from_standard_oauth2(
    name="google",
    authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    client_id=..., client_secret=...,
    scope="openid email profile",
    redirect_uri=f"{SERVER_URL}/google/callback",
    user_context=current_user,
)
```

### Switch storage backend

| `.env` setting | Backend |
|---|---|
| `TOKEN_STORAGE_MODE=memory` | In-process (default, no Redis needed) |
| `TOKEN_STORAGE_MODE=file` | Fernet-encrypted JSON files |
| `TOKEN_STORAGE_MODE=redis` | Redis (requires `REDIS_URL`) |

---

## See also

- [mcp-authkit library](https://github.com/masterela/mcp-authkit)
- [mcp-authkit docs](https://masterela.github.io/mcp-authkit/)
