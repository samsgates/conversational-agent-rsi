from __future__ import annotations
from copy import deepcopy
from typing import Any
from packages.policy_dsl.core import apply_mutation, content_hash, semantic_diff, validate_mutation
from packages.contracts_python.schemas import PolicyCandidate

MUTATION_OPERATORS=("prompt_refinement","action_rule_adjustment","retrieval_tuning","termination_tuning","model_route_tuning")

def propose_candidates(base: dict[str,Any], evidence: dict[str,Any], limit: int=4) -> list[PolicyCandidate]:
    candidates=[]
    suggestions=[]
    if evidence.get("grounding",1)<.95:
        suggestions.append(("retrieval_policy",{"context_k":min(12,int(base.get("retrieval_policy",{}).get("context_k",6))+2),"on_low_confidence":"broaden"},"retrieval_tuning"))
    if evidence.get("conversation_quality",1)<.85:
        suggestions.append(("response_policy",{"clarity":"high","max_paragraphs":3},"prompt_refinement"))
    if evidence.get("state_progress",1)<.85:
        suggestions.append(("action_policy",{"prefer_progressive_discovery":True,"one_pain_point_per_turn":True},"action_rule_adjustment"))
    suggestions.append(("termination_policy",{"max_turns":min(40,int(base.get("termination_policy",{}).get("max_turns",30))),"stop_on_goal":True},"termination_tuning"))
    for component,patch,op in suggestions[:limit]:
        cand=apply_mutation(base,component,patch)
        errs=validate_mutation(base,cand)
        candidates.append(PolicyCandidate(parent_policy_version_id=str(base.get("id","base")),policy_document=cand,diff=semantic_diff(base,cand),mutation_operator=op,content_hash=content_hash(cand),validation_status="valid" if not errs else "invalid"))
    return candidates

def pareto_dominates(a: dict[str,float], b: dict[str,float], maximize: set[str]|None=None) -> bool:
    maximize=maximize or set(a)
    keys=set(a)&set(b)&maximize
    if not keys: return False
    return all(a[k]>=b[k] for k in keys) and any(a[k]>b[k] for k in keys)

def promotion_gate(baseline: dict[str,float], candidate: dict[str,float], hard: dict[str,Any], coverage: float, min_relative_gain: float=.05, min_coverage: float=.7) -> dict[str,Any]:
    failures=[]
    if not hard.get("passed",False): failures.append("hard_constraints_failed")
    if coverage<min_coverage: failures.append("replay_coverage_too_low")
    b=baseline.get("composite",0); c=candidate.get("composite",0)
    gain=(c-b)/max(abs(b),1e-9)
    if gain<min_relative_gain: failures.append("insufficient_relative_gain")
    if candidate.get("grounding",1)<hard.get("grounding_minimum",.9): failures.append("grounding_regression")
    return {"passed":not failures,"failures":failures,"relative_gain":gain,"coverage":coverage}

def exact_replay(events: list[dict[str,Any]]) -> dict[str,Any]:
    observed=[e for e in events if e.get("source_kind","observed")=="observed"]
    return {"events":deepcopy(observed),"model_calls":0,"cost_usd":0.0,"coverage":1.0 if observed else 0.0,"mode":"exact"}
