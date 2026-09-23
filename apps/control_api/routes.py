from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.control_api.api_schemas import *
from apps.control_api.auth import Principal, get_principal, require
from apps.control_api.db import get_session
from apps.control_api.models import *
from apps.control_api.utils import audit
from apps.conversation_runtime.runtime import append_event, run_turn
from packages.contracts_python.schemas import RetrievalPlan
from packages.contracts_python.settings import get_settings
from packages.policy_dsl.core import content_hash, sign, validate_mutation
from services.rag_service.service import chunk_text, retrieve_for_conversation
from services.evaluation_service.evaluators import evaluate_deterministic, weighted_score
from services.rsi_orchestrator.core import exact_replay, propose_candidates, promotion_gate

router=APIRouter(prefix="/api/v1")
settings=get_settings()

def to_dict(obj: Any) -> dict[str,Any]:
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns}

@router.get("/me")
async def me(p: Principal=Depends(get_principal)) -> dict[str,Any]:
    return {"subject":p.subject,"tenant_id":p.tenant_id,"role":p.role,"permissions":sorted(p.permissions)}

@router.post("/tenants", status_code=201)
async def create_tenant(body: TenantCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    obj=Tenant(id=p.tenant_id,name=body.name,hard_budget_usd=settings.default_tenant_budget_usd)
    session.add(obj); await audit(session,p,"tenant.created",f"tenant:{obj.id}",after={"name":obj.name}); await session.commit(); return to_dict(obj)

@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    if tenant_id!=p.tenant_id: raise HTTPException(403,"cross-tenant access denied")
    obj=await session.get(Tenant,tenant_id)
    if not obj: raise HTTPException(404,"tenant not found")
    return to_dict(obj)

@router.patch("/tenants/{tenant_id}")
async def patch_tenant(tenant_id: str, patch: dict[str,Any], session: AsyncSession=Depends(get_session), p: Principal=Depends(require("project:write"))):
    if tenant_id!=p.tenant_id: raise HTTPException(403,"cross-tenant access denied")
    obj=await session.get(Tenant,tenant_id)
    if not obj: raise HTTPException(404,"tenant not found")
    before=to_dict(obj)
    for key in ("name","risk_tier","hard_budget_usd","kill_switch"):
        if key in patch: setattr(obj,key,patch[key])
    await audit(session,p,"tenant.updated",f"tenant:{obj.id}",before, to_dict(obj)); await session.commit(); return to_dict(obj)

@router.get("/projects")
async def list_projects(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    return [to_dict(x) for x in (await session.execute(select(Project).where(Project.tenant_id==p.tenant_id))).scalars().all()]

@router.post("/projects", status_code=201)
async def create_project(body: ProjectCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("project:write"))):
    obj=Project(tenant_id=p.tenant_id,name=body.name,description=body.description); session.add(obj); await session.flush(); await audit(session,p,"project.created",f"project:{obj.id}",after=to_dict(obj)); await session.commit(); return to_dict(obj)

@router.get("/agents")
async def list_agents(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    return [to_dict(x) for x in (await session.execute(select(Agent).where(Agent.tenant_id==p.tenant_id))).scalars().all()]

@router.post("/agents",status_code=201)
async def create_agent(body: AgentCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("agent:write"))):
    project=await session.scalar(select(Project).where(Project.id==body.project_id,Project.tenant_id==p.tenant_id))
    if not project: raise HTTPException(404,"project not found")
    obj=Agent(tenant_id=p.tenant_id,project_id=body.project_id,name=body.name,domain_pack=body.domain_pack); session.add(obj); await session.flush(); await audit(session,p,"agent.created",f"agent:{obj.id}",after=to_dict(obj)); await session.commit(); return to_dict(obj)

@router.post("/agents/{agent_id}/versions",status_code=201)
async def create_agent_version(agent_id: str, body: AgentVersionCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("agent:write"))):
    agent=await session.scalar(select(Agent).where(Agent.id==agent_id,Agent.tenant_id==p.tenant_id))
    if not agent: raise HTTPException(404,"agent not found")
    doc=dict(body.policy_document)
    doc.setdefault("id",f"{agent_id}:policy"); doc.setdefault("version","1"); doc.setdefault("safety_policy_ref","builtin:safe-v1"); doc.setdefault("evaluator_suite_ref",body.evaluator_suite_id or "builtin:generic-v1")
    errors=validate_mutation(doc,doc)
    if errors: raise HTTPException(422,errors)
    pv=PolicyVersion(tenant_id=p.tenant_id,agent_id=agent_id,version=str(doc["version"]),document_json=doc,content_hash=content_hash(doc),signature=sign(doc,settings.policy_signing_key),status="signed")
    session.add(pv); await session.flush()
    current=(await session.scalar(select(func.max(AgentVersion.version)).where(AgentVersion.agent_id==agent_id))) or 0
    av=AgentVersion(tenant_id=p.tenant_id,agent_id=agent_id,version=current+1,policy_version_id=pv.id,model_config=body.model_config,knowledge_snapshot_id=body.knowledge_snapshot_id,evaluator_suite_id=body.evaluator_suite_id,status="ready")
    session.add(av); await session.flush(); await audit(session,p,"agent.version_created",f"agent_version:{av.id}",after=to_dict(av)); await session.commit()
    return {"agent_version":to_dict(av),"policy_version":to_dict(pv)}

@router.get("/agent-versions/{version_id}/diff")
async def agent_version_diff(version_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    av=await session.scalar(select(AgentVersion).where(AgentVersion.id==version_id,AgentVersion.tenant_id==p.tenant_id))
    if not av: raise HTTPException(404,"version not found")
    return {"id":av.id,"policy_version_id":av.policy_version_id,"model_config":av.model_config}

@router.post("/deployments",status_code=201)
async def create_deployment(body: DeploymentCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("deployment:write"))):
    if body.stage not in {"shadow","canary","production"}: raise HTTPException(422,"invalid stage")
    pv=await session.scalar(select(PolicyVersion).where(PolicyVersion.id==body.policy_version_id,PolicyVersion.tenant_id==p.tenant_id,PolicyVersion.status=="signed"))
    if not pv: raise HTTPException(422,"signed policy required")
    obj=Deployment(tenant_id=p.tenant_id,agent_id=body.agent_id,agent_version_id=body.agent_version_id,policy_version_id=body.policy_version_id,stage=body.stage,traffic_percent=body.traffic_percent,rollback_target_id=body.rollback_target_id)
    session.add(obj); await session.flush(); await audit(session,p,"deployment.created",f"deployment:{obj.id}",after=to_dict(obj)); await session.commit(); return to_dict(obj)

@router.get("/deployments")
async def list_deployments(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    return [to_dict(x) for x in (await session.execute(select(Deployment).where(Deployment.tenant_id==p.tenant_id))).scalars().all()]

@router.post("/deployments/{deployment_id}/rollback")
async def rollback(deployment_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("deployment:write"))):
    dep=await session.scalar(select(Deployment).where(Deployment.id==deployment_id,Deployment.tenant_id==p.tenant_id))
    if not dep or not dep.rollback_target_id: raise HTTPException(422,"rollback target unavailable")
    target=await session.scalar(select(Deployment).where(Deployment.id==dep.rollback_target_id,Deployment.tenant_id==p.tenant_id))
    if not target: raise HTTPException(404,"rollback target not found")
    dep.status="rolled_back"; target.status="active"; target.stage="production"; target.traffic_percent=100
    await audit(session,p,"deployment.rollback",f"deployment:{dep.id}",metadata={"target":target.id}); await session.commit(); return {"rolled_back":dep.id,"active":target.id}

@router.post("/conversations",status_code=201)
async def create_conversation(body: ConversationCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("conversation:write"))):
    obj=Conversation(tenant_id=p.tenant_id,project_id=body.project_id,agent_id=body.agent_id,deployment_id=body.deployment_id,scenario_id=body.scenario_id,external_user_id=body.external_user_id,source_kind=body.source_kind,state_json={"tenant_id":p.tenant_id,"project_id":body.project_id,"agent_id":body.agent_id,"conversation_id":"","dialogue":{"turn_index":0,"phase":"opening"},"slots":{"discovered_facts":{},"unresolved_facts":[]},"governance":{}})
    session.add(obj); await session.flush(); obj.state_json={**obj.state_json,"conversation_id":obj.id}; await append_event(session,obj,"conversation.started","system",None,{"source_kind":body.source_kind},body.source_kind); await session.commit(); return to_dict(obj)

@router.post("/conversations/{conversation_id}/messages")
async def message(conversation_id: str, body: MessageCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("conversation:write"))):
    obj=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not obj: raise HTTPException(404,"conversation not found")
    result=await run_turn(session,obj,body.content); await session.commit(); return {"conversation_id":obj.id,**result}

@router.get("/conversations/{conversation_id}/events")
async def events(conversation_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    obj=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not obj: raise HTTPException(404,"conversation not found")
    rows=(await session.execute(select(ConversationEventRow).where(ConversationEventRow.conversation_id==conversation_id,ConversationEventRow.tenant_id==p.tenant_id).order_by(ConversationEventRow.sequence_no))).scalars().all()
    return [to_dict(x) for x in rows]

@router.post("/conversations/{conversation_id}/stop")
async def stop_conversation(conversation_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("conversation:write"))):
    obj=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not obj: raise HTTPException(404,"conversation not found")
    obj.status="stopped"; await append_event(session,obj,"conversation.finished","system",None,{"reason":"requested"}); await session.commit(); return {"status":"stopped"}

@router.post("/conversations/{conversation_id}/branches")
async def branch_conversation(conversation_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("conversation:write"))):
    src=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not src: raise HTTPException(404,"conversation not found")
    child=Conversation(tenant_id=p.tenant_id,project_id=src.project_id,agent_id=src.agent_id,deployment_id=src.deployment_id,scenario_id=src.scenario_id,status="active",state_json=dict(src.state_json),source_kind="counterfactual")
    session.add(child); await session.flush(); child.state_json={**child.state_json,"conversation_id":child.id}; await append_event(session,child,"conversation.started","system",None,{"branched_from":src.id},"counterfactual"); await session.commit(); return to_dict(child)

@router.post("/knowledge/sources",status_code=201)
async def add_source(body: KnowledgeSourceCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("knowledge:write"))):
    checksum=hashlib.sha256(body.content.encode()).hexdigest()
    existing=await session.scalar(select(KnowledgeSource).where(KnowledgeSource.tenant_id==p.tenant_id,KnowledgeSource.checksum==checksum))
    if existing: return to_dict(existing)
    src=KnowledgeSource(tenant_id=p.tenant_id,project_id=body.project_id,name=body.name,source_type=body.source_type,uri=body.uri,checksum=checksum,metadata_json=body.metadata)
    session.add(src); await session.flush()
    for i,text in enumerate(chunk_text(body.content)):
        session.add(KnowledgeChunk(tenant_id=p.tenant_id,source_id=src.id,text=text,locator=f"chunk:{i+1}",checksum=hashlib.sha256(text.encode()).hexdigest(),metadata_json={"title":body.name,**body.metadata}))
    await audit(session,p,"knowledge.source_registered",f"knowledge_source:{src.id}",after=to_dict(src)); await session.commit(); return to_dict(src)

@router.post("/knowledge/ingestions",status_code=202)
async def ingestion_alias(body: KnowledgeSourceCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("knowledge:write"))):
    return await add_source(body,session,p)

@router.get("/knowledge/jobs/{job_id}")
async def knowledge_job(job_id: str, p: Principal=Depends(get_principal)):
    return {"operation_id":job_id,"status":"completed","trace_id":job_id}

@router.post("/knowledge/snapshots",status_code=201)
async def snapshot(body: SnapshotCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("knowledge:write"))):
    valid=(await session.execute(select(KnowledgeSource.id).where(KnowledgeSource.tenant_id==p.tenant_id,KnowledgeSource.id.in_(body.source_ids)))).scalars().all()
    if set(valid)!=set(body.source_ids): raise HTTPException(422,"one or more sources are unauthorized or missing")
    ver=(await session.scalar(select(func.max(KnowledgeSnapshot.version)).where(KnowledgeSnapshot.tenant_id==p.tenant_id,KnowledgeSnapshot.project_id==body.project_id))) or 0
    obj=KnowledgeSnapshot(tenant_id=p.tenant_id,project_id=body.project_id,version=ver+1,manifest_json={"source_ids":body.source_ids,"immutable":True})
    session.add(obj); await session.commit(); return to_dict(obj)

@router.post("/retrieval/query")
async def retrieval(body: RetrievalRequest, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    rr=await retrieve_for_conversation(session,p.tenant_id,body.snapshot_id,RetrievalPlan(queries=[body.query]))
    return rr.model_dump()

@router.post("/scenarios",status_code=201)
async def create_scenario(body: ScenarioCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("agent:write"))):
    obj=Scenario(tenant_id=p.tenant_id,project_id=body.project_id,name=body.name,split=body.split,visible_briefing=body.visible_briefing,hidden_truth=body.hidden_truth,goals=body.goals,max_turns=body.max_turns); session.add(obj); await session.commit(); return to_dict(obj)

@router.get("/scenarios")
async def list_scenarios(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    rows=(await session.execute(select(Scenario).where(Scenario.tenant_id==p.tenant_id))).scalars().all()
    out=[]
    hidden_allowed="*" in p.permissions or "scenario:hidden:read" in p.permissions
    for x in rows:
        d=to_dict(x)
        if not hidden_allowed: d["hidden_truth"]={"redacted":True}
        out.append(d)
    return out

@router.post("/evaluator-suites",status_code=201)
async def create_suite(body: EvaluatorSuiteCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("evaluation:write"))):
    obj=EvaluatorSuite(tenant_id=p.tenant_id,name=body.name,config_json=body.config); session.add(obj); await session.commit(); return to_dict(obj)

@router.post("/evaluations/{conversation_id}")
async def evaluate(conversation_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    conv=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not conv: raise HTTPException(404,"conversation not found")
    rows=(await session.execute(select(ConversationEventRow).where(ConversationEventRow.conversation_id==conversation_id,ConversationEventRow.tenant_id==p.tenant_id).order_by(ConversationEventRow.sequence_no))).scalars().all()
    result=evaluate_deterministic(conversation_id,[to_dict(x) for x in rows])
    ev=Evaluation(tenant_id=p.tenant_id,target_id=conversation_id,evaluator_suite_id=result.suite_ref,result_json=result.model_dump(mode="json")); session.add(ev); await session.commit()
    return result.model_dump()

@router.post("/reviews",status_code=201)
async def create_review(body: ReviewCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    obj=ReviewItem(tenant_id=p.tenant_id,target_id=body.target_id,payload_json=body.payload); session.add(obj); await session.commit(); return to_dict(obj)

@router.get("/reviews")
async def list_reviews(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    return [to_dict(x) for x in (await session.execute(select(ReviewItem).where(ReviewItem.tenant_id==p.tenant_id))).scalars().all()]

@router.post("/experiments",status_code=201)
async def create_experiment(body: ExperimentCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("experiment:write"))):
    manifest={"baseline_policy_version_id":body.baseline_policy_version_id,"knowledge_snapshot_id":body.knowledge_snapshot_id,"evaluator_suite_id":body.evaluator_suite_id,"scenario_ids":body.scenario_ids,"frozen":True,"created_at":datetime.now(timezone.utc).isoformat()}
    obj=Experiment(tenant_id=p.tenant_id,project_id=body.project_id,manifest_json=manifest,budget_json={"usd":body.budget_usd,"spent_usd":0},status="created"); session.add(obj); await session.commit(); return to_dict(obj)

@router.get("/experiments")
async def list_experiments(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    return [to_dict(x) for x in (await session.execute(select(Experiment).where(Experiment.tenant_id==p.tenant_id))).scalars().all()]

@router.post("/candidates",status_code=201)
async def candidates(body: CandidateCreate, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("candidate:write"))):
    exp=await session.scalar(select(Experiment).where(Experiment.id==body.experiment_id,Experiment.tenant_id==p.tenant_id))
    if not exp: raise HTTPException(404,"experiment not found")
    pv=await session.scalar(select(PolicyVersion).where(PolicyVersion.id==exp.manifest_json["baseline_policy_version_id"],PolicyVersion.tenant_id==p.tenant_id))
    if not pv: raise HTTPException(404,"baseline policy not found")
    proposed=propose_candidates(pv.document_json,body.evidence)
    out=[]
    for cand in proposed:
        newpv=PolicyVersion(tenant_id=p.tenant_id,agent_id=pv.agent_id,version=f"{pv.version}-cand",parent_id=pv.id,document_json=cand.policy_document,content_hash=cand.content_hash,status="candidate")
        session.add(newpv); await session.flush()
        row=Candidate(tenant_id=p.tenant_id,experiment_id=exp.id,policy_version_id=newpv.id,parent_id=pv.id,diff_json=cand.diff,validation_status=cand.validation_status)
        session.add(row); await session.flush(); out.append(to_dict(row))
    await session.commit(); return out

@router.post("/replay/{conversation_id}")
async def replay(conversation_id: str, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("experiment:write"))):
    conv=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not conv: raise HTTPException(404,"conversation not found")
    rows=(await session.execute(select(ConversationEventRow).where(ConversationEventRow.conversation_id==conversation_id,ConversationEventRow.tenant_id==p.tenant_id).order_by(ConversationEventRow.sequence_no))).scalars().all()
    before=(await session.scalar(select(func.count()).select_from(UsageLedger).where(UsageLedger.run_id==conversation_id))) or 0
    result=exact_replay([to_dict(x) for x in rows])
    after=(await session.scalar(select(func.count()).select_from(UsageLedger).where(UsageLedger.run_id==conversation_id))) or 0
    result["usage_ledger_delta"]=after-before
    return result

@router.post("/promotions")
async def promote(body: PromotionRequest, session: AsyncSession=Depends(get_session), p: Principal=Depends(require("promotion:approve"))):
    hard=dict(body.hard_constraints); hard.setdefault("passed",False); hard.setdefault("grounding_minimum",.9)
    base={**body.baseline_scores,"composite":weighted_score(body.baseline_scores)}
    cand={**body.candidate_scores,"composite":weighted_score(body.candidate_scores)}
    gates=promotion_gate(base,cand,hard,body.coverage)
    decision="approve" if body.approve and gates["passed"] else "reject" if not gates["passed"] else "hold"
    row=PromotionDecisionRow(tenant_id=p.tenant_id,candidate_id=body.candidate_id,gates_json=gates,decision=decision,approver_id=p.subject if decision=="approve" else None,reason="all gates passed" if gates["passed"] else ";".join(gates["failures"]))
    session.add(row)
    if decision=="approve":
        c=await session.scalar(select(Candidate).where(Candidate.id==body.candidate_id,Candidate.tenant_id==p.tenant_id))
        if c:
            pv=await session.get(PolicyVersion,c.policy_version_id)
            if pv: pv.status="signed"; pv.signature=sign(pv.document_json,settings.policy_signing_key)
    await session.commit(); return to_dict(row)

@router.get("/audit")
async def audits(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    if "*" not in p.permissions and "audit:read" not in p.permissions: raise HTTPException(403,"audit permission required")
    rows=(await session.execute(select(AuditEvent).where(AuditEvent.tenant_id==p.tenant_id).order_by(AuditEvent.created_at.desc()).limit(200))).scalars().all()
    return [to_dict(x) for x in rows]

@router.get("/usage")
async def usage(session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    rows=(await session.execute(select(UsageLedger).where(UsageLedger.tenant_id==p.tenant_id).order_by(UsageLedger.created_at.desc()).limit(500))).scalars().all()
    return [to_dict(x) for x in rows]
