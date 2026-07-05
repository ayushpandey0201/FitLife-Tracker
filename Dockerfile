# syntax=docker/dockerfile:1

# --- build stage ------------------------------------------------------------
# Resolve and install dependencies into a self-contained virtualenv with uv,
# using the frozen lockfile for reproducible builds. Splitting the dependency
# install (no project) from the project install keeps the big dependency layer
# cached across source-only changes.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- runtime stage ----------------------------------------------------------
# A slim, non-root image carrying only the built venv and the application code
# (plus migrations and the food/exercise data needed at runtime).
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder --chown=app:app /app /app

USER app
EXPOSE 8000

# Serve the ASGI app. Run migrations separately (see README / compose) — a
# container should not assume it owns the schema.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
