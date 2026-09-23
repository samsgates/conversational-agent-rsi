# Security model

- Every tenant-owned database query is tenant constrained.
- Production policies are signed and verified before deployment.
- Evaluation/safety/knowledge references are frozen by experiment manifests.
- Hidden challenge and calibration split content is permission-restricted.
- Side-effect tools require explicit permission and confirmation policy.
- Transcript content is treated as untrusted input.
- Raw prompt/transcript logging is disabled by default.
- Kill switches exist at tenant and deployment levels.
- Audit records and usage ledgers are append-oriented.
- Purge operations must span SQL, vectors, cache, object storage and analytics.
