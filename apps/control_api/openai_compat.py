from __future__ import annotations
import json, time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.control_api.api_schemas import ChatCompletionRequest, ConversationCreate, MessageCreate
from apps.control_api.auth import Principal, get_principal
from apps.control_api.db import get_session
from apps.control_api.models import Conversation, Deployment
from apps.conversation_runtime.runtime import run_turn

router=APIRouter()

@router.post("/v1/chat/completions")
async def chat(body: ChatCompletionRequest, session: AsyncSession=Depends(get_session), p: Principal=Depends(get_principal)):
    if not body.model.startswith("agent:"):
        raise HTTPException(422,"model must be agent:<deployment_id>")
    deployment_id=body.model.split(":",1)[1]
    dep=await session.scalar(select(Deployment).where(Deployment.id==deployment_id,Deployment.tenant_id==p.tenant_id,Deployment.status=="active"))
    if not dep: raise HTTPException(404,"deployment not found")
    conversation_id=body.metadata.get("conversation_id")
    conv=None
    if conversation_id:
        conv=await session.scalar(select(Conversation).where(Conversation.id==conversation_id,Conversation.tenant_id==p.tenant_id))
    if not conv:
        conv=Conversation(tenant_id=p.tenant_id,project_id=body.metadata.get("project_id","default"),agent_id=dep.agent_id,deployment_id=dep.id,external_user_id=body.metadata.get("external_user_id"),source_kind="observed",state_json={"tenant_id":p.tenant_id,"project_id":body.metadata.get("project_id","default"),"agent_id":dep.agent_id,"conversation_id":"","dialogue":{"turn_index":0,"phase":"opening"},"slots":{"discovered_facts":{},"unresolved_facts":[]}})
        session.add(conv); await session.flush(); conv.state_json={**conv.state_json,"conversation_id":conv.id}
    user=next((m.get("content","") for m in reversed(body.messages) if m.get("role")=="user"),"")
    result=await run_turn(session,conv,user); await session.commit()
    payload={"id":f"chatcmpl-{conv.id}","object":"chat.completion","created":int(time.time()),"model":body.model,"choices":[{"index":0,"message":{"role":"assistant","content":result["content"]},"finish_reason":"stop"}],"usage":{"prompt_tokens":result["usage"]["input_tokens"],"completion_tokens":result["usage"]["output_tokens"],"total_tokens":result["usage"]["input_tokens"]+result["usage"]["output_tokens"]}}
    if not body.stream: return payload
    async def gen():
        chunk={"id":payload["id"],"object":"chat.completion.chunk","created":payload["created"],"model":body.model,"choices":[{"index":0,"delta":{"role":"assistant","content":result["content"]},"finish_reason":None}]}
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(),media_type="text/event-stream",headers={"x-rsi-trace-id":conv.id,"x-rsi-policy-version":dep.policy_version_id})
