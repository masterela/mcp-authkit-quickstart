# mcp-authkit-quickstart

A complete, runnable example of [mcp-authkit](https://github.com/masterela/mcp-authkit) showing:

- **Leg 1** — Keycloak OIDC JWT validation on every MCP session
- **Leg 2** — GitHub OAuth 2.0 token collection via MCP elicitation

Tools exposed: `list_repos`, `get_repo`, `list_prs`, `list_issues`.

> For a detailed explanation of the two-leg authentication architecture, see the **[Architecture docs](https://masterela.github.io/mcp-authkit/architecture/)**.

---

## Prerequisites

- [Docker + Docker Compose](https://docs.docker.com/get-docker/)
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- A GitHub account

---

## Quick start

### Step 1 — Create a GitHub OAuth App

This is the only manual step. Everything else is automated.

1. Go to **[GitHub → Settings → Developer settings → OAuth Apps → New OAuth App](https://github.com/settings/applications/new)**
2. Fill in:

   | Field | Value |
   |---|---|
   | Application name | `mcp-authkit-quickstart` (or anything) |
   | Homepage URL | `http://localhost:8005` |
   | Authorization callback URL | `http://localhost:8005/github/callback` |

3. Click **Register application**, then **Generate a new client secret**
4. Keep the **Client ID** and **Client secret** — you'll need them in Step 2

### Step 2 — Install and configure

```bash
make setup
```

This copies `.env.example` → `.env` and installs Python dependencies.  
Open `.env` and set your **GitHub OAuth App** credentials (these are the Client ID and Secret
of the app you just registered — not your personal GitHub login):

```
GITHUB_OAUTH_APP_CLIENT_ID=<paste your client id>
GITHUB_OAUTH_APP_CLIENT_SECRET=<paste your client secret>
```

Then generate a stable encryption key so tokens survive server restarts:

```bash
make gen-key
```

### Step 3 — Start everything

```bash
make up
```

Builds the MCP server image and starts Keycloak, Redis, and the MCP server via Docker Compose.
Waits until all three are ready — no manual health checks needed.

- MCP server: **http://localhost:8005/mcp**
- Keycloak admin console: **http://localhost:8889** → `admin` / `admin`

The realm `mcp-quickstart` is pre-configured with:
- A public OIDC client `mcp-quickstart-vscode` (PKCE enabled, VS Code redirect URIs)
- Two demo users: `alice` / `alice123` and `bob` / `bob123`

### Step 4 — Connect VS Code Copilot

1. Open VS Code → **GitHub Copilot** extension → **MCP servers** → **Add server**
2. Enter `http://localhost:8005/mcp`
3. Copilot redirects you to Keycloak — log in as `alice` / `alice123` (or `bob` / `bob123`)
4. On the first GitHub tool call, Copilot opens the GitHub OAuth page — authorise the app

### Step 5 — Try the tools

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

## Available make targets

```
make setup     Copy .env.example → .env and install Python deps
make gen-key   Generate a stable Fernet encryption key into .env
make up        Build + start all services; wait until the MCP server is ready
make stop      Stop all containers without removing them
make down      Stop and remove containers (data preserved)
make logs      Show recent logs  (filter: make logs SERVICE=server)
make follow    Follow logs in real time  (filter: make follow SERVICE=server)
make status    Check health of all services
make clean     Full reset — stop containers, delete volumes and .env
make dev       Run server locally with hot-reload (requires make up for infra)
```

---

## Project structure

```
main.py              # entry point — FastAPI app, health endpoint, MCP mount
auth.py              # OAuthProvider + JwtAuthMiddleware wiring
tools/
  github.py          # list_repos, get_repo, list_prs, list_issues
app/
  shared.py          # mcp instance + current_user ContextVar
config/
  settings.py        # Pydantic settings (reads .env)
  keycloak-realm.json  # Pre-configured realm (auto-imported on first start)
Dockerfile           # Builds the MCP server container image
docker-compose.yml   # Keycloak + Redis + MCP server
Makefile             # Automation: setup, infra, logs, stop
.env.example         # Template — copy to .env and fill in secrets
```

---

## Customising

> All snippets below extend `auth.py` and `tools/`. `current_user` is the `ContextVar` declared in `shared.py` — pass the same object to every provider so they can key stored credentials per user. See the [mcp-authkit docs](https://masterela.github.io/mcp-authkit/#setup) for a full explanation.

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
    redirect_uri=f"{settings.server_base_url}/google/callback",
    user_context=current_user,
)
```

### Switch storage backend

Set `TOKEN_STORAGE_MODE` in `.env`:

| Value | Backend |
|---|---|
| `memory` | In-process — no Redis needed, tokens lost on restart |
| `file` | Fernet-encrypted JSON files on disk |
| `redis` (default) | Async Redis — use for multi-process or persistent deployments |

---

## Troubleshooting

### Corporate / TLS-inspecting proxy

If outbound HTTPS calls fail with `CERTIFICATE_VERIFY_FAILED` (common on
networks with Netskope, Zscaler, or similar proxies), add your corporate CA
bundle path to `.env`:

```
REQUESTS_CA_BUNDLE=/path/to/your/ca-bundle.pem
```

The server reads this variable at startup and uses it for all outbound HTTPS
connections (GitHub OAuth token exchange and GitHub API calls).  The
`make up` build step also injects the host's system CA store into the
container image, so PyPI package downloads work during the build.

---

## See also

- [mcp-authkit library](https://github.com/masterela/mcp-authkit)
- [mcp-authkit docs](https://masterela.github.io/mcp-authkit/)
