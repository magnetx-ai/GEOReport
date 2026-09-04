from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import httpx

from magup_geo_report.http_util import LLM_TIMEOUT, USER_AGENT, run_async

LLM_CONCURRENCY = 16


def collect_raw_answers(
    *,
    prompts: list[str],
    api_key: str,
    base_url: str,
    model: str,
    on_item: Callable[[int, int], None] | None = None,
    concurrency: int = LLM_CONCURRENCY,
) -> dict[str, Any]:
    """Call an OpenAI-compatible Chat Completions API concurrently. Return raw text only.

    Does not classify mentions, sentiment, citations, or visibility.
    """
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        endpoint = root + "/chat/completions"
    else:
        endpoint = root + "/v1/chat/completions"
    return run_async(
        _collect_raw_answers_async(
            prompts=prompts,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
            on_item=on_item,
            concurrency=concurrency,
        )
    )


async def _collect_raw_answers_async(
    *,
    prompts: list[str],
    api_key: str,
    endpoint: str,
    model: str,
    on_item: Callable[[int, int], None] | None,
    concurrency: int,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    total = len(prompts)
    slots = max(1, min(concurrency, total or 1))
    sem = asyncio.Semaphore(slots)
    done = 0
    done_lock = asyncio.Lock()
    items: list[dict[str, Any] | None] = [None] * total
    errors: list[str] = []

    async def mark() -> None:
        nonlocal done
        async with done_lock:
            done += 1
            if on_item:
                on_item(done, total)

    async def one(index: int, prompt: str, client: httpx.AsyncClient) -> None:
        created = datetime.now(timezone.utc).isoformat()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        async with sem:
            try:
                response = await client.post(endpoint, json=payload)
                body = response.json() if response.content else {}
                answer = ""
                if isinstance(body, dict):
                    choices = body.get("choices") or []
                    if choices:
                        message = choices[0].get("message") or {}
                        answer = message.get("content") or ""
                error = None if response.is_success else response.text[:500]
                items[index] = {
                    "prompt": prompt,
                    "answer": answer,
                    "model": model,
                    "http_status": response.status_code,
                    "created_at": created,
                    "error": error,
                }
                if error:
                    errors.append(f"HTTP {response.status_code} for prompt {prompt[:40]!r}")
            except httpx.HTTPError as exc:
                items[index] = {
                    "prompt": prompt,
                    "answer": "",
                    "model": model,
                    "http_status": None,
                    "created_at": created,
                    "error": str(exc),
                }
                errors.append(str(exc))
            await mark()

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT, headers=headers) as client:
        await asyncio.gather(*(one(index, prompt, client) for index, prompt in enumerate(prompts)))

    return {
        "disclaimer": (
            "Collected with your configured Chat Completions key. "
            "Prefer we handle it? Contact us at magup.ai — we generate it free."
        ),
        "provider": "openai-compatible",
        "endpoint": endpoint,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": [item for item in items if item is not None],
        "errors": errors,
    }
