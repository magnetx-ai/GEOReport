from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from magup_geo_report.http_util import ANSWER_TIMEOUT, USER_AGENT, run_async

DATAFORSEO_BASE = "https://api.dataforseo.com"
# magup_v3 DataForSEO lane; Live cap is 30 in-flight per platform.
DFS_CONCURRENCY = 25
PROMPT_MAX = 500

# Live LLM Responses (faster, higher cost) — not Standard Queue / llm_scraper.
PLATFORM_LIVE = {
    "chatgpt": {
        "path": "/v3/ai_optimization/chat_gpt/llm_responses/live",
        "model": "gpt-4.1-mini",
        "label": "ChatGPT",
    },
    "gemini": {
        "path": "/v3/ai_optimization/gemini/llm_responses/live",
        "model": "gemini-2.5-flash",
        "label": "Gemini",
    },
    "claude": {
        "path": "/v3/ai_optimization/claude/llm_responses/live",
        "model": "claude-sonnet-4-5",
        "label": "Claude",
    },
    "perplexity": {
        "path": "/v3/ai_optimization/perplexity/llm_responses/live",
        "model": "sonar",
        "label": "Perplexity",
    },
}

LANG_TO_ISO = {
    "zh-hans": "CN",
    "zh-cn": "CN",
    "zh": "CN",
    "zh-hant": "TW",
    "zh-tw": "TW",
    "en": "US",
    "ja": "JP",
    "fr": "FR",
    "pt-br": "BR",
    "pt-pt": "PT",
    "ar": "SA",
}


def _iso_country(language: str) -> str:
    key = (language or "en").strip().lower().replace("_", "-")
    if key in LANG_TO_ISO:
        return LANG_TO_ISO[key]
    primary = key.split("-")[0]
    return LANG_TO_ISO.get(primary, "US")


def _texts(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_texts(item))
        return parts
    if isinstance(value, dict):
        parts = []
        for key in ("markdown", "text", "content", "message", "response", "answer"):
            parts.extend(_texts(value.get(key)))
        for key in ("sections", "items"):
            parts.extend(_texts(value.get(key)))
        return parts
    return []


def _result_row(body: Any) -> dict[str, Any]:
    if isinstance(body, dict):
        tasks = body.get("tasks") or []
        if tasks and isinstance(tasks[0], dict):
            rows = tasks[0].get("result") or []
            if rows and isinstance(rows[0], dict):
                return rows[0]
    return {}


def extract_answer_text(body: Any) -> str:
    parts = _texts(_result_row(body))
    return "\n\n".join(parts).strip()


def _source_host(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def extract_sources(body: Any) -> list[dict[str, str]]:
    """Pull citation lists from LLM Responses (annotations) and scraper (sources).

    ChatGPT often also inlines markdown URLs in the answer text. Gemini / Claude /
    Perplexity typically cite as [n] and put the real URLs only in annotations
    (on the message item and/or each text section).
    """
    result = _result_row(body)
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(raw: Any, usage: str) -> None:
        if not isinstance(raw, dict):
            return
        url = str(raw.get("url") or raw.get("uri") or raw.get("link") or "").strip()
        if not url or not url.lower().startswith(("http://", "https://")):
            return
        key = url.lower().rstrip("/")
        if key in seen:
            return
        seen.add(key)
        title = str(raw.get("title") or raw.get("source_name") or "").strip()
        domain = str(raw.get("domain") or "").strip() or _source_host(url)
        out.append({"url": url, "title": title, "domain": domain, "usage": usage})

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        for key in ("annotations", "sources", "citations"):
            rows = node.get(key)
            if isinstance(rows, list):
                for row in rows:
                    add(row, "applied")
        searched = node.get("search_results")
        if isinstance(searched, list):
            for row in searched:
                add(row, "searched")
        for key in ("items", "sections"):
            walk(node.get(key))

    walk(result)
    return out


def _task_error(body: Any) -> str | None:
    if not isinstance(body, dict):
        return "empty DataForSEO response"
    code = body.get("status_code")
    if code and code != 20000:
        return str(body.get("status_message") or f"DataForSEO status {code}")
    tasks = body.get("tasks") or []
    if not tasks or not isinstance(tasks[0], dict):
        return "DataForSEO task missing"
    task = tasks[0]
    task_code = task.get("status_code")
    if task_code and task_code != 20000:
        return str(task.get("status_message") or f"DataForSEO task status {task_code}")
    return None


_GEMINI_FALLBACKS = ("gemini-2.5-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite")


async def _resolve_gemini_model(client: httpx.AsyncClient, auth: tuple[str, str], preferred: str) -> str:
    """Pick a currently listed Gemini model. gemini-2.0-flash is no longer accepted."""
    try:
        response = await client.get(DATAFORSEO_BASE + "/v3/ai_optimization/gemini/llm_responses/models", auth=auth)
        body = response.json() if response.content else {}
    except (httpx.HTTPError, ValueError):
        return preferred
    tasks = body.get("tasks") or []
    rows = tasks[0].get("result") if tasks and isinstance(tasks[0], dict) else []
    names: list[str] = []
    web: list[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("model_name") or "").strip()
        if not name:
            continue
        names.append(name)
        if row.get("web_search_supported"):
            web.append(name)
    if preferred in names:
        return preferred
    pool = web or names
    for cand in _GEMINI_FALLBACKS:
        if cand in pool:
            return cand
    return pool[0] if pool else preferred


def _payload(platform: str, prompt: str, language: str, model: str | None = None) -> dict[str, Any]:
    spec = PLATFORM_LIVE[platform]
    iso = _iso_country(language)
    body: dict[str, Any] = {
        "user_prompt": prompt[:PROMPT_MAX],
        "model_name": model or spec["model"],
        "max_output_tokens": 2000,
    }
    if platform == "chatgpt":
        body.update({
            "web_search": True,
            "force_web_search": True,
            "web_search_country_iso_code": iso,
        })
    elif platform == "claude":
        body.update({
            "web_search": True,
            "force_web_search": True,
            "web_search_country_iso_code": iso,
        })
    elif platform == "gemini":
        body["web_search"] = True
    elif platform == "perplexity":
        body["web_search_country_iso_code"] = iso
    return body


def collect_dataforseo_answers(
    *,
    prompts: list[str],
    platforms: list[str],
    login: str,
    password: str,
    language: str = "en",
    on_item: Callable[[int, int], None] | None = None,
    concurrency: int = DFS_CONCURRENCY,
) -> dict[str, Any]:
    """Fetch prompt×platform answers via DataForSEO LLM Responses live, concurrently.

    Matches magup_v3 askMany: platforms run in parallel; each platform uses a
    concurrency pool. Uses live endpoints (fastest), not Standard Queue.
    """
    selected = [code for code in platforms if code in PLATFORM_LIVE] or list(PLATFORM_LIVE)
    return run_async(
        _collect_async(
            prompts=prompts,
            platforms=selected,
            login=login,
            password=password,
            language=language,
            on_item=on_item,
            concurrency=concurrency,
        )
    )


async def _collect_async(
    *,
    prompts: list[str],
    platforms: list[str],
    login: str,
    password: str,
    language: str,
    on_item: Callable[[int, int], None] | None,
    concurrency: int,
) -> dict[str, Any]:
    jobs = [
        {"prompt_index": p_i, "prompt": prompt, "platform": platform, "platform_index": pl_i}
        for p_i, prompt in enumerate(prompts)
        for pl_i, platform in enumerate(platforms)
    ]
    total = len(jobs)
    slots = max(1, min(concurrency, 30))
    done = 0
    done_lock = asyncio.Lock()
    items: list[dict[str, Any] | None] = [None] * total
    errors: list[str] = []
    resolved_models: dict[str, str] = {}

    async def mark() -> None:
        nonlocal done
        async with done_lock:
            done += 1
            if on_item:
                on_item(done, total)

    async def one(job_index: int, job: dict[str, Any], client: httpx.AsyncClient, sem: asyncio.Semaphore) -> None:
        platform = job["platform"]
        spec = PLATFORM_LIVE[platform]
        model = resolved_models.get(platform) or spec["model"]
        endpoint = DATAFORSEO_BASE + spec["path"]
        created = datetime.now(timezone.utc).isoformat()
        payload = _payload(platform, job["prompt"], language, model=model)
        async with sem:
            try:
                response = await client.post(endpoint, json=[payload], auth=(login, password))
                try:
                    body: Any = response.json() if response.content else {}
                except ValueError:
                    body = {}
                api_error = None if response.is_success else response.text[:500]
                if response.is_success:
                    api_error = _task_error(body)
                answer = extract_answer_text(body) if response.is_success else ""
                sources = extract_sources(body) if response.is_success else []
                items[job_index] = {
                    "prompt": job["prompt"],
                    "prompt_index": job["prompt_index"] + 1,
                    "platform": platform,
                    "model": model,
                    "answer": answer,
                    "sources": sources,
                    "http_status": response.status_code,
                    "created_at": created,
                    "endpoint": spec["path"],
                    "error": api_error,
                }
                if api_error:
                    errors.append(f"{spec['label']} HTTP {response.status_code}: {api_error}")
            except httpx.HTTPError as exc:
                items[job_index] = {
                    "prompt": job["prompt"],
                    "prompt_index": job["prompt_index"] + 1,
                    "platform": platform,
                    "model": model,
                    "answer": "",
                    "sources": [],
                    "http_status": None,
                    "created_at": created,
                    "endpoint": spec["path"],
                    "error": str(exc),
                }
                errors.append(str(exc))
            await mark()

    lanes: dict[str, list[tuple[int, dict[str, Any]]]] = {code: [] for code in platforms}
    for index, job in enumerate(jobs):
        lanes[job["platform"]].append((index, job))

    async with httpx.AsyncClient(timeout=ANSWER_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        for code in platforms:
            if code not in PLATFORM_LIVE:
                continue
            preferred = PLATFORM_LIVE[code]["model"]
            if code == "gemini":
                preferred = await _resolve_gemini_model(client, (login, password), preferred)
            resolved_models[code] = preferred

        async def lane(platform: str, lane_jobs: list[tuple[int, dict[str, Any]]]) -> None:
            sem = asyncio.Semaphore(max(1, min(slots, len(lane_jobs) or 1)))
            await asyncio.gather(*(one(index, job, client, sem) for index, job in lane_jobs))

        await asyncio.gather(*(lane(platform, lane_jobs) for platform, lane_jobs in lanes.items() if lane_jobs))

    ordered = [item for item in items if item is not None]
    ordered.sort(key=lambda row: (row.get("prompt_index") or 0, platforms.index(row["platform"]) if row.get("platform") in platforms else 99))
    return {
        "disclaimer": (
            "Collected with DataForSEO LLM Responses live (fastest method; not Standard Queue). "
            "Raw answers only. Prefer we handle it? Contact us at magup.ai — we generate it free."
        ),
        "provider": "dataforseo",
        "capture_method": "llm_responses_live",
        "platforms": platforms,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": ordered,
        "errors": errors,
    }
