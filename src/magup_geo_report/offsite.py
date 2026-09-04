"""Off-site channel probes via the caller's DataForSEO credentials.

Matches magup_v3 channel_signals methodology: public search
``brand/domain + site:youtube.com|reddit.com|wikipedia.org``, plus backlinks
summary when the account can access it. Empty results are measured zeros,
not 「本轮未测」.
"""
from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import httpx

from magup_geo_report.http_util import TIMEOUT, USER_AGENT, run_async

DATAFORSEO_SERP = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
DATAFORSEO_BACKLINKS = "https://api.dataforseo.com/v3/backlinks/summary/live"

LANG_LOC = {
    "zh-hans": ("2156", "zh-CN"),
    "zh": ("2156", "zh-CN"),
    "zh-cn": ("2156", "zh-CN"),
    "en": ("2840", "en"),
    "ja": ("2392", "ja"),
    "fr": ("2250", "fr"),
    "pt-br": ("2076", "pt"),
    "pt-pt": ("2620", "pt"),
    "ar": ("2682", "ar"),
}


def _loc(language: str) -> tuple[int, str]:
    key = (language or "en").strip().lower().replace("_", "-")
    if key in LANG_LOC:
        code, lang = LANG_LOC[key]
        return int(code), lang
    primary = key.split("-")[0]
    if primary in LANG_LOC:
        code, lang = LANG_LOC[primary]
        return int(code), lang
    return 2840, "en"


def _host(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _serp_payload(keyword: str, location: int, lang: str) -> dict[str, Any]:
    return {
        "keyword": keyword[:200],
        "location_code": location,
        "language_code": lang,
        "depth": 20,
    }


def _parse_serp(body: Any) -> dict[str, Any]:
    items: list[dict[str, str]] = []
    count = 0
    if not isinstance(body, dict):
        return {"ok": False, "result_count": 0, "items": [], "error": "empty"}
    code = body.get("status_code")
    if code and code != 20000:
        return {"ok": False, "result_count": 0, "items": [], "error": str(body.get("status_message") or code)}
    tasks = body.get("tasks") or []
    if not tasks or not isinstance(tasks[0], dict):
        return {"ok": False, "result_count": 0, "items": [], "error": "no task"}
    task = tasks[0]
    if task.get("status_code") and task.get("status_code") != 20000:
        return {"ok": False, "result_count": 0, "items": [], "error": str(task.get("status_message") or "")}
    rows = task.get("result") or []
    row = rows[0] if rows and isinstance(rows[0], dict) else {}
    try:
        count = int(row.get("se_results_count") or 0)
    except (TypeError, ValueError):
        count = 0
    for item in row.get("items") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        title = str(item.get("title") or "")
        domain = str(item.get("domain") or _host(url))
        if url or title:
            items.append({"url": url, "title": title, "domain": domain})
    if count <= 0:
        count = len(items)
    return {"ok": True, "result_count": count, "items": items, "error": None}


def _youtube_official(items: list[dict[str, str]], brand: str, domain: str) -> bool:
    needles = [n.lower() for n in (brand, domain.split(".")[0] if domain else "") if n]
    for item in items:
        url = (item.get("url") or "").lower()
        title = (item.get("title") or "").lower()
        if "/@" in url or "/channel/" in url or "/c/" in url:
            if any(n and (n in url or n in title) for n in needles):
                return True
        if "youtube.com" in url and any(n and n in title for n in needles):
            if "official" in title or "频道" in title or "channel" in title:
                return True
    return False


def _wiki_exists(items: list[dict[str, str]], brand: str) -> dict[str, Any]:
    brand_l = (brand or "").strip().lower()
    for item in items:
        host = (item.get("domain") or _host(item.get("url") or "")).lower()
        if "wikipedia.org" not in host:
            continue
        title = item.get("title") or ""
        url = item.get("url") or ""
        if brand_l and brand_l not in title.lower() and brand_l not in url.lower():
            # Still a wiki hit for the query; treat as candidate.
            if "/wiki/" not in url.lower():
                continue
        return {"exists": True, "url": url, "title": title}
    return {"exists": False, "url": "", "title": ""}


def _parse_backlinks(body: Any) -> dict[str, Any]:
    empty = {"ok": False, "backlinks": 0, "referring_domains": 0, "rank": 0, "error": "unavailable"}
    if not isinstance(body, dict):
        return empty
    if body.get("status_code") and body.get("status_code") != 20000:
        return {**empty, "error": str(body.get("status_message") or body.get("status_code"))}
    tasks = body.get("tasks") or []
    if not tasks or not isinstance(tasks[0], dict):
        return empty
    task = tasks[0]
    if task.get("status_code") and task.get("status_code") != 20000:
        return {**empty, "error": str(task.get("status_message") or "")}
    rows = task.get("result") or []
    row = rows[0] if rows and isinstance(rows[0], dict) else {}
    try:
        backlinks = int(row.get("backlinks") or 0)
        referring = int(row.get("referring_domains") or 0)
        rank = int(row.get("rank") or 0)
    except (TypeError, ValueError):
        return empty
    return {"ok": True, "backlinks": backlinks, "referring_domains": referring, "rank": rank, "error": None}


async def _post(client: httpx.AsyncClient, url: str, payload: list[dict[str, Any]], auth: tuple[str, str]) -> Any:
    try:
        response = await client.post(url, json=payload, auth=auth)
        try:
            return response.json() if response.content else {}
        except ValueError:
            return {"status_code": response.status_code, "status_message": response.text[:400]}
    except httpx.HTTPError as exc:
        return {"status_code": 0, "status_message": str(exc)}


def collect_offsite_signals(
    *,
    login: str,
    password: str,
    brand: str,
    domain: str,
    language: str = "en",
) -> dict[str, Any]:
    """Concurrent YouTube / Reddit / Wikipedia SERP + backlinks summary."""
    return run_async(
        _collect_async(login=login, password=password, brand=brand, domain=domain, language=language)
    )


async def _collect_async(
    *,
    login: str,
    password: str,
    brand: str,
    domain: str,
    language: str,
) -> dict[str, Any]:
    location, lang = _loc(language)
    brand_q = (brand or domain or "").strip()
    domain_q = (domain or "").strip()
    queries = {
        "youtube": f"{brand_q} site:youtube.com",
        "reddit": f"{brand_q} site:reddit.com",
        "wikipedia": f"{brand_q} site:wikipedia.org",
    }
    auth = (login, password)
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
        yt_task = _post(client, DATAFORSEO_SERP, [_serp_payload(queries["youtube"], location, lang)], auth)
        rd_task = _post(client, DATAFORSEO_SERP, [_serp_payload(queries["reddit"], location, lang)], auth)
        wk_task = _post(client, DATAFORSEO_SERP, [_serp_payload(queries["wikipedia"], 2840, "en")], auth)
        bl_task = _post(
            client,
            DATAFORSEO_BACKLINKS,
            [{"target": domain_q or brand_q, "internal_list_limit": 1, "backlinks_status_type": "live"}],
            auth,
        )
        yt_body, rd_body, wk_body, bl_body = await asyncio.gather(yt_task, rd_task, wk_task, bl_task)

    yt = _parse_serp(yt_body)
    rd = _parse_serp(rd_body)
    wk = _parse_serp(wk_body)
    wiki = _wiki_exists(wk.get("items") or [], brand_q)
    backlinks = _parse_backlinks(bl_body)

    return {
        "probed": True,
        "youtube": {
            "result_count": int(yt.get("result_count") or 0),
            "has_official_channel": _youtube_official(yt.get("items") or [], brand_q, domain_q),
            "ok": bool(yt.get("ok")),
            "error": yt.get("error"),
            "query": queries["youtube"],
        },
        "reddit": {
            "result_count": int(rd.get("result_count") or 0),
            "ok": bool(rd.get("ok")),
            "error": rd.get("error"),
            "query": queries["reddit"],
        },
        "wikipedia": {
            **wiki,
            "result_count": int(wk.get("result_count") or 0),
            "ok": bool(wk.get("ok")),
            "error": wk.get("error"),
            "query": queries["wikipedia"],
        },
        "backlinks": backlinks,
    }
