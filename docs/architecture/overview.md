# Architecture overview

The online plane resolves a signed deployment, appends immutable events, projects state, runs safety checks, selects a semantic action, optionally retrieves evidence or uses a tool, generates a response, validates output, and appends provenance plus usage.

The offline plane evaluates observed and simulated trajectories, exact-replays stored branches, proposes allowlisted policy mutations, explores uncertainty with bounded synthetic branches, compares candidates using hard constraints and Pareto-aware metrics, and promotes only through shadow/canary gates.

Service boundaries are represented by separate modules and container targets. PostgreSQL is authoritative. Redis is cache/locks only. Qdrant is the production vector adapter target. NATS transports domain events. Temporal owns durable workflows. MinIO/S3 owns large immutable artifacts.
