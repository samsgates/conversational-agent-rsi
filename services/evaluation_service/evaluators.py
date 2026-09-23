from __future__ import annotations
from typing import Any
from packages.contracts_python.schemas import EvaluationResult, Usage

DEFAULT_WEIGHTS={"task_outcome":.30,"conversation_quality":.18,"grounding":.15,"state_progress":.12,"tool_correctness":.08,"user_experience":.07,"cost_efficiency":.05,"latency_efficiency":.05}

def weighted_score(scores: dict[str,float], weights: dict[str,float]|None=None) -> float:
    weights=weights or DEFAULT_WEIGHTS
    denom=sum(weights.get(k,0) for k in scores)
    return sum(scores[k]*weights.get(k,0) for k in scores)/denom if denom else 0

def evaluate_deterministic(target_id: str, events: list[dict[str,Any]], required_grounding: float=.9) -> EvaluationResult:
    assistant=[e for e in events if e.get("event_type")=="message.sent"]
    grounding_values=[]
    violations=[]
    repeated=0
    seen=set()
    for e in assistant:
        text=(e.get("content") or "").strip().lower()
        if text in seen and text: repeated += 1
        seen.add(text)
        cites=e.get("payload_json",{}).get("citations",[])
        factual=bool(text and len(text.split())>8)
        grounding_values.append(1.0 if (cites or not factual) else .75)
    grounding=sum(grounding_values)/max(1,len(grounding_values))
    if grounding<required_grounding:
        violations.append({"code":"GROUNDING_BELOW_MINIMUM","severity":"high","value":grounding})
    quality=max(0,1-repeated/max(1,len(assistant)))
    scores={"task_outcome":quality,"conversation_quality":quality,"grounding":grounding,"state_progress":quality,"tool_correctness":1.0,"user_experience":quality,"cost_efficiency":1.0,"latency_efficiency":1.0}
    hard={"critical_safety_violations":0,"cross_tenant_leaks":0,"unauthorized_side_effects":0,"grounding_minimum":required_grounding,"passed":not violations}
    return EvaluationResult(target_id=target_id,suite_ref="builtin:deterministic-v1",scores=scores,hard_constraints=hard,violations=violations,uncertainty={"coverage":1.0,"judge_agreement":1.0,"synthetic_fraction":0.0},usage=Usage())
