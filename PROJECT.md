# TASK: Build the Zero-Trust API Gateway, step by step, with my approval at every stage

Read `AGENTS.md` in full first. It remains the source of truth for the novelty (graph-aware anomaly detection + closed-loop policy feedback), the tech stack, and the coding conventions. This prompt adds requirements and, where they conflict with AGENTS.md, **this prompt wins, but you must list each conflict and propose the AGENTS.md update for my approval.**

---

## 0. HARD RULES (non-negotiable)

1. **Do not write code, create files, install anything, or run any command until I explicitly approve that specific step.** Planning and discussion in chat are fine. Anything that touches the filesystem or the shell needs approval first.
2. **Work in small steps.** Never build more than one module or one logical unit per approval cycle. Do not "get ahead" and scaffold the next module.
3. **After each step, stop and report:** what you did, what tests/lint/type-checks passed, what you propose next. Then wait for my go-ahead.
4. **Ask before any decision not already specified**, and propose 2-3 options with a recommendation and reasoning. Do not silently pick.
5. **Do not add new major dependencies, frameworks, or services** beyond those listed here without flagging them first.
6. **Never commit secrets.** All config comes from environment variables, and `.env.example` is kept up to date.

---

## 1. WHAT WE ARE BUILDING

A Zero-Trust API Gateway with ReBAC authorization, continuous trust scoring, anomaly detection, a decision engine with closed-loop policy feedback, and SHAP explainability (as described in AGENTS.md section 1), plus a management dashboard.

### 1.1 Gateway split: control plane vs data plane
Users of the gateway only configure:
- **Upstreams** (backend services: name, URL, health/timeout settings)
- **Routes** (path/method matching → upstream, plus per-route settings)
- **Global middlewares** (which ones are enabled and their order/params)

Therefore:
- **Control plane** (CRUD API for upstreams/routes/middlewares; validates and stores config in MongoDB; exposes config to the data plane).
- **Data plane** (the actual request-proxying gateway; loads config from the control plane, never talks to MongoDB directly, and applies the middleware chain: auth → ReBAC check → trust scoring → decision engine → proxy).
- You must propose how config propagates from control plane to data plane (e.g. polling with versioning/ETag vs push/SSE) and get my approval. The data plane must keep serving with its last-known-good config if the control plane is down.

### 1.2 Ports
| Component | Port |
|---|---|
| Dashboard (React frontend) | **3001** |
| Control plane | **3002** |
| Data plane (gateway) | **3003** |

This overrides the 8000/8001 ports in AGENTS.md. Propose the corresponding AGENTS.md update. Internal services (trust engine, decision, audit, etc.) must also be separate services over HTTP/gRPC per AGENTS.md rule 6. Propose their ports, avoiding 3001-3003, and the actual service boundaries for my approval.

### 1.3 Storage and infrastructure
- **MongoDB** for gateway configs (upstreams, routes, middlewares, and audit records if you propose that). It is **already running on localhost:27017**; do NOT add Mongo to docker-compose. Handle the host-vs-container networking correctly (e.g. `host.docker.internal` / `extra_hosts` for Linux) and make the URI an env var.
- **Redis**, via Docker, for rolling behavioral windows and feature storage.
- **SpiceDB**, via Docker **only**. Propose its datastore (memory vs Postgres vs other) for my approval, since it affects persistence.
- **One `docker-compose.yml`** at the repo root that starts the dashboard, control plane, data plane, every internal service, Redis, and SpiceDB, with healthchecks, `depends_on` conditions, a shared network, and env-var-driven config. Local dev should also work with `uv run` per AGENTS.md section 3.

### 1.4 Dashboard
- React frontend created with exactly: `pnpm create vite@latest frontend`. Propose the template (React + TypeScript recommended) and get approval before running it.
- Runs on port **3001**.
- Manages upstreams, routes, and global middlewares by calling the control plane API only.
- Later (after core pieces exist), propose adding views for trust scores and decision/explanation audit logs. This is optional and needs my approval.

### 1.5 The novelty (must be implemented properly, not stubbed)
Per AGENTS.md sections 1 and 6, with these emphases:
- **ReBAC** via SpiceDB (schema, relationship writes, `Check`, `Expand`).
- **Continuous, stateful trust score** per session/subject with real decay and recovery logic (not a stateless per-request score).
- **Behavioral features** (request rate, geo-velocity, device/TLS fingerprint change, time-of-day deviation) and **graph-structural features** (path novelty, privilege-escalation shortcuts) derived from real SpiceDB traversal data.
- **Anomaly detection** with Isolation Forest (scikit-learn). Training and synthetic data live in `scripts/`, and the app only loads a model artifact.
- **Decision engine** mapping score bands to `allow` / `step_up` / `narrow`, where `narrow` **writes a temporary restricting relation back into SpiceDB** (with TTL/expiry handling). This closed loop is required.
- **SHAP** feature-level attribution on every decision, written to an audit record.
- **Features stored in Redis.**

---

## 2. DRY: the `shared` module
Create a top-level shared module for repetitive/cross-service code: config loading (pydantic settings), logging, pydantic schemas crossing service boundaries, HTTP client helpers, error types, health-check endpoint helpers, and common FastAPI dependencies. Rules:
- Anything used by 2+ services goes in `shared`. Never copy-paste it.
- `shared` has no business logic specific to one service and no circular dependencies on other modules.
- AGENTS.md currently has `app/common/`. Propose how `shared` replaces or relates to it (and how it is packaged, e.g. a `uv` workspace member) and the matching AGENTS.md update.

---

## 3. ENVIRONMENT
Use `uv` only (no pip, poetry, or conda; no manual venvs). After approval, set up the project properly: `pyproject.toml` (propose single project vs `uv` workspace with one member per service), a committed `uv.lock`, Python 3.12+, ruff, mypy (strict), pytest, `.env.example`, `.gitignore`, and a README with run instructions. For the frontend, use pnpm.

---

## 4. REQUIRED WORKFLOW

### Phase A: Planning (no code, no commands)
Produce a written architecture proposal covering:
1. Final list of modules/services and each one's single responsibility and public interface.
2. Final repo layout (reconcile AGENTS.md section 4 with the control/data plane split, `shared`, and `frontend`).
3. Service-to-service communication diagram (text/mermaid) including the request flow through the data plane and the closed feedback loop.
4. MongoDB collections and schemas, Redis key design (including TTLs), and the SpiceDB schema (definitions, relations, permissions, and how restricting/`narrow` relations are modeled).
5. Config propagation design (control plane → data plane).
6. Trust score formula (decay and recovery), score bands, and how session state is stored.
7. Feature list (behavioral + graph) and the model train/serve flow.
8. Audit record format with SHAP attribution.
9. Docker Compose service list, ports, volumes, healthchecks.
10. Conflicts with AGENTS.md and proposed edits to it.
11. **Ordered build plan**: the sequence of small steps, each with its scope, tests, and "done" criteria. Suggested order for you to refine: environment/scaffold → `shared` → control plane → data plane core (config loading + plain proxy) → policy/SpiceDB → features (behavioral, then graph) → training scripts + trust engine → decision engine + write-back → audit/SHAP → dashboard → full docker-compose and end-to-end test.
12. Open questions and risks.

**Stop here and wait for my written approval of the plan.**

### Phase B: Build, one step at a time
For each step in the approved plan:
1. State exactly which files you will create or change and which commands you will run, then **ask for approval**.
2. After approval: implement it plus its tests (tests are never optional).
3. Run `uv run pytest`, `uv run ruff check .`, `uv run mypy .` (and the frontend lint/build for dashboard steps). All must pass before the step counts as done.
4. Report results, summarize the change and why, note any AGENTS.md updates needed, propose the next step, and **stop**.

---

## 5. Definition of done (whole project, later)
- `docker compose up` brings up the dashboard (3001), control plane (3002), data plane (3003), the internal services, Redis, and SpiceDB, all healthy.
- I can add an upstream, route, and middleware from the dashboard, and the data plane picks it up and proxies traffic.
- Anomalous behavior or relationship paths lower the trust score, trigger `step_up` or `narrow`, and `narrow` verifiably writes a restricting relation to SpiceDB.
- Every decision has an audit record with SHAP attribution.
- Tests, lint, and type-checks are all green.

**Begin with Phase A only. Do not write code or run commands yet.**