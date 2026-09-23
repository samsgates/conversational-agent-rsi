# ADR 0002. Local service consolidation

Status: accepted.

The developer profile packages service modules in a shared Python image to reduce local operational overhead while preserving boundaries in code. Production may split them into independently scaled deployments without changing contracts.
