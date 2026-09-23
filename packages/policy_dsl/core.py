from __future__ import annotations
import hashlib, hmac, json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
import yaml
from pydantic import BaseModel, Field

PROTECTED_FIELDS = {"safety_policy_ref", "evaluator_suite_ref", "tenant_permissions", "knowledge_snapshot_ref"}
ALLOWED_COMPONENTS = {"phase_policy","action_policy","retrieval_policy","tool_policy","response_policy","memory_policy","termination_policy"}

class PolicyDocument(BaseModel):
    id: str
    version: str
    description: str = ""
    phase_policy: dict[str, Any] = Field(default_factory=dict)
    action_policy: dict[str, Any] = Field(default_factory=dict)
    retrieval_policy: dict[str, Any] = Field(default_factory=dict)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    response_policy: dict[str, Any] = Field(default_factory=dict)
    memory_policy: dict[str, Any] = Field(default_factory=dict)
    termination_policy: dict[str, Any] = Field(default_factory=dict)
    safety_policy_ref: str
    evaluator_suite_ref: str
    knowledge_snapshot_ref: str | None = None
    tenant_permissions: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def content_hash(document: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(document).encode()).hexdigest()

def sign(document: dict[str, Any], key: str) -> str:
    return hmac.new(key.encode(), canonical_json(document).encode(), hashlib.sha256).hexdigest()

def verify(document: dict[str, Any], signature: str, key: str) -> bool:
    return hmac.compare_digest(sign(document, key), signature)

def parse_policy(text: str) -> PolicyDocument:
    raw = yaml.safe_load(text) if not text.lstrip().startswith("{") else json.loads(text)
    return PolicyDocument.model_validate(raw)

def semantic_diff(base: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    keys = sorted(set(base) | set(candidate))
    for key in keys:
        if base.get(key) != candidate.get(key):
            changes[key] = {"before": base.get(key), "after": candidate.get(key)}
    return changes

def validate_mutation(base: dict[str, Any], candidate: dict[str, Any], mutable: set[str] | None = None) -> list[str]:
    mutable = mutable or ALLOWED_COMPONENTS
    errors: list[str] = []
    for key in PROTECTED_FIELDS:
        if base.get(key) != candidate.get(key):
            errors.append(f"protected field changed: {key}")
    for key in semantic_diff(base, candidate):
        if key not in mutable and key not in {"version","description","metadata"}:
            errors.append(f"field is not mutable: {key}")
    try:
        PolicyDocument.model_validate(candidate)
    except Exception as exc:
        errors.append(f"schema validation failed: {exc}")
    return errors

def apply_mutation(base: dict[str, Any], component: str, patch: dict[str, Any]) -> dict[str, Any]:
    if component not in ALLOWED_COMPONENTS:
        raise ValueError(f"component not mutable: {component}")
    out = deepcopy(base)
    current = dict(out.get(component, {}))
    current.update(patch)
    out[component] = current
    return out

def choose_action(policy: PolicyDocument, state: dict[str, Any]) -> tuple[str, float]:
    phase = state.get("dialogue", {}).get("phase", "opening")
    rules = policy.action_policy.get("rules", [])
    for rule in rules:
        when = rule.get("when", {})
        if when.get("phase") in (None, phase):
            unmet = when.get("unresolved_fact")
            if unmet and unmet not in state.get("slots", {}).get("unresolved_facts", []):
                continue
            return str(rule.get("action", "clarify")), float(rule.get("confidence", .8))
    return str(policy.action_policy.get("default_action", "clarify")), .6
