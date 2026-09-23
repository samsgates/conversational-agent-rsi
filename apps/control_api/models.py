from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

def uid() -> str: return str(uuid4())
def now() -> datetime: return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    risk_tier: Mapped[str] = mapped_column(String(30), default="standard")
    hard_budget_usd: Mapped[float] = mapped_column(Float, default=25)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    domain_pack: Mapped[str] = mapped_column(String(200), default="generic-support")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AgentVersion(Base):
    __tablename__ = "agent_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    policy_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_config: Mapped[dict] = mapped_column(JSON, default=dict)
    knowledge_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluator_suite_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    __table_args__ = (UniqueConstraint("agent_id","version"),)

class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    agent_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    version: Mapped[str] = mapped_column(String(64))
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_json: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Deployment(Base):
    __tablename__ = "deployments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    agent_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_version_id: Mapped[str] = mapped_column(String(36))
    policy_version_id: Mapped[str] = mapped_column(String(36))
    stage: Mapped[str] = mapped_column(String(30), default="shadow")
    traffic_percent: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="active")
    rollback_target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    project_id: Mapped[str] = mapped_column(index=True)
    agent_id: Mapped[str] = mapped_column(index=True)
    deployment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    external_user_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_kind: Mapped[str] = mapped_column(String(30), default="observed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ConversationEventRow(Base):
    __tablename__ = "conversation_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_kind: Mapped[str] = mapped_column(String(30), default="observed")
    state_hash: Mapped[str] = mapped_column(String(64), index=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("conversation_id","sequence_no"),)

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    project_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(250))
    source_type: Mapped[str] = mapped_column(String(50))
    uri: Mapped[str] = mapped_column(Text, default="")
    checksum: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    locator: Mapped[str] = mapped_column(String(250), default="")
    checksum: Mapped[str] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

class KnowledgeSnapshot(Base):
    __tablename__ = "knowledge_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    project_id: Mapped[str] = mapped_column(index=True)
    version: Mapped[int] = mapped_column(Integer)
    manifest_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="published")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    project_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))
    split: Mapped[str] = mapped_column(String(30), default="train")
    visible_briefing: Mapped[dict] = mapped_column(JSON, default=dict)
    hidden_truth: Mapped[dict] = mapped_column(JSON, default=dict)
    goals: Mapped[dict] = mapped_column(JSON, default=dict)
    max_turns: Mapped[int] = mapped_column(Integer, default=20)

class EvaluatorSuite(Base):
    __tablename__ = "evaluator_suites"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, default=1)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    evaluator_suite_id: Mapped[str] = mapped_column(String(36))
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    project_id: Mapped[str] = mapped_column(index=True)
    manifest_json: Mapped[dict] = mapped_column(JSON)
    workflow_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="created")
    budget_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    experiment_id: Mapped[str] = mapped_column(String(36), index=True)
    policy_version_id: Mapped[str] = mapped_column(String(36))
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    diff_json: Mapped[dict] = mapped_column(JSON, default=dict)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending")

class ReplayRun(Base):
    __tablename__ = "replay_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True)
    world_id: Mapped[str] = mapped_column(String(36))
    mode: Mapped[str] = mapped_column(String(30))
    coverage_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_json: Mapped[dict] = mapped_column(JSON, default=dict)

class PromotionDecisionRow(Base):
    __tablename__ = "promotion_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True)
    gates_json: Mapped[dict] = mapped_column(JSON)
    decision: Mapped[str] = mapped_column(String(30))
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class UsageLedger(Base):
    __tablename__ = "usage_ledger"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    tokens_json: Mapped[dict] = mapped_column(JSON, default=dict)
    cost_usd: Mapped[float] = mapped_column(Float, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str] = mapped_column(String(30), default="observed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(120))
    object_ref: Mapped[str] = mapped_column(String(200))
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class ReviewItem(Base):
    __tablename__ = "review_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    tenant_id: Mapped[str] = mapped_column(index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

Index("ix_events_tenant_conversation", ConversationEventRow.tenant_id, ConversationEventRow.conversation_id)
Index("ix_usage_tenant_run", UsageLedger.tenant_id, UsageLedger.run_id)
