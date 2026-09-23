from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class TenantCreate(BaseModel): name: str
class ProjectCreate(BaseModel): name: str; description: str = ""
class AgentCreate(BaseModel): project_id: str; name: str; domain_pack: str = "generic-support"
class AgentVersionCreate(BaseModel): policy_document: dict[str,Any]; model_config: dict[str,Any]=Field(default_factory=dict); knowledge_snapshot_id: str|None=None; evaluator_suite_id: str|None=None
class DeploymentCreate(BaseModel): agent_id: str; agent_version_id: str; policy_version_id: str; stage: str="shadow"; traffic_percent: int=0; rollback_target_id: str|None=None
class ConversationCreate(BaseModel): project_id: str; agent_id: str; deployment_id: str|None=None; scenario_id: str|None=None; external_user_id: str|None=None; source_kind: str="observed"
class MessageCreate(BaseModel): content: str
class KnowledgeSourceCreate(BaseModel): project_id: str; name: str; source_type: str="manual"; uri: str=""; content: str; metadata: dict[str,Any]=Field(default_factory=dict)
class SnapshotCreate(BaseModel): project_id: str; source_ids: list[str]
class ScenarioCreate(BaseModel): project_id: str; name: str; split: str="train"; visible_briefing: dict[str,Any]=Field(default_factory=dict); hidden_truth: dict[str,Any]=Field(default_factory=dict); goals: dict[str,Any]=Field(default_factory=dict); max_turns: int=20
class EvaluatorSuiteCreate(BaseModel): name: str; config: dict[str,Any]=Field(default_factory=dict)
class ExperimentCreate(BaseModel): project_id: str; baseline_policy_version_id: str; knowledge_snapshot_id: str; evaluator_suite_id: str; scenario_ids: list[str]=Field(default_factory=list); budget_usd: float=5
class CandidateCreate(BaseModel): experiment_id: str; evidence: dict[str,Any]=Field(default_factory=dict)
class ReviewCreate(BaseModel): target_id: str; payload: dict[str,Any]=Field(default_factory=dict)
class PromotionRequest(BaseModel): candidate_id: str; baseline_scores: dict[str,float]; candidate_scores: dict[str,float]; hard_constraints: dict[str,Any]; coverage: float; approve: bool=False
class RetrievalRequest(BaseModel): snapshot_id: str; query: str
class ChatCompletionRequest(BaseModel): model: str; messages: list[dict[str,Any]]; stream: bool=False; metadata: dict[str,Any]=Field(default_factory=dict)
