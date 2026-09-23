from __future__ import annotations
from datetime import timedelta
from temporalio import workflow, activity
from dataclasses import dataclass

@dataclass
class OperationInput:
    operation_id: str
    tenant_id: str
    payload: dict

@activity.defn
async def execute_operation(inp: OperationInput) -> dict:
    return {"operation_id":inp.operation_id,"tenant_id":inp.tenant_id,"status":"completed","payload":inp.payload}

@workflow.defn
class DurableOperationWorkflow:
    @workflow.run
    async def run(self, inp: OperationInput) -> dict:
        return await workflow.execute_activity(
            execute_operation, inp,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=None,
        )
