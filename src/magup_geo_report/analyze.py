from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from magup_geo_report.i18n import REPORT_PLATFORMS

_LABEL = {item["value"]: item["label"] for item in REPORT_PLATFORMS}
_RECOMMEND = re.compile(
    r"推荐|值得|首选|最好|最佳|recommend(?:ed)?|\bbest\b|\btop\b",
    re.I,
)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_LINK = re.compile(r"\[([^\]]{2,60})\]\((https?://[^)]+)\)")
_LIST_NAME = re.compile(
    r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+(?:\*\*|__)?([A-Z][A-Za-z0-9][\w.&+\-]{1,40}(?:\s+[A-Z][A-Za-z0-9][\w.&+\-]{0,24}){0,3})",
)
_URL = re.compile(r"https?://[^\s\]\)>'\"<>]+", re.I)
_GENERIC_HOSTS = {
    "wikipedia.org",
    "youtube.com",
    "youtu.be",
    "reddit.com",
    "google.com",
    "bing.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "github.com",
    "openai.com",
    "anthropic.com",
    "perplexity.ai",
    "apple.com",
    "microsoft.com",
    "amazon.com",
    "medium.com",
    "substack.com",
}
_NAME_STOP = {
    "ai",
    "seo",
    "geo",
    "aeo",
    "llm",
    "llms",
    "brand",
    "brands",
    "tool",
    "tools",
    "platform",
    "platforms",
    "suite",
    "search",
    "chat",
    "gpt",
    "chatgpt",
    "gemini",
    "claude",
    "perplexity",
    "openai",
    "google",
    "best",
    "top",
    "official",
    "website",
    "http",
    "https",
}


def _clean_name(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip(" \t-–—:·*|"))
    text = re.sub(r"\*\*", "", text)
    text = text.strip(" .")
    if not text or len(text) < 3 or len(text) > 48:
        return ""
    if text.lower() in _NAME_STOP:
        return ""
    token = re.split(r"[\s./_-]+", text)[0].lower()
    if token in _NAME_STOP:
        return ""
    return text


def _label_from_host(host: str) -> str:
    host = (host or "").lower()
    if not host or "." not in host:
        return ""
    if any(host == g or host.endswith("." + g) for g in _GENERIC_HOSTS):
        return ""
    label = host.split(".")[0]
    if len(label) < 3 or label in _NAME_STOP:
        return ""
    if label.isdigit():
        return ""
    return label[0].upper() + label[1:]


def extract_competitor_names(answer: str, *, brand: str, extras: list[str] | None = None) -> list[str]:
    """Pull rival brand names from list items, bold text, markdown links, and domains."""
    text = answer or ""
    brand_l = (brand or "").strip().lower()
    found: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        name = _clean_name(raw)
        if not name:
            return
        key = name.lower()
        if brand_l and (key == brand_l or brand_l in key or key in brand_l):
            return
        if key in seen:
            return
        seen.add(key)
        found.append(name)

    for extra in extras or []:
        _add(extra)
    for match in _BOLD.finditer(text):
        _add(match.group(1))
    for match in _MD_LINK.finditer(text):
        _add(match.group(1))
        _add(_label_from_host(_host(match.group(2))))
    for match in _LIST_NAME.finditer(text):
        _add(match.group(1))
    for match in _URL.finditer(text):
        _add(_label_from_host(_host(match.group(0))))
    return found[:16]


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 1) if d else 0.0


def _host(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    host = (urlparse(text).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _hit_name(text: str, name: str) -> bool:
    needle = (name or "").strip()
    if not needle:
        return False
    hay = text or ""
    if any("\u4e00" <= ch <= "\u9fff" for ch in needle):
        return needle.lower() in hay.lower()
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay, re.I) is not None


def _cited_domain(text: str, domain: str) -> bool:
    host = _host(domain)
    if not host:
        return False
    hay = (text or "").lower()
    return host in hay or f"www.{host}" in hay


def _cited_in_sources(sources: Any, domain: str) -> bool:
    host = _host(domain)
    if not host:
        return False
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        hay = f"{src.get('url') or ''} {src.get('domain') or ''}".lower()
        if host in hay or f"www.{host}" in hay:
            return True
    return False


def analyze_item(
    item: dict[str, Any],
    *,
    brand: str,
    domain: str,
    competitors: list[str],
) -> dict[str, Any]:
    answer = str(item.get("answer") or "")
    error = str(item.get("error") or "")
    ok = bool(answer.strip()) and not error
    brand_hit = bool(ok and brand and _hit_name(answer, brand))
    cited = bool(ok and (_cited_domain(answer, domain) or _cited_in_sources(item.get("sources"), domain)))
    competitor_names = [name for name in competitors if name and _hit_name(answer, name)]
    discovered = extract_competitor_names(answer, brand=brand, extras=competitor_names)
    merged: list[str] = []
    seen: set[str] = set()
    for name in competitor_names + discovered:
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(name)
    return {
        "ok": ok,
        "brand_mentioned": brand_hit,
        "own_site_cited": cited,
        "competitors_mentioned": merged,
        "competitor_mentioned": bool(merged),
        "recommended": bool(ok and brand_hit and _RECOMMEND.search(answer)),
    }


def analyze_answers(
    *,
    items: list[dict[str, Any]] | None,
    brand: str,
    domain: str,
    competitors: list[str],
    platforms: list[str],
    prompts: list[str],
) -> dict[str, Any]:
    rows = list(items or [])
    annotated: list[dict[str, Any]] = []
    for item in rows:
        flags = analyze_item(item, brand=brand, domain=domain, competitors=competitors)
        annotated.append({**item, "analysis": flags})

    selected = [code for code in platforms if code in _LABEL] or list(_LABEL)
    present = {str(item.get("platform") or "").lower() for item in annotated if item.get("platform")}
    if not present:
        selected = ["llm"]

    by_platform: dict[str, dict[str, Any]] = {}
    for code in selected:
        subset = [
            item
            for item in annotated
            if (str(item.get("platform") or "llm").lower() == code)
            or (code == "llm" and not item.get("platform"))
        ]
        total = len(subset)
        usable = [item for item in subset if (item.get("analysis") or {}).get("ok")]
        n = len(usable) or total
        brand_hit = sum(1 for item in usable if (item.get("analysis") or {}).get("brand_mentioned"))
        cited = sum(1 for item in usable if (item.get("analysis") or {}).get("own_site_cited"))
        competitor_hit = sum(1 for item in usable if (item.get("analysis") or {}).get("competitor_mentioned"))
        recommended = sum(1 for item in usable if (item.get("analysis") or {}).get("recommended"))
        errors = sum(1 for item in subset if not (item.get("analysis") or {}).get("ok"))
        by_platform[code] = {
            "id": code,
            "label": _LABEL.get(code, "LLM"),
            "total": total,
            "usable": len(usable),
            "errors": errors,
            "brand_hit": brand_hit,
            "own_site_cited": cited,
            "competitor_hit": competitor_hit,
            "recommended": recommended,
            "brand_rate": _pct(brand_hit, n if usable else 0),
            "cite_rate": _pct(cited, n if usable else 0),
            "competitor_rate": _pct(competitor_hit, n if usable else 0),
            "recommend_rate": _pct(recommended, n if usable else 0),
        }

    usable_all = [item for item in annotated if (item.get("analysis") or {}).get("ok")]
    n_all = len(usable_all)
    brand_hit_all = sum(1 for item in usable_all if item["analysis"]["brand_mentioned"])
    cited_all = sum(1 for item in usable_all if item["analysis"]["own_site_cited"])
    competitor_all = sum(1 for item in usable_all if item["analysis"]["competitor_mentioned"])

    matrix: list[dict[str, Any]] = []
    for index, prompt in enumerate(prompts, start=1):
        cells = {}
        for code in selected:
            match = next(
                (
                    item
                    for item in annotated
                    if int(item.get("prompt_index") or 0) == index
                    and str(item.get("platform") or "llm").lower() == code
                ),
                None,
            )
            if match is None and code == "llm":
                match = next(
                    (item for item in annotated if (item.get("prompt") or "") == prompt and not item.get("platform")),
                    None,
                )
            flags = (match or {}).get("analysis") or {}
            cells[code] = {
                "ok": bool(flags.get("ok")),
                "brand_mentioned": bool(flags.get("brand_mentioned")),
                "own_site_cited": bool(flags.get("own_site_cited")),
                "competitor_mentioned": bool(flags.get("competitor_mentioned")),
                "error": (match or {}).get("error") if match else "missing",
            }
        matrix.append({"prompt_index": index, "prompt": prompt, "cells": cells})

    return {
        "disclaimer": (
            "Observed counts from this run's harvested answers. "
            "Not MagUp production Visibility / SOV scores."
        ),
        "brand": brand,
        "domain": domain,
        "competitors": competitors,
        "platforms": selected,
        "totals": {
            "samples": len(annotated),
            "usable": n_all,
            "brand_hit": brand_hit_all,
            "own_site_cited": cited_all,
            "competitor_hit": competitor_all,
            "brand_rate": _pct(brand_hit_all, n_all),
            "cite_rate": _pct(cited_all, n_all),
            "competitor_rate": _pct(competitor_all, n_all),
        },
        "by_platform": by_platform,
        "matrix": matrix,
        "items": annotated,
    }
