# FitLife Tracker

An evidence-based fitness & nutrition engine. Given your body metrics and a
weight goal, it computes **BMR → TDEE → a safe calorie target → macro &
hydration targets**, then generates a **deterministic, calorie-matched meal
plan**.

Originally a single-file CLI script, it is being migrated to a production-quality,
layered backend (Clean Architecture) that will power web/mobile clients. See the
[migration plan](#migration-plan) below.

## Architecture

```
app/
├── domain/            # Pure, framework-agnostic business logic (no I/O, fully typed)
│   ├── enums.py       # Sex, ActivityLevel, Goal, DietPreference, MealType
│   ├── constants.py   # Named, sourced constants (no magic numbers)
│   ├── models.py      # Pydantic value objects: UserProfile, NutritionPlan, ...
│   ├── nutrition.py   # BMR / TDEE / calorie target / macro engine (deterministic)
│   ├── meals.py       # Deterministic meal-plan generation
│   ├── tracking.py    # Log value objects + pure analytics (MET calories, daily sum)
│   ├── exceptions.py  # Domain error hierarchy
│   └── repositories.py# Repository *ports* (Protocols) — pure, no storage import
├── db/                # Persistence infrastructure (only place importing SQLAlchemy)
│   ├── base.py        # DeclarativeBase + naming convention
│   ├── engine.py      # Engine/sessionmaker from Settings + session_scope()
│   └── models.py      # ORM models (users, profiles, plans, tokens, tracking logs)
├── repositories/      # Repository *adapters* (SQLAlchemy) + row<->domain mapping
├── security/          # Password hashing (Argon2) + JWT create/decode
├── services/          # Application services (use cases): auth, profile, plan, tracking
├── schemas/           # HTTP request/response models (Pydantic DTOs)
├── api/               # FastAPI adapter: app factory, routers, DI, error mapping
├── config.py          # Typed Settings (pydantic-settings), loaded from .env
├── logging_config.py  # Centralised, idempotent logging setup
├── catalog.py         # Loads bundled food/exercise data (infrastructure/I/O)
├── cli.py             # Thin CLI adapter over the domain
└── main.py            # ASGI entrypoint (uvicorn app.main:app)
data/                  # foods.json, exercises.json (was inline in the script)
migrations/            # Alembic environment + versioned schema migrations
tests/                 # pytest unit + CLI + repository tests
docker-compose.yml     # Local Postgres for development
python_project_vs.py   # Backwards-compatible entrypoint (thin shim over app.cli)
```

The `domain` layer imports no framework or I/O. Persistence is reached only
through repository **ports** (`app/domain/repositories.py`) whose SQLAlchemy
**adapters** live in `app/repositories/`, so the domain never depends on the
database. Later phases add an API (FastAPI + JWT) and analytics *around* it the
same way.

## Persistence & migrations

Persistence is **opt-in**: with no `DATABASE_URL` set, the CLI runs statelessly
(unchanged). To use a database:

```bash
docker compose up -d db                 # local Postgres (see docker-compose.yml)
cp .env.example .env                     # then uncomment DATABASE_URL
uv run alembic upgrade head              # apply migrations

# Author a new migration after changing ORM models:
uv run alembic revision --autogenerate -m "describe change"
```

`migrations/env.py` reads the connection URL from the application `Settings`
(the single source of truth) and targets `app.db.base.Base.metadata`.

## Getting started

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"

# Run the CLI
uv run python python_project_vs.py      # or: uv run fitlife-cli

# Run the HTTP API (requires DATABASE_URL; see Persistence & migrations)
uv run uvicorn app.main:app --reload    # docs at http://127.0.0.1:8000/docs
```

## HTTP API

A FastAPI app (`app/api/`) exposes the engine over HTTP with JWT auth. Routes are
thin adapters: each validates a request schema, calls one application service
(`app/services/`), and returns a response schema. Service errors are mapped to
status codes centrally in `app/api/errors.py`; the domain/services layers never
import HTTP types.

| Method & path            | Auth   | Purpose                                        |
|--------------------------|--------|------------------------------------------------|
| `POST /auth/register`    | –      | Create an account                              |
| `POST /auth/login`       | –      | Exchange credentials for an access/refresh pair|
| `POST /auth/refresh`     | –      | Rotate a refresh token (old one is revoked)    |
| `POST /auth/logout`      | –      | Revoke a refresh token (idempotent)            |
| `GET  /auth/me`          | Bearer | Current authenticated user                     |
| `POST /profiles`         | Bearer | Create a new profile version                   |
| `GET  /profiles/current` | Bearer | Current (latest) profile                       |
| `GET  /profiles`         | Bearer | Profile history (newest first)                 |
| `POST /plans`            | Bearer | Generate a plan from the current profile       |
| `GET  /plans`            | Bearer | Plan history (summaries, newest first)         |
| `GET  /plans/{id}`       | Bearer | Fetch one plan in full (404 if not the caller's)|
| `POST /logs/{kind}`      | Bearer | Record a log — `kind` ∈ weight/water/food/exercise |
| `GET  /logs/{kind}`      | Bearer | Log history for a kind (newest first)          |
| `DELETE /logs/{kind}/{id}`| Bearer | Delete one log entry (404 if not the caller's) |
| `GET  /progress/daily`   | Bearer | Daily summary (calories in/out, macros, water) |
| `GET  /progress/weight`  | Bearer | Weight series + net change over a date range   |

Access tokens are short-lived Bearer JWTs; refresh tokens are longer-lived,
stored **hashed**, and revocable. All profile/plan/log reads are user-scoped — a
resource that isn't the caller's returns `404`, so existence isn't leaked.

### Tracking & progress (Phase 5)

Users log what actually happened — weigh-ins, water, food (with its nutrition),
and exercise. Exercise **calories burned** are derived server-side from the
catalogue MET and the user's current-profile weight (`kcal = MET · weight · hrs`)
and stored, so history stays stable even if weight or the catalogue later change.
`logged_at` defaults to now but may be supplied to back-date an entry. Progress
views aggregate logs by **UTC** day: `/progress/daily` sums calories in vs out,
macros, and water; `/progress/weight` returns the weight series and its net
change. All the arithmetic lives in the pure `app/domain/tracking.py`.

## Development

```bash
uv run ruff format app tests     # format
uv run ruff check app tests      # lint
uv run mypy                      # type-check (strict)
uv run pytest                    # tests
```

Runtime dependencies are pinned in `requirements.txt` (generated via
`uv pip compile pyproject.toml -o requirements.txt`); dev tooling lives in the
`dev` optional-dependency group in `pyproject.toml`.

## What changed vs. the original

- **Correctness:** BMR now uses *current* weight (not target); the calorie
  deficit is applied once (not double-counted); intake is floored to a safe
  minimum; invalid input (age 0, `weeks_to_target` 0, unknown sex) is rejected
  instead of crashing.
- **Determinism:** macro targets and meal selection are now computed from the
  calorie goal — the original used `random.randint` / `random.choice`, so advice
  changed on every run.
- **Structure:** one 400-line script → a typed, tested, layered package. The CLI
  no longer executes on import.

## Migration plan

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | uv scaffold, tooling (ruff/mypy/pytest), project structure | ✅ done |
| 1 | Deterministic domain engine + data extraction + CLI adapter | ✅ done |
| 2 | Config (pydantic-settings), structured logging, error handling | ✅ done |
| 3 | Persistence: SQLAlchemy + Alembic + PostgreSQL (docker-compose) | ✅ done |
| 4 | FastAPI app + JWT auth + user profile endpoints | ✅ done |
| 5 | Tracking & analytics: nutrition/water/exercise/weight logs, progress | ✅ done |
| 6 | Dockerfile, CI, docs; recommendation seam for future AI features | planned |
