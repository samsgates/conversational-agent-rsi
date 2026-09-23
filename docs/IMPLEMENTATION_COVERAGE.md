# Implementation coverage

This repository implements the supplied PRD as a runnable clean-room monorepo. The core runtime, immutable event model, policy DSL, tenant isolation, RAG snapshot metadata, evaluators, exact replay, candidate mutation, promotion gates, staged deployment records, rollback, OpenAI-compatible serving, reference domain packs, local infrastructure, Helm packaging, CI, tests, and web-console routes are included.

Provider-specific capabilities are connected through typed adapters. External model gateways, Qdrant, S3/MinIO, NATS, and Temporal are configured by environment variables and local Docker Compose. The deterministic fake model and lexical retriever make tests and local development independent of paid APIs.

Enhancements added on top of the minimum PRD implementation include deterministic offline model-free smoke operation, content-addressed policy artifacts, explicit synthetic/observed provenance, tenant kill switch enforcement in the runtime, injection/secret preflight checks, replay usage-ledger verification, clean-room ADRs, and a responsive console shell covering all primary product areas.
