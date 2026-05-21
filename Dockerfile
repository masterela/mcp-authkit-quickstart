FROM python:3.11-slim

WORKDIR /app

# ── Install uv ────────────────────────────────────────────────────────────────
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ── Trust host CA bundle (handles corporate TLS-inspecting proxies) ───────────
# `make up` copies /etc/ssl/certs/ca-certificates.crt to .build-ca-bundle.crt
# before the build starts. Empty file = no-op (standard environments).
COPY .build-ca-bundle.crt /tmp/host-ca.crt
RUN if [ -s /tmp/host-ca.crt ]; then \
      cp /tmp/host-ca.crt /usr/local/share/ca-certificates/host-bundle.crt \
      && update-ca-certificates; \
    fi && rm /tmp/host-ca.crt

# ── Install deps (cached layer — only re-runs when pyproject.toml or uv.lock changes) ──
COPY pyproject.toml uv.lock ./
RUN uv --native-tls sync --frozen --no-dev --no-install-project

# ── Copy application source ───────────────────────────────────────────────────
COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8005

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
