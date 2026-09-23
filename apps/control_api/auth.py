from __future__ import annotations
from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status
import jwt
from packages.contracts_python.settings import get_settings

ROLE_PERMISSIONS = {
    "tenant_owner": {"*"},
    "project_admin": {"project:write","agent:write","knowledge:write","deployment:write","read"},
    "agent_builder": {"agent:write","conversation:write","simulation:write","read"},
    "rsi_engineer": {"experiment:write","candidate:write","read"},
    "evaluator_admin": {"evaluation:write","scenario:hidden:read","read"},
    "reviewer": {"review:write","read"},
    "deployer": {"deployment:write","promotion:approve","read"},
    "auditor": {"read","audit:read"},
    "service_account": {"read"},
}

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    role: str
    permissions: frozenset[str]

async def get_principal(authorization: str | None = Header(default=None), x_tenant_id: str | None = Header(default=None)) -> Principal:
    settings = get_settings()
    if settings.dev_auth_enabled and not authorization:
        tid = x_tenant_id or "00000000-0000-4000-8000-000000000001"
        return Principal("dev-user", tid, "tenant_owner", frozenset({"*"}))
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience=settings.oidc_audience)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    role = str(payload.get("role","service_account"))
    tid = str(payload.get("tenant_id",""))
    if not tid:
        raise HTTPException(status_code=403, detail="tenant_id missing")
    return Principal(str(payload.get("sub","unknown")), tid, role, frozenset(ROLE_PERMISSIONS.get(role,set())))

def require(permission: str):
    async def dep(principal: Principal = Depends(get_principal)) -> Principal:
        if "*" not in principal.permissions and permission not in principal.permissions:
            raise HTTPException(status_code=403, detail=f"permission required: {permission}")
        return principal
    return dep
