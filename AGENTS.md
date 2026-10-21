# AGENTS.md

Instructions for any AI coding agent working on this repository. Read this file in full before writing or modifying any code.

---

## 1. Project Overview

This project is a **Zero-Trust API Gateway with Fine-Grained, Graph-Aware Authorization**.

Unlike a conventional API gateway (which authorizes a request once, at the point of authentication), this system:

1. Uses a **ReBAC (relationship-based access control)** model — permissions are derived from a relationship graph (e.g. `user:alice` is a `member` of `team:eng`, which is a `viewer` of `doc:123`) rather than static roles.
2. Computes a **continuous, decaying trust score** per session/subject, fed by two feature streams:
   - **Behavioral features** — request rate, geo-velocity, device/TLS fingerprint changes, time-of-day deviation.
   - **Graph-structural features** — whether the relationship path used to satisfy an access check is novel/anomalous for that subject, or represents a privilege-escalation shortcut.
3. Feeds both streams into an **anomaly detection model** (Isolation Forest or LSTM-Autoencoder) that outputs a trust score.
4. Uses a **Decision Engine** that maps trust score bands to responses: `allow`, `step_up` (challenge for stronger auth), or `narrow` (write a temporary restricting relation back into the ReBAC graph — closing the loop, not just alerting).
5. Logs every decision with **feature-level attribution** (e.g. SHAP values) so denials/step-ups are explainable, not a black box.

The core novelty is the **graph-aware anomaly detection** and the **closed-loop policy feedback** — not generic "ML on API logs." Any agent working on this project should protect that distinction: don't simplify graph-feature extraction away, and don't turn the decision engine into a passive logger.

---

## 2. Tech Stack

- **Language:** Python 3.12+
- **Gateway Services:** FastAPI (Control Plane on Port 3002, Data Plane on Port 3003)
- **Frontend Dashboard:** React, TypeScript, Vite, pnpm (Port 3001)
- **ASGI server:** Uvicorn
- **Package/environment manager:** `uv` workspace monorepo (not pip/poetry/conda — see Section 3)
- **ReBAC store:** SpiceDB (v1.30+), backed by PostgreSQL via Docker Compose (Port 50051 gRPC, 8443 HTTP)
- **Configuration & Audit store:** MongoDB (running on host `localhost:27017`, accessed by Control Plane and Audit module)
- **Feature & State store:** Redis (rolling behavioral windows, Port 6379)
- **ML:** scikit-learn (Isolation Forest) as the default model; PyTorch only if/when the LSTM-Autoencoder variant is explicitly scoped in
- **Explainability:** SHAP
- **Testing:** pytest
- **Linting/formatting:** ruff (lint + format)
- **Type checking:** mypy (strict on new code)

Do not introduce a new language, framework, package manager, or major dependency (a new database, a new ML framework, a new web framework) without flagging it explicitly rather than silently adding it.

---

## 3. How to Run / Build / Test

All Python tooling goes through **`uv`**. Never call `pip install` directly, never create a `venv` manually.

```bash
# Install/sync all workspace dependencies (reads pyproject.toml + uv.lock)
uv sync

# Add a new dependency to a package/service
uv add <package> --package <workspace-member>

# Add a dev-only dependency
uv add --dev <package>

# Run the control plane service locally
uv run uvicorn services.control_plane.main:app --reload --port 3002

# Run the data plane service locally
uv run uvicorn services.data_plane.main:app --reload --port 3003

# Run the frontend dashboard locally
cd frontend && pnpm dev --port 3001

# Run the full test suite
uv run pytest

# Run tests for a single module
uv run pytest tests/trust_engine/

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

SpiceDB (with its Postgres backing store) and Redis run via `docker compose up` (compose file at repo root). MongoDB runs directly on the host (`localhost:27017`). Do not hardcode connection strings — read them from environment variables via a config module (see Section 5).

**Before considering any task complete:** run `uv run pytest`, `uv run ruff check .`, and `uv run mypy .`, and make sure all three pass. A task is not done if tests are red or linting fails.

---

## 4. Repository Structure (target layout)

```
.
├── packages/
│   ├── shared/                 # Config, logging, schemas, errors, http helpers
│   ├── trust_engine/           # Features (behavioral + graph), Isolation Forest, decay in Redis
│   ├── decision_engine/        # SpiceDB ReBAC checks, score bands, closed-loop narrow write-back
│   └── audit/                  # SHAP calculation & MongoDB audit logger
├── services/
│   ├── control_plane/          # CRUD API for upstreams/routes/middlewares (Port 3002)
│   └── data_plane/             # Proxy gateway with 4s config polling & pipeline (Port 3003)
├── frontend/                   # React + TypeScript + Vite Dashboard (Port 3001)
├── tests/                      # Mirrors structure — one test module per package/service
├── scripts/                    # Synthetic traffic generator, offline model training
├── models/                     # Serialized model artifacts (.joblib)
├── docker-compose.yml
├── pyproject.toml
└── AGENTS.md
```

Each package and service has a **single responsibility**. New code belongs inside the module that owns that responsibility — do not create a second place that also does policy checks, feature extraction, etc.

---

## 5. Coding Conventions

- **Modular by default.** Every module (`gateway`, `policy`, `features`, `trust_engine`, `decision`, `audit`) is independently testable and has a clear public interface (a small number of functions/classes other modules import — not free access to its internals).
- **Pydantic models for all data crossing a module boundary.** No passing raw dicts between modules — define a schema in `common/schemas.py` or the owning module.
- **Config via environment variables, loaded once** through a single `common/config.py` (pydantic `BaseSettings`). No `os.getenv()` scattered through the codebase.
- **Dependency injection for FastAPI routes** — use FastAPI's `Depends()` for things like the SpiceDB client, Redis client, and the loaded ML model, so they can be swapped out in tests.
- **No business logic in route handlers.** A FastAPI route function should validate input, call into the relevant module's service function, and return the response — the actual logic lives in the module, testable without spinning up FastAPI.
- **Type hints everywhere.** All function signatures fully typed; mypy strict mode must pass.
- **Docstrings on every public function/class** — one-line summary minimum; longer for anything implementing a non-obvious part of the design (e.g. the trust decay formula, the graph traversal comparison).
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, module names short and singular where possible (`policy`, not `policy_stuff`).
- **No premature abstraction.** Don't build a generic plugin system for "future anomaly models" unless asked — write the Isolation Forest implementation cleanly and make swapping it out a deliberate, visible refactor later.

---

## 6. Architecture Rules

These rules protect the project's actual novelty (graph-aware anomaly detection + closed-loop policy feedback). Do not erode them for convenience.

1. **The Trust Engine must consume both behavioral and graph features.** Never simplify it down to behavioral-only "request rate anomaly detection" — that collapses the project back into a generic IDS demo, which is explicitly *not* the goal.
2. **Graph features must come from real ReBAC traversal data** (SpiceDB's `Expand`/relationship data), not be mocked/faked permanently. Mocking is fine for unit tests; the integration path must be real.
3. **The Decision Engine must be able to write back to the policy store** (the `narrow` action). A decision engine that only logs or only blocks at the gateway, without ever adjusting the ReBAC graph, does not satisfy the design — the "closed loop" is a required property, not a nice-to-have.
4. **The trust score is stateful across a session, not recomputed independently per request.** Implement the decay/recovery function as specified — don't quietly replace it with a stateless per-request score even though it's simpler.
5. **Every decision (allow/step_up/narrow/deny) must produce an audit record with feature-level attribution.** A decision engine that returns a bare boolean without an explanation payload is incomplete.
6. **Separation of Control Plane and Data Plane with in-process evaluation for performance.** The system isolates the Control Plane (managing configuration in MongoDB on port 3002) from the Data Plane (proxying requests on port 3003). For high-throughput, sub-2ms request evaluation, the core evaluation modules (`trust_engine`, `decision_engine`, and `audit`) are packaged as isolated workspace packages and executed in-process within the Data Plane via strict, typed interfaces, with audit record persistence offloaded asynchronously. The Data Plane never talks directly to MongoDB; it polls the Control Plane every 4 seconds and continues proxying on its in-memory last-known-good configuration if the Control Plane is offline.
7. **Synthetic data generation and model training live in `scripts/`, not in `app/`.** Application code loads a trained model artifact; it does not train models at request time.

---

## 7. What the Agent Must Do

- **Work module by module.** Implement and fully test one module (e.g. `app/policy/`) before moving to the next, rather than sketching all modules simultaneously. Each unit of work should leave the repo in a state where `uv run pytest` and `uv run ruff check .` pass.
- **Write tests alongside implementation**, not as an afterthought — every new function in `app/` gets a corresponding test in `tests/`.
- **Ask before making an architectural decision** that isn't already specified here (e.g. choice of message queue, choice between Isolation Forest and LSTM-Autoencoder if not yet decided, schema design for the ReBAC relations) — propose an option and reasoning rather than silently picking one.
- **Keep commits/changes scoped.** One logical change (one module, one feature) per unit of work, with a clear description of what changed and why.
- **Update this file** if an architectural decision made during implementation changes something stated here (e.g. a dependency swap) — keep AGENTS.md in sync with reality.

## 8. What the Agent Must Not Do

- **Do not implement the entire project in one pass.** No single task should span gateway + policy + features + trust engine + decision + audit all at once. Break work into module-sized units and complete each one properly (implementation + tests + passing lint/type-check) before starting the next.
- **Do not use `pip`, `poetry`, or `conda`.** `uv` only.
- **Do not put business logic inside FastAPI route handlers.**
- **Do not fake or stub out the graph-feature extraction permanently** to make things easier — this is the project's core novelty, not an optional piece.
- **Do not let the Decision Engine become passive (log-only).** The `narrow` action's write-back to the policy store is required, not optional.
- **Do not introduce new major dependencies or frameworks** without flagging the choice explicitly.
- **Do not skip writing tests** to move faster — an implementation without tests is not considered complete.
- **Do not commit secrets, API keys, or real credentials** — all config comes from environment variables, with a `.env.example` kept up to date instead.