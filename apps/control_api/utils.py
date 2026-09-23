from __future__ import annotations
import hashlib, json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from apps.control_api.models import AuditEvent
from apps.control_api.auth import Principal

def hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",",":")).encode()).hexdigest()

async def audit(session: AsyncSession, principal: Principal, action: str, object_ref: str, before: Any = None, after: Any = None, metadata: dict[str, Any] | None = None) -> None:
    session.add(AuditEvent(
        tenant_id=principal.tenant_id,
        actor=principal.subject,
        action=action,
        object_ref=object_ref,
        before_hash=hash_json(before) if before is not None else None,
        after_hash=hash_json(after) if after is not None else None,
        metadata_json=metadata or {},
    ))
