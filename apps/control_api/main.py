from __future__ import annotations
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from apps.control_api.db import engine
from apps.control_api.routes import router as api_router
from apps.control_api.openai_compat import router as openai_router
from packages.contracts_python.settings import get_settings

settings=get_settings()
app=FastAPI(title="Conversational-Agent-RSI API",version="0.1.0",openapi_version="3.1.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(api_router)
app.include_router(openai_router)

@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id=request.headers.get("x-trace-id") or str(uuid.uuid4())
    try:
        response=await call_next(request)
    except Exception as exc:
        response=JSONResponse(status_code=500,content={"type":"about:blank","title":"Internal error","status":500,"detail":str(exc) if settings.app_env=="local" else "Internal server error","code":"INTERNAL_ERROR","trace_id":trace_id,"retryable":False})
    response.headers["x-trace-id"]=trace_id
    return response

@app.get("/healthz")
async def healthz(): return {"status":"ok","service":"control-api"}

@app.get("/readyz")
async def readyz():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status":"ready"}
