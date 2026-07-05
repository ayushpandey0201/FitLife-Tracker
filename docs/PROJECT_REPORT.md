# FitLife Tracker — Project Report (Phases 0–6)

> A complete overview of the project: its objective, the phase-by-phase build,
> the technology used, how to run it, and the future agenda. Metrics reflect the
> state at the end of Phase 6 (109 tests passing, 21 endpoints, 8 tables,
> 3 migrations, ~3,900 lines of application code).

---

## 1. Objective — what is being built and why

FitLife Tracker started as a single **~400-line Python script**: a fitness/nutrition
calculator riddled with correctness bugs and non-determinism. It used
`random.choice` / `random.randint` to pick meals (so advice changed every run),
computed BMR from *target* weight instead of current, double-counted the calorie
deficit, and crashed on edge inputs (`ZeroDivisionError` on zero weeks,
`UnboundLocalError` on any sex other than two hard-coded letters).

The project's objective is to **migrate that script into a production-quality,
layered backend** that can power web/mobile clients — an **evidence-based fitness
& nutrition engine**. Given a user's body metrics and a weight goal, it computes:

> **BMR → TDEE → a safe calorie target → macro & hydration targets → a
> deterministic, calorie-matched meal plan**

…then lets users **create accounts, persist profiles, track what they actually
do** (weight, water, food, exercise), **see progress**, and receive
**personalised recommendations** — with a deliberate seam for plugging in AI later.

### Guiding principles

- **Clean / Hexagonal Architecture** — a pure `domain` layer with zero framework
  or I/O dependencies, reached only through repository **ports** (Protocols)
  whose adapters live at the edges.
- **Determinism** — same input always yields the same advice (critical for a
  health app and for testing).
- **Correctness first** — every original bug fixed and locked behind a
  regression test.
- **Typed & tested** — strict `mypy`, comprehensive `pytest`, `ruff` lint +
  format enforced in CI.

---

## 2. Phase-by-phase breakdown

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | uv scaffold, tooling, project structure | ✅ done |
| 1 | Deterministic domain engine + data extraction + CLI | ✅ done |
| 2 | Config (pydantic-settings) + structured logging | ✅ done |
| 3 | Persistence: SQLAlchemy + Alembic + PostgreSQL | ✅ done |
| 4 | FastAPI app + JWT auth + profile/plan endpoints | ✅ done |
| 5 | Tracking & analytics: logs + progress | ✅ done |
| 6 | Docker, CI, docs + recommendation seam for AI | ✅ done |

### Phase 0 — Scaffold & tooling

Set up the `uv`-managed project: `pyproject.toml`, a layered package skeleton,
and the quality toolchain — `ruff` (lint + format), `mypy` (strict), `pytest`.
Established the discipline that every later phase plugs into.

### Phase 1 — Deterministic domain engine

The heart of the app, kept **pure** (no I/O, fully typed):

- **Value objects** (`domain/models.py`): `UserProfile` (validated — rejects
  age 0, zero weeks, unknown sex), `NutritionPlan`, `BodyMetrics` (BMI + WHO
  category), `MacroTargets`.
- **Enums** (`domain/enums.py`): `Sex`, `ActivityLevel` (with proper TDEE
  multipliers, replacing a hard-coded `×1.5`), `Goal`, `DietPreference`,
  `MealType`.
- **Engine** (`domain/nutrition.py`): Mifflin-St Jeor BMR → activity-scaled
  TDEE → safe calorie target (deficit applied once, floored to a safe minimum)
  → macros + hydration.
- **Meal planner** (`domain/meals.py`): deterministically picks the eligible
  food best matching the target macro ratio and scales the portion to hit the
  calorie share.
- **Data extraction**: inline food/exercise data pulled out into
  `data/foods.json` and `data/exercises.json`, loaded via `catalog.py`.
- **CLI** (`cli.py`): a thin adapter — the CLI no longer executes on import.

### Phase 2 — Config & logging

- **`config.py`**: a single typed `Settings` object (pydantic-settings) — the
  one place the app reads its environment (from args → env vars → `.env`).
  Refuses to boot in `production` with the default JWT secret.
- **`logging_config.py`**: centralised, idempotent structured logging, wired
  into the CLI.

### Phase 3 — Persistence

- **`db/`**: SQLAlchemy `DeclarativeBase` with an explicit naming convention
  (stable, portable migrations), engine/sessionmaker from `Settings`, ORM models.
- **Repository seam**: `domain/repositories.py` defines **ports** (Protocols);
  `repositories/` holds the SQLAlchemy **adapters** with row↔domain mapping. The
  domain never imports the database.
- **Alembic** migrations + **`docker-compose.yml`** with Postgres 16.
  Persistence is **opt-in** — with no `DATABASE_URL`, the CLI still runs
  statelessly.

### Phase 4 — FastAPI app + JWT auth

- **`security/`**: Argon2 password hashing + JWT create/decode.
- **Auth**: register, login, **refresh-token rotation** (refresh tokens stored
  *hashed* and revocable → real logout), `/auth/me`.
- **Persistence**: `users`, `plans`, `refresh_tokens` tables; profiles linked to
  users.
- **API layer** (`api/`): thin routers → application **services** (`services/`)
  → domain. Service exceptions mapped to HTTP status codes centrally
  (`api/errors.py`); the domain/services layers never import HTTP types.
  Non-owned resources return **404, not 403** (existence isn't leaked).

### Phase 5 — Tracking & analytics

- **Domain** (`domain/tracking.py`): pure log value objects + deterministic
  analytics — `calories_burned` (MET formula), `summarise_day`,
  `build_weight_trend`.
- **4 log tables** (`weight/water/food/exercise_logs`) sharing an abstract
  `TrackingLog` base with a composite `(user_id, logged_at)` index.
- **Service**: exercise calories derived server-side from catalogue MET × the
  user's current-profile weight, then **stored** (history stays stable if
  weight/catalogue later change). `logged_at` defaults to now but can back-date.
- **Endpoints**: `/logs/{kind}` (record/list/delete) and
  `/progress/{daily,weight}` (UTC-bucketed summaries).

### Phase 6 — Ops + the AI seam

- **Recommendation seam** (`domain/recommendations.py`): a `Recommender`
  **port** with a pure, deterministic `RuleBasedRecommender` default
  (hydration/protein/calories/weight/activity/logging rules + a positive
  fallback so a logged day is never empty). `GET /recommendations`.
  **Swapping in AI = implement the Protocol + override one provider — zero
  changes to routers, services, domain, or the HTTP contract.**
- **Docker**: multi-stage `Dockerfile` (uv build → slim, **non-root** runtime);
  compose `api` service that waits for a healthy DB, migrates, then serves.
- **CI** (`.github/workflows/ci.yml`): a *quality* job (ruff format-check, ruff,
  strict mypy, pytest+coverage) and a *migrations* job (alembic upgrade + drift
  check against real Postgres).

---

## 3. Technology used

| Category | Tools |
|----------|-------|
| **Language** | Python 3.12 |
| **Web framework** | FastAPI + Uvicorn (ASGI) |
| **Data / validation** | Pydantic v2, pydantic-settings |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (ORM), psycopg 3 |
| **Migrations** | Alembic |
| **Auth / security** | PyJWT (access + refresh tokens), argon2-cffi (password hashing) |
| **Packaging / deps** | uv (lockfile-driven), hatchling (build backend) |
| **Quality** | ruff (lint + format), mypy (strict), pytest + pytest-cov, httpx (TestClient) |
| **Ops** | Docker (multi-stage), Docker Compose, GitHub Actions CI |

**Architecture pattern:** Clean / Hexagonal — `domain` (pure) ← `services` (use
cases) ← `api` (HTTP adapter) / `cli`; persistence behind repository ports.

---

## 4. The codebase at a glance

- **~3,900 lines** of application code across **57 modules**; **~1,530 lines**
  of tests across **14 files**; **109 tests passing**.
- **8 tables:** `users`, `user_profiles`, `plans`, `refresh_tokens`,
  `weight_logs`, `water_logs`, `food_logs`, `exercise_logs` (3 Alembic
  migrations).
- **21 endpoints:** auth (5), profiles (3), plans (3), logs (4 kinds ×
  record/list/delete), progress (2), recommendations (1), health (1).

```
app/
├── domain/        # Pure business logic (models, enums, nutrition, meals,
│                  # tracking, recommendations, exceptions, repository ports)
├── db/            # SQLAlchemy base, engine, ORM models
├── repositories/  # SQLAlchemy adapters (row↔domain)
├── security/      # Argon2 + JWT
├── services/      # Application use cases (auth, profile, plan, tracking, recommendation)
├── schemas/       # HTTP DTOs
├── api/           # FastAPI app factory, routers, DI, error mapping
├── config.py · logging_config.py · catalog.py · cli.py · main.py
data/ · migrations/ · tests/ · Dockerfile · docker-compose.yml · .github/
```

### Full endpoint surface

| Method & path | Auth | Purpose |
|---------------|------|---------|
| `POST /auth/register` | – | Create an account |
| `POST /auth/login` | – | Exchange credentials for an access/refresh pair |
| `POST /auth/refresh` | – | Rotate a refresh token (old one revoked) |
| `POST /auth/logout` | – | Revoke a refresh token (idempotent) |
| `GET  /auth/me` | Bearer | Current authenticated user |
| `POST /profiles` | Bearer | Create a new profile version |
| `GET  /profiles/current` | Bearer | Current (latest) profile |
| `GET  /profiles` | Bearer | Profile history (newest first) |
| `POST /plans` | Bearer | Generate a plan from the current profile |
| `GET  /plans` | Bearer | Plan history (summaries) |
| `GET  /plans/{id}` | Bearer | Fetch one plan in full |
| `POST /logs/{kind}` | Bearer | Record a log — weight/water/food/exercise |
| `GET  /logs/{kind}` | Bearer | Log history for a kind |
| `DELETE /logs/{kind}/{id}` | Bearer | Delete one log entry |
| `GET  /progress/daily` | Bearer | Daily summary (calories in/out, macros, water) |
| `GET  /progress/weight` | Bearer | Weight series + net change over a range |
| `GET  /recommendations` | Bearer | Personalised guidance from profile + plan + logs |
| `GET  /health` | – | Liveness probe |

---

## 5. How to run

### Option A — CLI only (no database)

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
uv run python python_project_vs.py          # or: uv run fitlife-cli
```

### Option B — HTTP API locally (hot reload; best for development)

```bash
uv venv --python 3.12 && uv pip install -e ".[dev]"
docker compose up -d db                      # Postgres
cp .env.example .env                         # uncomment DATABASE_URL
uv run alembic upgrade head                  # migrate
uv run uvicorn app.main:app --reload         # → http://127.0.0.1:8000/docs
```

### Option C — Full stack in Docker (one command)

```bash
docker compose up --build -d api             # Postgres + API, auto-migrates
# → http://localhost:8000/docs
docker compose down                          # stop (add -v to wipe data)
```

> **macOS note:** if `docker compose` reports `error getting credentials`, the
> Homebrew `docker` CLI can't find Docker Desktop's credential helper. Prefix the
> command with `PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"`.

The interactive Swagger UI at **`/docs`** walks the full flow: register → log in
→ create a profile → generate a plan → log tracking data → view progress → get
recommendations.

---

## 6. Future agenda

**The headline next step — the reason Phase 6's seam exists:**

- **AI recommender.** Implement the `Recommender` Protocol with an LLM given the
  same pure `RecommendationContext`, and override `provide_recommendation_service`.
  No changes to routers, services, domain, or the API contract. Natural
  extensions: natural-language coaching, adaptive plan adjustments from logged
  trends, meal suggestions grounded in the food catalogue.

**Broader roadmap (candidates, roughly by value):**

- **Finish CI/CD:** get the pipeline green on GitHub, then add a **CD** step
  (build + publish the image to a registry, deploy to a host).
- **Deployment:** a production target (Fly.io / Render / a container host),
  secrets management, and a strong `JWT_SECRET_KEY`.
- **Product depth:** goal progress against ETA, streaks / adherence scoring,
  exercise-catalogue expansion, richer analytics (weekly rollups, macro
  adherence over time), pagination + date filters on log listings.
- **Hardening:** rate limiting on auth, refresh-token cleanup job, email
  verification / password reset, an `admin` role (the RBAC seam is already
  wired).
- **Observability:** request-logging middleware, metrics, structured error
  responses.
- **Client:** a web or mobile front-end consuming the API (the whole backend was
  designed to power one).
