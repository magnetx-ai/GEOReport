from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar

import httpx

USER_AGENT = "MagUp-GEO-Report/0.1 (+https://magup.ai)"
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
LLM_TIMEOUT = httpx.Timeout(90.0, connect=10.0)
ANSWER_TIMEOUT = httpx.Timeout(130.0, connect=15.0)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    holder: dict[str, Any] = {}

    def worker() -> None:
        try:
            holder["value"] = asyncio.run(coro)
        except Exception as exc:  # noqa: BLE001
            holder["error"] = exc

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    if "error" in holder:
        raise holder["error"]
    return holder["value"]


@dataclass
class Fetched:
    url: str
    final_url: str
    status: int | None
    ok: bool
    body: str
    content_type: str
    error: str | None = None


def get_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
        timeout=TIMEOUT,
    )


def fetch_text(client: httpx.Client, url: str) -> Fetched:
    try:
        response = client.get(url)
        content_type = response.headers.get("content-type", "")
        # Avoid decoding huge binaries as text
        if len(response.content) > 2_000_000:
            return Fetched(
                url=url,
                final_url=str(response.url),
                status=response.status_code,
                ok=False,
                body="",
                content_type=content_type,
                error="response larger than 2MB, skipped",
            )
        text = response.text if "charset" in content_type.lower() or content_type.startswith("text/") or "json" in content_type or "xml" in content_type or "html" in content_type or not content_type else ""
        if not text and response.content:
            try:
                text = response.content.decode("utf-8", errors="replace")
            except Exception:
                text = ""
        return Fetched(
            url=url,
            final_url=str(response.url),
            status=response.status_code,
            ok=response.is_success,
            body=text,
            content_type=content_type,
        )
    except httpx.HTTPError as exc:
        return Fetched(
            url=url,
            final_url=url,
            status=None,
            ok=False,
            body="",
            content_type="",
            error=str(exc),
        )
