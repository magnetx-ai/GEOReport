from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from magup_geo_report.http_util import TIMEOUT, USER_AGENT

DATAFORSEO_SERP = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"


def collect_search_raw(
    *,
    login: str,
    password: str,
    domain: str,
) -> dict[str, Any]:
    """One public DataForSEO live SERP call using the caller's credentials."""
    keyword = domain
    payload = [
        {
            "keyword": keyword,
            "location_code": 2840,
            "language_code": "en",
            "depth": 10,
        }
    ]
    try:
        with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
            response = client.post(
                DATAFORSEO_SERP,
                json=payload,
                auth=(login, password),
            )
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = {"raw_text": response.text[:4000]}
            return {
                "disclaimer": (
                    "Collected with your configured DataForSEO credentials. "
                    "Prefer we handle it? Contact us at magup.ai — we generate it free."
                ),
                "endpoint": DATAFORSEO_SERP,
                "keyword": keyword,
                "http_status": response.status_code,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "response": body,
            }
    except httpx.HTTPError as exc:
        return {
            "disclaimer": "Raw DataForSEO call failed. No MagUp interpretation is applied.",
            "endpoint": DATAFORSEO_SERP,
            "keyword": keyword,
            "http_status": None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
            "response": None,
        }
