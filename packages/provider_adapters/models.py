from __future__ import annotations
import hashlib, time
from collections.abc import AsyncIterator
import httpx
from packages.contracts_python.schemas import ModelRequest, ModelResponse, Usage

class DeterministicModelProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        last = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        content = f"I understand. {last[:350]}".strip()
        return ModelResponse(
            content=content,
            usage=Usage(input_tokens=sum(len(m.content.split()) for m in request.messages), output_tokens=len(content.split())),
            provider_fingerprint="fake:deterministic:v1",
        )
    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        for token in response.content.split(" "):
            yield token + " "

class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
    async def generate(self, request: ModelRequest) -> ModelResponse:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": False,
                },
            )
            r.raise_for_status()
            data = r.json()
        u = data.get("usage", {})
        return ModelResponse(
            content=data["choices"][0]["message"]["content"],
            usage=Usage(
                input_tokens=u.get("prompt_tokens", 0),
                output_tokens=u.get("completion_tokens", 0),
                cached_tokens=u.get("prompt_tokens_details", {}).get("cached_tokens", 0),
                reasoning_tokens=u.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
                latency_ms=int((time.perf_counter()-started)*1000),
            ),
            provider_fingerprint=r.headers.get("x-model-fingerprint", "openai-compatible"),
        )
    async def stream(self, request: ModelRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        yield response.content

def provider_from_settings(base_url: str, api_key: str):
    return OpenAICompatibleProvider(base_url, api_key) if base_url else DeterministicModelProvider()
