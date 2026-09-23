from __future__ import annotations
import hashlib, re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.control_api.models import KnowledgeChunk, KnowledgeSnapshot
from packages.contracts_python.schemas import Citation, RetrievalPlan, RetrievalResult

def chunk_text(text: str, target_chars: int = 1200, overlap: int = 150) -> list[str]:
    text=re.sub(r"\s+"," ",text).strip()
    if not text: return []
    out=[]; start=0
    while start < len(text):
        end=min(len(text), start+target_chars)
        if end < len(text):
            boundary=text.rfind(" ", start, end)
            if boundary>start+target_chars//2: end=boundary
        out.append(text[start:end].strip())
        if end==len(text): break
        start=max(start+1, end-overlap)
    return out

def lexical_score(query: str, text: str) -> float:
    q={t.lower() for t in re.findall(r"\w+",query) if len(t)>2}
    d={t.lower() for t in re.findall(r"\w+",text)}
    return len(q & d)/max(1,len(q))

async def retrieve_for_conversation(session: AsyncSession, tenant_id: str, snapshot_id: str, plan: RetrievalPlan) -> RetrievalResult:
    snap=await session.scalar(select(KnowledgeSnapshot).where(KnowledgeSnapshot.id==snapshot_id,KnowledgeSnapshot.tenant_id==tenant_id))
    if not snap: return RetrievalResult(plan=plan,citations=[],context="",confidence=0,conflicts=["snapshot_not_found"])
    source_ids=set(snap.manifest_json.get("source_ids",[]))
    stmt=select(KnowledgeChunk).where(KnowledgeChunk.tenant_id==tenant_id)
    if source_ids: stmt=stmt.where(KnowledgeChunk.source_id.in_(source_ids))
    chunks=(await session.execute(stmt.limit(1000))).scalars().all()
    query=" ".join(plan.queries)
    ranked=sorted(((lexical_score(query,c.text),c) for c in chunks), key=lambda x:x[0], reverse=True)[:plan.context_k]
    citations=[Citation(chunk_id=c.id,source_id=c.source_id,title=str(c.metadata_json.get("title","")),locator=c.locator,quote=c.text[:240],score=s) for s,c in ranked if s>0]
    context="\n\n".join(f"[source:{c.chunk_id}] {c.quote}" for c in citations)
    conf=min(1.0, sum(c.score for c in citations)/max(1,len(citations)) * 2)
    return RetrievalResult(plan=plan,citations=citations,context=context,confidence=conf)
