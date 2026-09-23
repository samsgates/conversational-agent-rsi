# Operations runbook

## Backup
Back up PostgreSQL with PITR, object storage with versioning, Qdrant snapshots, and configuration/secrets through the platform KMS or secret manager.

## Restore
Restore PostgreSQL first, then the immutable object artifacts and vector snapshot matching each knowledge snapshot. Validate signed policy artifacts and run the benchmark suite before serving traffic.

## Incident controls
Use tenant or deployment kill switches to stop new generations. Revoke affected policy artifacts, disable tool writes, capture trace IDs, preserve audit records, and roll back to the last known-good deployment.
