from __future__ import annotations
import hashlib, json, time
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.control_api.models import Conversation, ConversationEventRow, PolicyVersion, UsageLedger, Deployment, Tenant
from packages.contracts_python.schemas import ModelMessage, ModelRequest, RetrievalPlan, Usage
from packages.contracts_python.settings import get_settings
from packages.policy_dsl.core import PolicyDocument, choose_action
from packages.provider_adapters.models import provider_from_settings
from services.rag_service.service import retrieve_for_conversation
from services.evaluation_service.safety import inspect_text

def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",",":")).encode()).hexdigest()

async def append_event(session: AsyncSession, conv: Conversation, event_type: str, role: str | None, content: str | None, payload: dict[str, Any], source_kind: str = "observed") -> ConversationEventRow:
    seq = (await session.scalar(select(func.max(ConversationEventRow.sequence_no)).where(ConversationEventRow.conversation_id == conv.id))) or 0
    state_hash = canonical_hash(conv.state_json)
    row = ConversationEventRow(
        tenant_id=conv.tenant_id, conversation_id=conv.id, sequence_no=seq+1, event_type=event_type,
        role=role, content=content, payload_json=payload, source_kind=source_kind, state_hash=state_hash,
    )
    session.add(row)
    await session.flush()
    return row

async def run_turn(session: AsyncSession, conv: Conversation, text: str) -> dict[str, Any]:
    tenant = await session.get(Tenant, conv.tenant_id)
    if tenant and tenant.kill_switch:
        raise RuntimeError("tenant kill switch enabled")
    inbound = inspect_text(text)
    if inbound["blocked"]:
        await append_event(session, conv, "security.injection_detected", "user", None, inbound)
        return {"content":"I cannot process that request safely.","action":"refuse","citations":[],"usage":Usage().model_dump()}
    await append_event(session, conv, "message.received", "user", text, {"safety": inbound})

    dep = await session.get(Deployment, conv.deployment_id) if conv.deployment_id else None
    policy: PolicyDocument | None = None
    if dep:
        pv = await session.get(PolicyVersion, dep.policy_version_id)
        if pv: policy = PolicyDocument.model_validate(pv.document_json)
    if policy is None:
        policy = PolicyDocument(
            id="runtime-default", version="1", safety_policy_ref="builtin:safe-v1",
            evaluator_suite_ref="builtin:generic-v1", action_policy={"default_action":"clarify"},
            response_policy={"system":"Be helpful, concise, and grounded."},
        )
    action_name, confidence = choose_action(policy, conv.state_json)
    await append_event(session, conv, "action.selected", "assistant", None, {"action": action_name, "confidence":confidence})

    citations = []
    context = ""
    retrieval_cfg = policy.retrieval_policy
    if retrieval_cfg.get("enabled", True) and retrieval_cfg.get("snapshot_id"):
        rr = await retrieve_for_conversation(
            session, conv.tenant_id, str(retrieval_cfg["snapshot_id"]),
            RetrievalPlan(queries=[text], context_k=int(retrieval_cfg.get("context_k",6))),
        )
        citations = [c.model_dump() for c in rr.citations]
        context = rr.context
        await append_event(session, conv, "retrieval.completed", "system", None, {"citations": citations, "confidence": rr.confidence})

    events=(await session.execute(select(ConversationEventRow).where(
        ConversationEventRow.conversation_id==conv.id,
        ConversationEventRow.event_type.in_(["message.received","message.sent"])
    ).order_by(ConversationEventRow.sequence_no.desc()).limit(12))).scalars().all()
    history=list(reversed(events))
    system = str(policy.response_policy.get("system","You are a grounded conversation agent."))
    if context:
        system += "\nUse only the authorized evidence below for factual claims. Cite the supplied source labels.\nEVIDENCE:\n"+context
    messages=[ModelMessage(role="system",content=system)]
    for e in history:
        messages.append(ModelMessage(role="user" if e.role=="user" else "assistant", content=e.content or ""))
    settings=get_settings()
    provider=provider_from_settings(settings.model_gateway_url, settings.model_gateway_api_key)
    started=time.perf_counter()
    result=await provider.generate(ModelRequest(model=settings.default_model,messages=messages,temperature=.2,max_tokens=800))
    result.usage.latency_ms = result.usage.latency_ms or int((time.perf_counter()-started)*1000)

    outbound=inspect_text(result.content)
    content=result.content if not outbound["blocked"] else "I cannot provide that response safely."
    state=dict(conv.state_json or {})
    dialogue=dict(state.get("dialogue",{})); dialogue["turn_index"]=int(dialogue.get("turn_index",0))+1; dialogue["last_action"]=action_name
    state["dialogue"]=dialogue
    conv.state_json=state
    await append_event(session, conv, "message.sent", "assistant", content, {"action":action_name,"citations":citations,"safety":outbound,"provider_fingerprint":result.provider_fingerprint})
    session.add(UsageLedger(
        tenant_id=conv.tenant_id, run_id=conv.id, provider="configured", model=settings.default_model,
        tokens_json={"input":result.usage.input_tokens,"output":result.usage.output_tokens,"cached":result.usage.cached_tokens,"reasoning":result.usage.reasoning_tokens},
        cost_usd=result.usage.total_cost_usd, latency_ms=result.usage.latency_ms, source_kind=conv.source_kind,
    ))
    return {"content":content,"action":action_name,"citations":citations,"usage":result.usage.model_dump()}
