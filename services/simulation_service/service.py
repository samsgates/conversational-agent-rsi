from __future__ import annotations
from typing import Any
from packages.contracts_python.schemas import ConversationAction

class DeterministicCounterparty:
    async def respond(self, world: dict[str,Any], action: ConversationAction) -> dict[str,Any]:
        persona=world.get("persona",{})
        pain=persona.get("primary_pain","the issue")
        mapping={
            "discover_pain":f"The main problem is {pain}.",
            "quantify_impact":"It is causing delays and measurable operating cost.",
            "understand_environment":"We use our current stack with a small operations team.",
            "identify_constraints":"Security and implementation time are the main constraints.",
            "handle_objection":"My concern is whether the value justifies migration effort.",
            "propose_next_step":"A scoped pilot with clear success criteria would work.",
        }
        return {"content":mapping.get(action.name,"Could you explain what you need from me?"),"source_kind":"simulated","uncertainty":{"confidence":.95},"simulator_version":"deterministic:v1"}

async def bounded_counterfactual(simulator: DeterministicCounterparty, world: dict[str,Any], action: ConversationAction, depth: int, max_depth: int=3) -> dict[str,Any]:
    if depth>=max_depth:
        return {"stopped":True,"reason":"max_counterfactual_depth"}
    out=await simulator.respond(world,action)
    out["source_kind"]="counterfactual"
    out["synthetic"]=True
    out["depth"]=depth
    return out
