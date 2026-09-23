# macOS Server and Development Setup Guide

Comprehensive setup guide for running **Conversational-Agent-RSI** on macOS (Apple Silicon M1/M2/M3/M4 and Intel x86_64).

---

## Table of Contents

1. [Prerequisites on macOS](#1-prerequisites-on-macos)
2. [Setup Mode Overview](#2-setup-mode-overview)
3. [Mode 1: Full Docker Compose (Server Mode)](#3-mode-1-full-docker-compose-server-mode)
4. [Mode 2: Hybrid Dev Mode (Hot-Reloading & Local Debugging)](#4-mode-2-hybrid-dev-mode-hot-reloading--local-debugging)
5. [Mode 3: Lightweight Standalone Smoke Mode (Zero Docker)](#5-mode-3-lightweight-standalone-smoke-mode-zero-docker)
6. [macOS Specific Considerations & Troubleshooting](#6-macos-specific-considerations--troubleshooting)
7. [Verification and Testing](#7-verification-and-testing)

---

## 1. Prerequisites on macOS

Ensure you have the following installed on macOS:

### 1.1 Homebrew Package Manager
If Homebrew is not yet installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 1.2 Python 3.12
Conversational-Agent-RSI requires Python `>=3.12`. Install Python 3.12 via Homebrew:
```bash
brew install python@3.12
python3.12 --version
```

### 1.3 Node.js 20 or 22
Next.js 15 requires Node.js 20+ (Node 22 LTS recommended):
```bash
brew install node@22
node -v
npm -v
```

### 1.4 Docker Engine / Container Manager
On macOS, choose one of the following container runtimes:
- **Docker Desktop for Mac**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop/) (Enable VirtioFS in Settings -> General for faster file I/O on Apple Silicon).
- **OrbStack**: Fast, resource-efficient alternative (`brew install orbstack`).
- **Colima**: Open-source CLI container runtime (`brew install colima docker docker-compose && colima start --cpu 4 --memory 8`).

Verify Docker is running:
```bash
docker info
docker compose version
```

---

## 2. Setup Mode Overview

Depending on your workflow, you can choose between three modes:

| Mode | Use Case | Docker Needed? | Hot Reloading? | Services Included |
|---|---|---|---|---|
| **Mode 1: Full Docker Compose** | Server evaluation, full end-to-end integration | Yes (all containers) | Rebuild on change | API, Worker, Web, Postgres, Redis, Qdrant, MinIO, NATS, Temporal |
| **Mode 2: Hybrid Dev Mode** *(Recommended)* | Core development & active UI/API coding | Yes (infra containers only) | Instant (Python + Next.js hot reload) | Infra in Docker; API, Worker, and Web run on macOS host |
| **Mode 3: Standalone Smoke Mode** | Rapid CLI smoke test & unit testing | No | Instant | SQLite, fake model provider, lexical retrieval |

---

## 3. Mode 1: Full Docker Compose (Server Mode)

Runs the entire stack (infrastructure and application containers) via Docker Compose.

### Step 1: Clone and Prepare Environment
```bash
cd /Users/augray/SamData/Innovation/conversational-agent-rsi
cp .env.example .env
```

### Step 2: Launch All Services
```bash
make dev
```
*(Or directly: `docker compose up --build`)*

This command:
1. Bootstraps `.env` if not present.
2. Starts PostgreSQL, Redis, Qdrant, MinIO, NATS, and Temporal.
3. Waits for PostgreSQL to become healthy.
4. Builds and runs the `api` container (automatically running `alembic upgrade head` and `python scripts/seed.py`).
5. Starts the Temporal `worker` container.
6. Builds and starts the Next.js `web` console container.

### Step 3: Access Service Endpoints

| Service | URL | Description | Default Credentials |
|---|---|---|---|
| **Web Console** | `http://localhost:3000` | Full administrative UI | Dev Auth auto-login |
| **Control Plane API** | `http://localhost:8000` | FastAPI application | None (Dev Auth enabled) |
| **OpenAPI Interactive Docs** | `http://localhost:8000/docs` | Swagger UI for all endpoints | Dev Auth enabled |
| **API Health Check** | `http://localhost:8000/healthz` | System health probe | - |
| **API Readiness Check** | `http://localhost:8000/readyz` | Database connectivity probe | - |
| **MinIO Console** | `http://localhost:9001` | Object storage dashboard | User: `localminio` / Pass: `localminiosecret` |
| **MinIO S3 API** | `http://localhost:9000` | S3 artifact storage endpoint | - |
| **Qdrant Dashboard** | `http://localhost:6333/dashboard` | Vector database web interface | - |
| **NATS Monitoring** | `http://localhost:8222` | NATS JetStream telemetry | - |

### Step 4: Stopping Services
```bash
make stop
```
*(Or `docker compose down` — add `-v` if you wish to clear volume persistence: `docker compose down -v`)*

---

## 4. Mode 2: Hybrid Dev Mode (Hot-Reloading & Local Debugging)

This mode runs backing databases in Docker while running the Python API, Worker, and Next.js frontend directly on macOS for instant hot-reload and breakpoint debugging.

### Step 1: Start Backing Infrastructure in Docker
Start only the backing storage and messaging containers:
```bash
docker compose up -d postgres redis qdrant minio nats temporal
```

Verify infra is healthy:
```bash
docker compose ps
```

### Step 2: Configure Environment for Local Host
In `.env`, configure the endpoints to point to `localhost` instead of container hostnames:
```bash
APP_ENV=local
DEV_AUTH_ENABLED=true
DATABASE_URL=postgresql+asyncpg://rsi:rsi@localhost:5432/rsi
REDIS_URL=redis://localhost:6379/0
NATS_URL=nats://localhost:4222
TEMPORAL_ADDRESS=localhost:7233
QDRANT_URL=http://localhost:6333
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=rsi-artifacts
S3_ACCESS_KEY=localminio
S3_SECRET_KEY=localminiosecret
POLICY_SIGNING_KEY=local-dev-signing-key-change-me
JWT_SECRET=local-dev-jwt-secret-change-me
DEFAULT_MODEL=fake/deterministic
DEFAULT_EMBEDDING_MODEL=fake/hash-embedding
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Setup Local Python Virtual Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

### Step 4: Run Database Migrations and Seed Demo Data
```bash
source .venv/bin/activate
alembic upgrade head
python scripts/seed.py
```

### Step 5: Start the API with Auto-Reload
In your first terminal tab:
```bash
source .venv/bin/activate
uvicorn apps.control_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6: Start the Temporal Worker (Optional for RSI Workflows)
In a second terminal tab:
```bash
source .venv/bin/activate
python -m services.worker_runtime.main
```

### Step 7: Start the Next.js Web Console
In a third terminal tab:
```bash
cd apps/web
npm install
npm run dev
```
Open `http://localhost:3000` in your browser. Any changes to frontend components or backend routes reload instantly.

---

## 5. Mode 3: Lightweight Standalone Smoke Mode (Zero Docker)

To run a fast, low-overhead smoke test without Docker:

```bash
# 1. Create venv and install dependencies
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure SQLite and Dev Auth
export DATABASE_URL="sqlite+aiosqlite:///./rsi.db"
export DEV_AUTH_ENABLED="true"
export APP_ENV="local"
export POLICY_SIGNING_KEY="local-smoke-key"

# 3. Migrate and seed
alembic upgrade head
python scripts/seed.py

# 4. Run the API
uvicorn apps.control_api.main:app --reload --port 8000
```

In another terminal, run frontend against the local API:
```bash
cd apps/web
npm install
npm run dev
```

---

## 6. macOS Specific Considerations & Troubleshooting

### 6.1 Port Conflicts on macOS
Common local macOS services may conflict with platform ports:
- **PostgreSQL (`5432`)**: If Homebrew PostgreSQL is running locally, Docker cannot bind `5432:5432`.
  ```bash
  # Check if port 5432 is occupied
  lsof -i :5432
  # Stop Homebrew postgres if running
  brew services stop postgresql@16 || brew services stop postgresql
  ```
- **Redis (`6379`)**:
  ```bash
  lsof -i :6379
  brew services stop redis
  ```
- **AirPlay Receiver (`5000` / `7000`)**:
  macOS uses port 5000 and 7000 for AirPlay Receiver by default. This platform uses `8000` and `3000`, avoiding AirPlay. However, if you customize ports, ensure AirPlay does not interfere (System Settings -> General -> AirDrop & AirPlay -> Turn off AirPlay Receiver).

### 6.2 Apple Silicon (`arm64`) Architecture
All container images specified in `docker-compose.yml` (`postgres:16-alpine`, `redis:7-alpine`, `qdrant/qdrant:v1.12.6`, `nats:2.10-alpine`, `temporalio/auto-setup:1.27.2`, `python:3.12-slim`, `node:22-alpine`) provide native ARM64 multi-arch builds.
If Docker produces architecture warnings, ensure:
```bash
export DOCKER_DEFAULT_PLATFORM=linux/arm64
```

### 6.3 macOS zsh Variable Safety
In macOS `zsh`, `path` is an internal array synchronized with `$PATH`. Never assign a variable named `path` in shell scripts or terminal commands:
```bash
# BAD in zsh:
path="/some/dir"   # Corrupts your $PATH!

# GOOD:
file_path="/some/dir"
```

### 6.4 File Descriptor Limits (ulimit)
Running multiple containers and local Node/Python watchers can exhaust default macOS file descriptor limits. If you see `EMFILE: too many open files`:
```bash
ulimit -n 65536
```
Add `ulimit -n 65536` to your `~/.zshrc` if needed.

---

## 7. Verification and Testing

Run the test suite to verify the local installation:

```bash
source .venv/bin/activate

# Unit and contract tests
make test
# Or: pytest -q tests/unit tests/contract

# Code quality & types
make lint
make typecheck

# Integration tests (requires Docker infra or live DB)
make test-integration

# Security & adversarial policy tests
make test-security

# Synthetic benchmark
make benchmark
```

---

*Related Documentation:*
- Configuration reference: [docs/operations/configuration-guide.md](docs/operations/configuration-guide.md)
- Runbook & recovery: [docs/operations/runbook.md](docs/operations/runbook.md)
- Architecture overview: [docs/architecture/overview.md](docs/architecture/overview.md)
