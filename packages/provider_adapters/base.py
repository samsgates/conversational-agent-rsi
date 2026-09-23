from __future__ import annotations
from collections.abc import AsyncIterator
from typing import Protocol, Any
from packages.contracts_python.schemas import (
    ConversationAction, EvaluationResult, ModelRequest, ModelResponse,
    PolicyCandidate, RetrievalPlan, RetrievalResult,
)

class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[str]: ...

class Retriever(Protocol):
    async def retrieve(self, plan: RetrievalPlan, authz: dict[str, Any]) -> RetrievalResult: ...

class Evaluator(Protocol):
    async def evaluate(self, target: dict[str, Any], context: dict[str, Any]) -> EvaluationResult: ...

class CounterpartySimulator(Protocol):
    async def respond(self, world: dict[str, Any], action: ConversationAction) -> dict[str, Any]: ...

class PolicyOptimizer(Protocol):
    async def propose(self, evidence: dict[str, Any], space: dict[str, Any]) -> list[PolicyCandidate]: ...

class ToolAdapter(Protocol):
    async def plan(self, call: dict[str, Any], authz: dict[str, Any]) -> dict[str, Any]: ...
    async def execute(self, approved_plan: dict[str, Any]) -> dict[str, Any]: ...
