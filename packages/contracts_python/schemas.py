from __future__ import annotations
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class SourceKind(StrEnum):
    observed = "observed"
    simulated = "simulated"
    counterfactual = "counterfactual"
    imported = "imported"
    human_authored = "human_authored"

class ActionFamily(StrEnum):
    dialogue = "dialogue"
    support = "support"
    training = "training"
    sales = "sales"
    rag = "rag"
    tool = "tool"
    safety = "safety"
    control = "control"

class EventType(StrEnum):
    conversation_started = "conversation.started"
    message_received = "message.received"
    action_selected = "action.selected"
    retrieval_completed = "retrieval.completed"
    tool_completed = "tool.completed"
    message_sent = "message.sent"
    conversation_finished = "conversation.finished"
    simulation_generated = "simulation.generated"

class ConversationAction(BaseModel):
    family: ActionFamily
    name: str
    confidence: float = Field(default=1.0, ge=0, le=1)
    rationale: str = ""
    requires_evidence: bool = False
    requires_tool: bool = False

class Citation(BaseModel):
    chunk_id: str
    source_id: str
    title: str = ""
    locator: str = ""
    quote: str = ""
    score: float = 0.0

class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    model_cost_usd: float = 0
    tool_cost_usd: float = 0
    compute_cost_usd: float = 0
    latency_ms: int = 0

    @property
    def total_cost_usd(self) -> float:
        return self.model_cost_usd + self.tool_cost_usd + self.compute_cost_usd

class ConversationState(BaseModel):
    model_config = ConfigDict(extra="allow")
    tenant_id: str
    project_id: str
    agent_id: str
    conversation_id: str
    scenario_id: str | None = None
    participants: dict[str, Any] = Field(default_factory=dict)
    dialogue: dict[str, Any] = Field(default_factory=lambda: {"turn_index": 0, "phase": "opening"})
    goals: dict[str, Any] = Field(default_factory=dict)
    slots: dict[str, Any] = Field(default_factory=lambda: {"discovered_facts": {}, "unresolved_facts": []})
    affect: dict[str, Any] = Field(default_factory=dict)
    knowledge: dict[str, Any] = Field(default_factory=dict)
    tools: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    governance: dict[str, Any] = Field(default_factory=dict)
    economics: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=lambda: {"observed_or_synthetic": "observed"})

class ConversationEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    conversation_id: str
    tenant_id: str
    event_type: EventType
    role: str | None = None
    content: str | None = None
    action: ConversationAction | None = None
    observation: dict[str, Any] = Field(default_factory=dict)
    citations: list[Citation] = Field(default_factory=list)
    source_kind: SourceKind = SourceKind.observed
    uncertainty: dict[str, Any] = Field(default_factory=dict)
    reward_vector: dict[str, float] = Field(default_factory=dict)
    artifact_refs: dict[str, Any] = Field(default_factory=dict)
    usage: Usage = Field(default_factory=Usage)
    created_at: datetime = Field(default_factory=utcnow)

class RetrievalPlan(BaseModel):
    query_strategy: Literal["hyde", "rewrite", "multi_query", "direct"] = "direct"
    queries: list[str]
    filters: dict[str, Any] = Field(default_factory=dict)
    dense_weight: float = Field(default=.65, ge=0, le=1)
    sparse_weight: float = Field(default=.35, ge=0, le=1)
    candidate_k: int = Field(default=40, ge=1, le=500)
    rerank_k: int = Field(default=12, ge=1, le=100)
    context_k: int = Field(default=6, ge=1, le=50)
    reranker: str | None = None
    max_context_tokens: int = Field(default=6000, ge=128, le=100000)
    diversity_lambda: float = Field(default=.25, ge=0, le=1)
    freshness_weight: float = Field(default=.10, ge=0, le=1)
    required_citation_coverage: float = Field(default=.95, ge=0, le=1)
    on_low_confidence: Literal["clarify", "broaden", "abstain"] = "clarify"

    @field_validator("sparse_weight")
    @classmethod
    def weights_sane(cls, value: float) -> float:
        return value

class RetrievalResult(BaseModel):
    plan: RetrievalPlan
    citations: list[Citation]
    context: str
    confidence: float = Field(ge=0, le=1)
    conflicts: list[str] = Field(default_factory=list)
    latency_ms: int = 0

class ModelMessage(BaseModel):
    role: Literal["system","user","assistant","tool"]
    content: str

class ModelRequest(BaseModel):
    model: str
    messages: list[ModelMessage]
    temperature: float = 0.2
    max_tokens: int = 1000
    metadata: dict[str, Any] = Field(default_factory=dict)

class ModelResponse(BaseModel):
    content: str
    usage: Usage = Field(default_factory=Usage)
    provider_fingerprint: str = "unknown"

class EvaluationResult(BaseModel):
    target_id: str
    suite_ref: str
    scores: dict[str, float]
    hard_constraints: dict[str, Any]
    violations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: dict[str, float] = Field(default_factory=dict)
    usage: Usage = Field(default_factory=Usage)

    @property
    def passed(self) -> bool:
        return bool(self.hard_constraints.get("passed", False))

class PolicyCandidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    parent_policy_version_id: str
    policy_document: dict[str, Any]
    diff: dict[str, Any]
    mutation_operator: str
    content_hash: str = ""
    validation_status: Literal["pending","valid","invalid"] = "pending"

class PromotionDecision(BaseModel):
    candidate_id: str
    decision: Literal["approve","reject","hold"]
    gates: dict[str, Any]
    reason: str
    approver_id: str | None = None

class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str
    trace_id: str
    retryable: bool = False
    field_errors: dict[str, str] = Field(default_factory=dict)
