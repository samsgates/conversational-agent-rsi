from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asyncio, json, pathlib, yaml, hashlib
from sqlalchemy import select
from apps.control_api.db import SessionLocal, engine
from apps.control_api.models import Base, Tenant, Project, Agent, PolicyVersion, AgentVersion, Deployment, Scenario
from packages.policy_dsl.core import content_hash, sign
from packages.contracts_python.settings import get_settings
TENANT="00000000-0000-4000-8000-000000000001"
async def main():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        t=await s.get(Tenant,TENANT)
        if not t: s.add(Tenant(id=TENANT,name="Local Demo"))
        p=await s.scalar(select(Project).where(Project.tenant_id==TENANT,Project.name=="Demo"))
        if not p:
            p=Project(tenant_id=TENANT,name="Demo",description="Seed project"); s.add(p); await s.flush()
        a=await s.scalar(select(Agent).where(Agent.tenant_id==TENANT,Agent.name=="Support Agent"))
        if not a:
            a=Agent(tenant_id=TENANT,project_id=p.id,name="Support Agent",domain_pack="generic-support"); s.add(a); await s.flush()
            doc={"id":"support-default","version":"1.0.0","safety_policy_ref":"builtin:safe-v1","evaluator_suite_ref":"builtin:generic-v1","action_policy":{"default_action":"clarify","rules":[{"when":{"phase":"opening"},"action":"clarify","confidence":.8}]},"retrieval_policy":{"enabled":False},"response_policy":{"system":"You are a concise customer support agent. Ask one useful question at a time."},"termination_policy":{"max_turns":30}}
            pv=PolicyVersion(tenant_id=TENANT,agent_id=a.id,version="1.0.0",document_json=doc,content_hash=content_hash(doc),signature=sign(doc,get_settings().policy_signing_key),status="signed"); s.add(pv); await s.flush()
            av=AgentVersion(tenant_id=TENANT,agent_id=a.id,version=1,policy_version_id=pv.id,model_config={"model":"fake/deterministic"},status="ready"); s.add(av); await s.flush()
            s.add(Deployment(tenant_id=TENANT,agent_id=a.id,agent_version_id=av.id,policy_version_id=pv.id,stage="production",traffic_percent=100,status="active"))
        await s.commit()
    print("Seed complete")
if __name__=="__main__": asyncio.run(main())
