from __future__ import annotations
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from packages.contracts_python.settings import get_settings
from services.worker_runtime.workflows import DurableOperationWorkflow, execute_operation

async def main():
    client=await Client.connect(get_settings().temporal_address)
    worker=Worker(client,task_queue="rsi-default",workflows=[DurableOperationWorkflow],activities=[execute_operation])
    await worker.run()
if __name__=="__main__": asyncio.run(main())
