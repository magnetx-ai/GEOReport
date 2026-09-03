from __future__ import annotations

from dataclasses import dataclass

import httpx

USER_AGENT = (
    "MagUp-GEO-Community-Report/0.1 "
    "(+https://magup.ai; community hygiene check, not production crawler)"
)
TIMEOUT = httpx.Timeout(20.0, connect=10.0)


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
