.DEFAULT_GOAL := help

.PHONY: help setup gen-key up down dev logs status clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ── Setup ─────────────────────────────────────────────────────────────────────

setup: ## Copy .env.example → .env (if absent) and install Python deps
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env — open it and fill in GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"; \
	else \
		echo ".env already exists, skipping copy"; \
	fi
	uv sync
	@echo "Dependencies installed"

gen-key: ## Generate a stable Fernet encryption key and write it to .env
	@[ -f .env ] || (echo "Run 'make setup' first"; exit 1)
	@KEY=$$(uv run python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"); \
	if grep -q "^STORAGE_ENCRYPTION_KEY=" .env; then \
		sed -i "s|^STORAGE_ENCRYPTION_KEY=.*|STORAGE_ENCRYPTION_KEY=$$KEY|" .env; \
	else \
		echo "STORAGE_ENCRYPTION_KEY=$$KEY" >> .env; \
	fi; \
	echo "Encryption key written to .env (tokens will survive restarts)"

# ── Infrastructure ────────────────────────────────────────────────────────────

up: ## Start Keycloak + Redis; wait until Keycloak has imported the realm
	docker compose up -d
	@printf "Waiting for Keycloak to be ready"
	@until docker compose exec -T keycloak \
		curl -sf http://localhost:8080/realms/mcp-quickstart > /dev/null 2>&1; do \
		printf "."; sleep 2; \
	done
	@echo ""
	@echo "Keycloak ready  →  http://localhost:8889  (admin / admin)"
	@echo "Redis ready     →  localhost:6379"

down: ## Stop and remove containers (data is preserved)
	docker compose down

# ── Development ───────────────────────────────────────────────────────────────

dev: ## Run the FastMCP server with hot-reload on port 8005
	uv run uvicorn server:app --reload --port 8005

# ── Utilities ─────────────────────────────────────────────────────────────────

logs: ## Tail docker container logs
	docker compose logs -f

status: ## Print Keycloak + Redis health
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
