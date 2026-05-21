.DEFAULT_GOAL := help

.PHONY: help setup gen-key up stop down dev logs follow status clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Copy .env.example → .env (if absent) and install Python deps
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env — open it and fill in GITHUB_OAUTH_APP_CLIENT_ID and GITHUB_OAUTH_APP_CLIENT_SECRET"; \
	else \
		echo ".env already exists, skipping copy"; \
	fi
	uv sync
	@echo "Dependencies installed"

gen-key: ## Generate a stable Fernet encryption key and write it to .env
	@[ -f .env ] || (echo "Run 'make setup' first"; exit 1)
	@uv run python3 -c "\
import re; \
from cryptography.fernet import Fernet; \
key = Fernet.generate_key().decode(); \
text = open('.env').read(); \
pat = r'^STORAGE_ENCRYPTION_KEY=.*'; \
replacement = 'STORAGE_ENCRYPTION_KEY=' + key; \
text = re.sub(pat, replacement, text, flags=re.M) if re.search(pat, text, re.M) else text + '\\nSTORAGE_ENCRYPTION_KEY=' + key; \
open('.env', 'w').write(text); \
print('Encryption key written to .env (tokens will survive restarts)')"

# ── Infrastructure ────────────────────────────────────────────────────────────

up: ## Build + start all services; wait until the MCP server is ready
	@# Copy host CA bundle so Docker can reach PyPI through corporate TLS proxies.
	@# Tries Linux path, then macOS path; creates empty file on Windows/other (no-op).
	@cp /etc/ssl/certs/ca-certificates.crt .build-ca-bundle.crt 2>/dev/null || \
	 cp /etc/ssl/cert.pem .build-ca-bundle.crt 2>/dev/null || \
	 touch .build-ca-bundle.crt
	docker compose up -d --build
	@rm -f .build-ca-bundle.crt
	@printf "Waiting for Keycloak"
	@until docker compose exec -T keycloak \
		bash -c "exec 3<>/dev/tcp/127.0.0.1/8080; echo -e 'GET /health/ready HTTP/1.1\r\nHost: localhost:8080\r\nConnection: close\r\n\r\n' >&3; cat <&3 | grep -q '\"status\": \"UP\"'" \
		> /dev/null 2>&1; do \
		printf "."; sleep 2; \
	done
	@printf "\nWaiting for MCP server"
	@until curl -sf http://localhost:8005/.well-known/oauth-authorization-server > /dev/null 2>&1; do \
		printf "."; sleep 2; \
	done
	@echo ""
	@echo "All services ready:"
	@echo "  MCP server  →  http://localhost:8005/mcp"
	@echo "  Keycloak    →  http://localhost:8889  (admin / admin)"
	@echo "  Redis       →  localhost:6379"

stop: ## Stop all containers without removing them (resume with: make up)
	docker compose stop

down: ## Stop and remove containers (data is preserved)
	docker compose down

# ── Development (local, hot-reload) ──────────────────────────────────────────

dev: ## Run the server locally with hot-reload (requires make up for infra)
	uv run uvicorn main:app --reload --port 8005

# ── Logging ───────────────────────────────────────────────────────────────────

logs: ## Show recent logs. Filter with: make logs SERVICE=server
	docker compose logs --tail=200 $(SERVICE)

follow: ## Follow logs in real time. Filter with: make follow SERVICE=server
	docker compose logs -f $(SERVICE)

# ── Utilities ─────────────────────────────────────────────────────────────────

status: ## Print health of all services
	@echo "=== MCP server ==="
	@curl -sf http://localhost:8005/.well-known/oauth-authorization-server > /dev/null \
		&& echo "READY  →  http://localhost:8005/mcp" \
		|| echo "NOT READY (run: make up)"
	@echo "=== Keycloak ==="
	@curl -sf http://localhost:8889/realms/mcp-quickstart \
		| python3 -c "import sys,json; d=json.load(sys.stdin); print('realm:', d['realm'], '| users can log in')" \
		|| echo "NOT READY (run: make up)"
	@echo "=== Redis ==="
	@docker compose exec -T redis redis-cli ping 2>/dev/null || echo "NOT READY (run: make up)"

clean: ## Stop containers, delete volumes and .env (full reset)
	docker compose down -v
	rm -f .env
	@echo "Cleaned up — run 'make setup' to start fresh"
