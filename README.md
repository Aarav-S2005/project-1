# Zero-Trust API Gateway

> **Zero-Trust API Gateway with Fine-Grained, Graph-Aware Authorization (SpiceDB ReBAC), Continuous Decaying Trust Scoring, Closed-Loop Policy Feedback, and SHAP Feature Attribution.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![SpiceDB](https://img.shields.io/badge/SpiceDB-v1.30+-purple.svg)](https://authzed.com/spicedb)
[![Docker Compose](https://img.shields.io/badge/docker--compose-ready-2496ED.svg)](https://docs.docker.com/compose/)

---

## 📖 Table of Contents
- [1. Architecture & Novelty](#1-architecture--novelty)
- [2. System Architecture & Port Map](#2-system-architecture--port-map)
- [3. Prerequisites](#3-prerequisites)
- [4. Quickstart: Clone, Initialize & Run (Docker - Recommended)](#4-quickstart-clone-initialize--run-docker---recommended)
- [5. Running the Interactive Demo Simulation](#5-running-the-interactive-demo-simulation)
- [6. Local Development Workflow (Without Docker)](#6-local-development-workflow-without-docker)
- [7. How It Works (Personas & Scenarios)](#7-how-it-works-personas--scenarios)
- [8. Model Retraining & Synthetic Traffic](#8-model-retraining--synthetic-traffic)
- [9. Testing & Code Quality](#9-testing--code-quality)

---

## 1. Architecture & Novelty

Conventional API gateways authenticate a user once at the perimeter (e.g., JWT verification) and grant static access. In contrast, this gateway continuously computes an adaptive trust score on every incoming request:

1. **Graph-Aware ReBAC (Relationship-Based Access Control)**:
   Permissions are derived from a relationship graph powered by **SpiceDB v1.30+** (e.g., `user:alice` is an `owner` of `document:doc_1`, or a `member` of `organization:acme`).
2. **Dual-Stream Feature Extraction**:
   - **Behavioral Features**: Sliding Redis request-rate windows (10s, 60s, burst ratio), Haversine geo-velocity, user-agent/TLS fingerprint anomalies, and time-of-day deviations.
   - **Graph-Structural Features**: SpiceDB permission tree expansion depth, path length, novel path discovery (`seen_paths` in Redis), and privilege-escalation shortcut scores.
3. **Continuous Anomaly Scoring & Stateful Decay**:
    Dual-stream vectors are evaluated using an **Isolation Forest** model. Trust decays continuously over time ($T_t = T_0 \cdot e^{-\lambda \Delta t}$) and recovers gradually with benign traffic.
4. **Closed-Loop Policy Feedback (`narrow`)**:
   When trust drops into the $[0.60, 0.85)$ band, the gateway does not merely log or alert: it writes a temporary restricting relation (`document:{id}#restricted_subject@{user}`) back into the SpiceDB ReBAC graph. The graph policy (`view = (owner | editor | viewer) - restricted_subject`) dynamically restricts access until the TTL expires or trust recovers.
5. **Feature-Level Explainability (SHAP)**:
   Every decision records TreeExplainer **SHAP attribution values**, showing operators exactly which features caused trust penalties.
6. **In-Process Request Evaluation**:
   Core evaluation packages (`trust_engine`, `decision_engine`, `audit`) execute in-process inside the Data Plane reverse proxy for sub-2ms evaluation latency, offloading audit records asynchronously to MongoDB.

---

## 2. System Architecture & Port Map

| Component | Technology | Port | Description |
| :--- | :--- | :--- | :--- |
| **Frontend Dashboard** | React 19, TypeScript, Vite | `3001` | Real-time observability, trust score management, & SHAP explainer |
| **Control Plane** | FastAPI, Uvicorn | `3002` | Management API for routes, upstreams, runtime parameters, & audit logs |
| **Data Plane** | FastAPI / Streaming Proxy | `3003` | Reverse proxy enforcing ReBAC, trust scoring, and closed-loop actions |
| **SpiceDB** | SpiceDB v1.30 | `50051` (gRPC), `8443` (HTTP) | ReBAC graph engine |
| **PostgreSQL** | Postgres 16 Alpine | `5432` | Persistent datastore backing SpiceDB |
| **Redis** | Redis 7 Alpine | `6379` | Behavioral rate windows, session state, & active narrow TTLs |
| **MongoDB** | MongoDB 7 | `27017` | Route configurations & immutable audit history |
| **Demo User Portal** | React, Vite | `4001` | Multi-persona attack simulation client (Alice, Bob, Charlie, Darth) |
| **Demo Microservices** | Node.js Express | `4010` - `4013` | Upstreams (Users: 4010, Docs: 4011, Payroll: 4012, Admin: 4013) |

---

## 3. Prerequisites

Before starting, ensure you have:
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) (v2.20+)
- *(Optional for local development)*:
  - [Python 3.12+](https://www.python.org/downloads/)
  - [`uv`](https://docs.astral.sh/uv/) (Python package & workspace manager)
  - [Node.js 20+](https://nodejs.org/) & [`pnpm`](https://pnpm.io/)

---

## 4. Quickstart: Clone, Initialize & Run (Docker - Recommended)

### Step 1: Clone the Repository
```bash
git clone https://github.com/Aarav-S2005/project-1.git
cd project-1
```

### Step 2: Initialize Environment Variables
Create your `.env` configuration file from the template:
```bash
# On Linux / macOS:
cp .env.example .env

# On Windows (PowerShell):
Copy-Item .env.example .env
```

*(Default credentials and endpoints inside `.env.example` are pre-configured to work out of the box with Docker Compose.)*

### Step 3: Start the Gateway Stack
Build and launch all database services, the SpiceDB ReBAC engine, the Control Plane, Data Plane, and Admin Dashboard:

```bash
docker compose up --build -d
```

### Step 4: Bootstrap ReBAC Schema & Initial Data
Once the containers are healthy, seed SpiceDB schemas, default routes, and initial users into the database:

```bash
# Execute the seed script inside the control_plane container:
docker compose exec control_plane uv run python scripts/seed_demo_data.py
```

### Step 5: Verify Everything is Running
Open your browser and navigate to:
- 📊 **Security Admin Dashboard**: [http://localhost:3001](http://localhost:3001)
- ⚙️ **Control Plane API Docs (Swagger)**: [http://localhost:3002/docs](http://localhost:3002/docs)
- 🛡️ **Data Plane Gateway Health**: [http://localhost:3003/health](http://localhost:3003/health)

---

## 5. Running the Interactive Demo Simulation

The repository includes a multi-persona client and upstream backend to test attacks, rate spikes, and closed-loop narrowing in real time.

### 1. Start the Demo Microservices & Demo Frontend
In a separate terminal:
```bash
cd demo
docker compose up --build -d
cd ..
```

### 2. Register Upstreams & ReBAC Tuples
Register the demo microservices with the Control Plane:
```bash
# Register upstream routes and permissions
docker compose exec control_plane uv run python scripts/seed_demo_data.py
```

### 3. Open the Demo User Portal
Navigate to:
- 🧪 **Demo User Portal**: [http://localhost:4001](http://localhost:4001)

Here you can select different personas (**Alice**, **Bob**, **Charlie**, or **Darth**) and trigger legitimate actions, privilege escalation attempts, or burst rate attacks. Watch the trust scores adjust and closed-loop narrowing trigger live in the Admin Dashboard ([http://localhost:3001](http://localhost:3001))!

---

## 6. Local Development Workflow (Without Docker)

If you prefer developing and debugging Python and React services locally with hot-reloading:

### 1. Start Backing Datastores in Docker
```bash
docker compose up -d spicedb_db spicedb_migrate spicedb redis mongodb
```

### 2. Install Dependencies
```bash
# Install Python workspace dependencies using uv
uv sync

# Install frontend dependencies
cd frontend && pnpm install && cd ..
```

### 3. Seed Local Data
```bash
uv run python scripts/seed_demo_data.py
```

### 4. Launch Services in Separate Terminals
```bash
# Terminal 1: Control Plane (Port 3002)
uv run uvicorn services.control_plane.main:app --reload --port 3002

# Terminal 2: Data Plane Gateway (Port 3003)
uv run uvicorn services.data_plane.main:app --reload --port 3003

# Terminal 3: Admin Frontend Dashboard (Port 3001)
cd frontend && pnpm dev --port 3001
```

---

## 7. How It Works (Personas & Scenarios)

### Decision Bands
| Trust Score | Action | Gateway Behavior |
| :--- | :--- | :--- |
| **$\ge 0.85$** | `allow` | Request permitted through to upstream; normal ReBAC check passes. |
| **$[0.60, 0.85)$** | `narrow` | Closed-loop policy write-back: temporary restriction relation written to SpiceDB; degraded access granted. |
| **$[0.40, 0.60)$** | `step_up` | Suspicious behavioral shift; intercepted with HTTP 401 MFA Challenge (`WWW-Authenticate: Bearer challenge=step_up_mfa`). |
| **$< 0.40$** | `deny` | Critical anomaly or ReBAC failure; intercepted with HTTP 403 Forbidden. |

### Included Personas
- **Alice (Admin / Org Owner)**: Normal high-trust access to documents and settings.
- **Bob (Finance Analyst)**: Authorized for payroll and accounting records; unauthorized for engineering specs.
- **Charlie (Engineering Intern)**: Authorized for public docs; restricted from payroll and production config.
- **Darth (External Attacker)**: Has no organization affiliation; repeatedly attempts unauthorized traversals, high-rate bursts, and credential stuffing.

### Resetting Trust Scores & Audit Logs
At any point during testing, you can use the top toolbar in the [Admin Dashboard](http://localhost:3001) to:
- **Restore User Trust to 1.0**: Restore a single user or all users to baseline nominal trust.
- **Clear Logs & Set All to 0.0**: Clear all MongoDB audit records and place all users in zero-trust lockdown mode.

---

## 8. Model Retraining & Synthetic Traffic

Pre-trained Isolation Forest and SHAP explainer models are included under `models/`. To generate fresh synthetic traffic datasets or retrain the models:

```bash
# 1. Generate synthetic dual-stream traffic samples
uv run python scripts/generate_synthetic_traffic.py

# 2. Retrain Isolation Forest & generate SHAP Explainer artifact
uv run python scripts/train_model.py
```

---

## 9. Testing & Code Quality

Run tests, linting, and type-checking across all workspace packages:

```bash
# Run pytest test suite
uv run pytest

# Run linter
uv run ruff check .

# Run code formatter check
uv run ruff format --check .

# Run strict type checking with mypy
uv run mypy .
```

---

## 📄 License
This project is licensed under the Apache 2.0 License.
