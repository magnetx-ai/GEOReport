from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from magup_geo_report.http_util import TIMEOUT, USER_AGENT


def collect_raw_answers(
    *,
    prompts: list[str],
    api_key: str,
    base_url: str,
    model: str,
) -> dict[str, Any]:
    """Call an OpenAI-compatible Chat Completions API. Return raw text only.

    Does not classify mentions, sentiment, citations, or visibility.
    """
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        endpoint = root + "/chat/completions"
    else:
        endpoint = root + "/v1/chat/completions"

    items: list[dict[str, Any]] = []
    errors: list[str] = []
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }

    with httpx.Client(timeout=TIMEOUT, headers=headers) as client:
        for prompt in prompts:
            created = datetime.now(timezone.utc).isoformat()
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            try:
                response = client.post(endpoint, json=payload)
                body = response.json() if response.content else {}
                answer = ""
                if isinstance(body, dict):
                    choices = body.get("choices") or []
                    if choices:
                        message = choices[0].get("message") or {}
                        answer = message.get("content") or ""
                items.append(
                    {
                        "prompt": prompt,
                        "answer": answer,
                        "model": model,
                        "http_status": response.status_code,
                        "created_at": created,
                        "error": None if response.is_success else response.text[:500],
                    }
                )
                if not response.is_success:
                    errors.append(f"HTTP {response.status_code} for prompt {prompt[:40]!r}")
            except httpx.HTTPError as exc:
                items.append(
                    {
                        "prompt": prompt,
                        "answer": "",
                        "model": model,
                        "http_status": None,
                        "created_at": created,
                        "error": str(exc),
                    }
                )
                errors.append(str(exc))

    return {
        "disclaimer": (
            "Raw Chat Completions dump only. MagUp GEO Community Report does not "
            "compute mention rate, sentiment, citation, or Visibility. "
            "Production analysis remains at magup.ai."
        ),
        "provider": "openai-compatible",
        "endpoint": endpoint,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
        "errors": errors,
    }
