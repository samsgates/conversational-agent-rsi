# Domain events

Subjects include `conversation.*`, `knowledge.*`, `evaluation.*`, `experiment.*`, `deployment.*`, and `security.*`. Each event envelope carries event ID, tenant ID, aggregate ID, schema version, timestamp, trace ID, source artifact versions, and payload checksum. Consumers must be idempotent and dead-letter malformed messages.
