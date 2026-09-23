# Platform Configuration Guide

Complete configuration reference for **Conversational-Agent-RSI**, detailing environment variables, settings schemas, runtime profiles, security flags, and provider adapters.

---

## Table of Contents

1. [Configuration Architecture](#1-configuration-architecture)
2. [Environment Variables Reference](#2-environment-variables-reference)
3. [Configuration Profiles](#3-configuration-profiles)
4. [Security & Authentication Configuration](#4-security--authentication-configuration)
5. [Storage, Databases & Messaging Configuration](#5-storage-databases--messaging-configuration)
6. [Model Gateway & LLM Provider Configuration](#6-model-gateway--llm-provider-configuration)
7. [Governance, Budgets & Observability](#7-governance-budgets--observability)
8. [Configuration Loading Order & Precedence](#8-configuration-loading-order--precedence)
9. [Secret Management & Production Best Practices](#9-secret-management--production-best-practices)

---

## 1. Configuration Architecture

Configuration in Conversational-Agent-RSI is defined centrally in `packages/contracts_python/settings.py` using Pydantic Settings (`BaseSettings`). It provides:
- Strongly-typed validation at startup.
- Dynamic environment variable parsing with case-insensitive matching.
- Sensible zero-dependency local defaults (SQLite, fake deterministic LLM, dev auth).
- Compatibility across FastAPI API, Temporal workers, Alembic migrations, and evaluation harnesses.
- Frontend runtime configuration for the Next.js web console via `NEXT_PUBLIC_` prefixed variables.

---

## 2. Environment Variables Reference

Below is the complete reference table for all configuration variables supported across backend and frontend services:

| Variable | Type | Default | Scope | Description |
|---|---|---|---|---|
| `APP_ENV` | `str` | `local` | Backend | Environment identifier (`local`, `dev`, `staging`, `production`). In `local`, detailed error payloads are returned. |
| `DEV_AUTH_ENABLED` | `bool` | `true` | Backend | When `true`, requests without Authorization headers automatically receive a tenant-owner principal (`00000000-0000-4000-8000-000000000001`). Must be `false` in production. |
| `DATABASE_URL` | `str` | `sqlite+aiosqlite:///./rsi.db` | Backend / Migrations | SQLAlchemy async connection string. For PostgreSQL: `postgresql+asyncpg://user:pass@host:5432/db`. |
| `REDIS_URL` | `str` | `redis://localhost:6379/0` | Backend | Connection string for Redis cache, rate limiting, and distributed locking. |
| `NATS_URL` | `str` | `nats://localhost:4222` | Backend | NATS JetStream server address for publishing and subscribing to platform events. |
| `TEMPORAL_ADDRESS` | `str` | `localhost:7233` | Backend / Worker | gRPC address for the Temporal workflow server orchestrating RSI loops. |
| `QDRANT_URL` | `str` | `http://localhost:6333` | Backend | Qdrant vector database HTTP API endpoint for embedding storage and semantic search. |
| `S3_ENDPOINT` | `str` | `http://localhost:9000` | Backend | S3-compatible object storage endpoint (MinIO locally, AWS S3 / Cloudflare R2 in prod). |
| `S3_BUCKET` | `str` | `rsi-artifacts` | Backend | S3 bucket name for immutable snapshots, evaluation dumps, and candidate policies. |
| `S3_ACCESS_KEY` | `str` | `localminio` | Backend | S3 access key / AWS access key ID. |
| `S3_SECRET_KEY` | `str` | `localminiosecret` | Backend | S3 secret key / AWS secret access key. |
| `POLICY_SIGNING_KEY` | `str` | `change-me` | Backend | Secret key used for cryptographic HMAC-SHA256 signing and verification of immutable policy versions. |
| `JWT_SECRET` | `str` | `change-me` | Backend | Secret key for verifying HS256 JWT bearer tokens when `DEV_AUTH_ENABLED=false`. |
| `OIDC_ISSUER` | `str` | `""` | Backend | Expected OIDC token issuer URL (for enterprise OAuth/OIDC integrations). |
| `OIDC_AUDIENCE` | `str` | `conversational-agent-rsi` | Backend | Expected audience claim (`aud`) in incoming JWT tokens. |
| `MODEL_GATEWAY_URL` | `str` | `""` | Backend / Runtime | Base URL for LLM gateway (e.g. LiteLLM proxy `http://localhost:4000` or direct OpenAI endpoint). If empty, deterministic fake model is used. |
| `MODEL_GATEWAY_API_KEY` | `str` | `""` | Backend / Runtime | API authorization key sent to the model gateway. |
| `DEFAULT_MODEL` | `str` | `fake/deterministic` | Backend | Default model identifier for agent responses and simulations when none is specified. |
| `DEFAULT_EMBEDDING_MODEL` | `str` | `fake/hash-embedding` | Backend | Default embedding model identifier used for RAG ingestion and retrieval queries. |
| `DEFAULT_TENANT_BUDGET_USD` | `float` | `25.0` | Backend | Maximum lifetime spending ceiling allocated to newly created tenants. |
| `DEFAULT_RUN_BUDGET_USD` | `float` | `5.0` | Backend | Maximum allowable spend per experiment or simulation run before hard stop. |
| `DEFAULT_MAX_TURNS` | `int` | `50` | Backend | Turn limit per conversation to prevent infinite dialogue loops. |
| `CORS_ORIGINS` | `str` | `http://localhost:3000` | Backend | Comma-separated list of allowed CORS origins for browser API calls. |
| `LOG_RAW_CONTENT` | `bool` | `false` | Backend | Whether to include raw message payloads in structured logging (keep `false` for PII/privacy). |
| `OTEL_EXPORTER_OTLP_ENDPOINT`| `str` | `""` | Backend | gRPC/HTTP endpoint for OpenTelemetry collector traces and metrics. |
| `NEXT_PUBLIC_API_URL` | `str` | `http://localhost:8000` | Frontend (`web`) | Base URL where the browser and Next.js SSR communicate with the Control Plane API. |

---

## 3. Configuration Profiles

### 3.1 Profile: Docker Compose (All-in-One Containerized)
Used by `make dev` and root `docker-compose.yml`. Services communicate over Docker network aliases:
```env
APP_ENV=local
DEV_AUTH_ENABLED=true
DATABASE_URL=postgresql+asyncpg://rsi:rsi@postgres:5432/rsi
REDIS_URL=redis://redis:6379/0
NATS_URL=nats://nats:4222
TEMPORAL_ADDRESS=temporal:7233
QDRANT_URL=http://qdrant:6333
S3_ENDPOINT=http://minio:9000
S3_BUCKET=rsi-artifacts
S3_ACCESS_KEY=localminio
S3_SECRET_KEY=localminiosecret
POLICY_SIGNING_KEY=local-dev-signing-key-change-me
JWT_SECRET=local-dev-jwt-secret-change-me
DEFAULT_MODEL=openai/gpt-5.6-luna
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3.2 Profile: Hybrid Dev (macOS Local Python & Next.js, Docker Infra)
Used when running API and frontend locally on macOS while databases run in Docker:
```env
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

### 3.3 Profile: Zero-Dependency Standalone Smoke
Used for offline smoke runs or unit testing on macOS without any running Docker containers:
```env
APP_ENV=local
DEV_AUTH_ENABLED=true
DATABASE_URL=sqlite+aiosqlite:///./rsi.db
POLICY_SIGNING_KEY=smoke-test-key
JWT_SECRET=smoke-test-key
DEFAULT_MODEL=fake/deterministic
DEFAULT_EMBEDDING_MODEL=fake/hash-embedding
```

### 3.4 Profile: Production
In production, enforce strict authentication, TLS, and external services:
```env
APP_ENV=production
DEV_AUTH_ENABLED=false
DATABASE_URL=postgresql+asyncpg://<app_user>:<managed_password>@<pg_host>:5432/<dbname>?ssl=require
REDIS_URL=rediss://:<redis_password>@<redis_host>:6380/0
NATS_URL=tls://<nats_user>:<nats_pass>@<nats_host>:4222
TEMPORAL_ADDRESS=<temporal_cloud_or_server>:7233
QDRANT_URL=https://<qdrant_cluster_endpoint>:6333
S3_ENDPOINT=https://s3.<region>.amazonaws.com
S3_BUCKET=<production_bucket_name>
S3_ACCESS_KEY=<aws_iam_access_key>
S3_SECRET_KEY=<aws_iam_secret_key>
POLICY_SIGNING_KEY=<vault_or_kms_managed_hmac_secret>
JWT_SECRET=<strong_jwt_shared_secret_or_oidc_jwks>
OIDC_ISSUER=https://auth.example.com/
OIDC_AUDIENCE=conversational-agent-rsi
MODEL_GATEWAY_URL=https://litellm-proxy.example.com
MODEL_GATEWAY_API_KEY=<gateway_api_key>
DEFAULT_MODEL=openai/gpt-5.6-luna
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
CORS_ORIGINS=https://rsi.example.com
LOG_RAW_CONTENT=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.monitoring:4317
NEXT_PUBLIC_API_URL=https://api.rsi.example.com
```

---

## 4. Security & Authentication Configuration

### 4.1 Dev Auth Mode vs Production RBAC
The system includes role-based access control (RBAC) supporting the following roles:
- `tenant_owner`: Wildcard permission (`*`)
- `project_admin`: `project:write`, `agent:write`, `knowledge:write`, `deployment:write`, `read`
- `agent_builder`: `agent:write`, `conversation:write`, `simulation:write`, `read`
- `rsi_engineer`: `experiment:write`, `candidate:write`, `read`
- `evaluator_admin`: `evaluation:write`, `scenario:hidden:read`, `read`
- `reviewer`: `review:write`, `read`
- `deployer`: `deployment:write`, `promotion:approve`, `read`
- `auditor`: `read`, `audit:read`
- `service_account`: `read`

**Dev Mode (`DEV_AUTH_ENABLED=true`):**
Requests with missing Authorization headers automatically inherit the `tenant_owner` role under default tenant `00000000-0000-4000-8000-000000000001` (or the tenant specified by the `X-Tenant-ID` header).

**Production Mode (`DEV_AUTH_ENABLED=false`):**
Requires standard HTTP `Authorization: Bearer <jwt_token>`.
Tokens must be signed with `JWT_SECRET` (HS256) and contain claims:
```json
{
  "sub": "user_12345",
  "tenant_id": "00000000-0000-4000-8000-000000000001",
  "role": "rsi_engineer",
  "aud": "conversational-agent-rsi"
}
```

### 4.2 Policy Cryptographic Signatures
To guarantee that candidate mutations are safe and tamper-proof, every policy version is cryptographically signed using HMAC-SHA256 with `POLICY_SIGNING_KEY`.
- Any modification to protected policy fields (e.g., `safety_policy_ref`, `evaluator_suite_ref`) invalidates the signature and blocks promotion.
- In production, rotate `POLICY_SIGNING_KEY` using standard KMS practices.

---

## 5. Storage, Databases & Messaging Configuration

### 5.1 Relational Database (`DATABASE_URL`)
- Uses SQLAlchemy 2.0 async engine (`create_async_engine`).
- Tested with:
  - PostgreSQL (`postgresql+asyncpg://...`): For multi-tenant concurrency and production deployments.
  - SQLite (`sqlite+aiosqlite:///./rsi.db`): For lightweight local runs and tests.
- Alembic database migrations read `DATABASE_URL` via `packages/contracts_python/settings.py`.

### 5.2 Vector Database (`QDRANT_URL`)
- Qdrant is used by `services/rag_service` for document embeddings and semantic retrieval.
- During local smoke runs without Qdrant, the RAG service falls back to lexical/deterministic search if configured.

### 5.3 Artifact Storage (`S3_*`)
- S3 / MinIO stores immutable snapshots, evaluation dumps, and candidate diffs.
- Supports AWS S3, Google Cloud Storage (via S3 interoperability), Cloudflare R2, and local MinIO.

### 5.4 Durable Orchestration (`TEMPORAL_ADDRESS`)
- Temporal orchestrates multi-step RSI cycles, simulation matrices, and long-running evaluations.
- Temporal worker connects to task queue `rsi-default`.

---

## 6. Model Gateway & LLM Provider Configuration

The conversation runtime and simulation service route LLM completions through `packages/provider_adapters/models.py`.

### 6.1 Deterministic Fake Mode (Offline / Zero Cost)
When `MODEL_GATEWAY_URL` is empty or `DEFAULT_MODEL=fake/deterministic`:
- No external network calls are made.
- Generates reproducible, policy-aligned responses suitable for automated testing and CI.
- No OpenAI or Anthropic API keys needed.

### 6.2 External LLM Gateway (LiteLLM / OpenAI)
To connect to live LLMs:
1. Set `MODEL_GATEWAY_URL`:
   - LiteLLM Proxy: `http://localhost:4000` or `https://litellm.internal`
   - Direct OpenAI: `https://api.openai.com/v1`
2. Set `MODEL_GATEWAY_API_KEY`: Your bearer token / API key.
3. Set `DEFAULT_MODEL`: e.g. `openai/gpt-4o`, `anthropic/claude-3-5-sonnet`, `meta-llama/llama-3.1-70b`.
4. Set `DEFAULT_EMBEDDING_MODEL`: e.g. `text-embedding-3-small`.

---

## 7. Governance, Budgets & Observability

- **Tenant Budgets (`DEFAULT_TENANT_BUDGET_USD`)**: Tenants have hard budget caps recorded in the `tenants` table. When spending reaches the cap, execution is blocked.
- **Run Budgets (`DEFAULT_RUN_BUDGET_USD`)**: Individual RSI experiment runs enforce a hard spending ceiling.
- **Turn Limits (`DEFAULT_MAX_TURNS`)**: Conversations automatically terminate if turns exceed this value, preventing runaway automated conversations.
- **Privacy Controls (`LOG_RAW_CONTENT`)**: Defaults to `false`. When `false`, conversational text and user inputs are excluded from server application logs to comply with privacy frameworks (GDPR, HIPAA).
- **OpenTelemetry (`OTEL_EXPORTER_OTLP_ENDPOINT`)**: When set, exports traces and metrics to Jaeger, Prometheus, or Grafana Tempo via standard OTLP protocols.

---

## 8. Configuration Loading Order & Precedence

Pydantic Settings resolves configuration in the following order (highest precedence first):
1. **Explicit Environment Variables** (in current shell or container runtime).
2. **`.env` file** in the project root directory.
3. **Pydantic Model Field Defaults** in `packages/contracts_python/settings.py`.

---

## 9. Secret Management & Production Best Practices

1. **Never commit `.env` files**: `.env` is listed in `.gitignore`. Use `.env.example` as a template only.
2. **Do not use default keys**: Always generate unique, high-entropy secrets for `POLICY_SIGNING_KEY` and `JWT_SECRET` in staging and production:
   ```bash
   openssl rand -hex 32
   ```
3. **Turn off Dev Auth in Production**: Ensure `DEV_AUTH_ENABLED=false` in any internet-facing deployment.
4. **Enforce Database SSL**: Append `?ssl=require` or configure root certificates for cloud-managed PostgreSQL.
5. **Audit Configuration Changes**: Changes to tenant risk tiers, budgets, and kill switches are automatically recorded in the `audit_events` ledger table.

---

*Related Documentation:*
- macOS Server & Dev Setup: [docs/operations/server-and-dev-setup-macos.md](docs/operations/server-and-dev-setup-macos.md)
- Operations Runbook: [docs/operations/runbook.md](docs/operations/runbook.md)
