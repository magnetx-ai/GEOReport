from __future__ import annotations

import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from magup_geo_report.http_util import TIMEOUT, Fetched, fetch_text
from magup_geo_report.llm_raw import collect_raw_answers
from magup_geo_report.prompt_gen import _extract_json
from magup_geo_report.site_audit import infer_brand, registrable_host

INTRO_MAX_CHARS = 1200
BODY_SNIPPET_CHARS = 1500
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
NOISY_HEADING = re.compile(
    r"^(your cart|cart is currently empty|we use cookies|cookies?|privacy( policy)?|"
    r"sign in|log in|login|search|menu|skip to content|newsletter|subscribe|"
    r"follow us|share|close|ok|accept( all)?|add to cart)$",
    re.I,
)


def _browser_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        },
        follow_redirects=True,
        timeout=TIMEOUT,
    )


def _heading_texts(soup: BeautifulSoup, tag: str, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for node in soup.find_all(tag):
        text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
        if not text or len(text) < 2 or NOISY_HEADING.match(text) or text in seen:
            continue
        if re.search(r"footer|cookie|newsletter|sign in|log in", text, re.I):
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _remove_chrome(soup: BeautifulSoup) -> None:
    for node in soup.select("script, style, noscript, svg, iframe, header, nav, footer"):
        node.decompose()
    for node in soup.select("[role='banner'], [role='navigation'], [role='contentinfo']"):
        node.decompose()
    victims = []
    for node in soup.find_all(True):
        hay = f"{node.get('id') or ''} {' '.join(node.get('class') or [])}".lower()
        if re.search(r"(cart|cookie|consent|newsletter|drawer)", hay):
            victims.append(node)
    for node in victims:
        node.decompose()


def _meta_content(soup: BeautifulSoup, **attrs: Any) -> str:
    tag = soup.find("meta", attrs=attrs)
    if not tag:
        return ""
    return re.sub(r"\s+", " ", (tag.get("content") or "")).strip()


def extract_page_brief(url: str) -> dict[str, Any]:
    raw = url if "://" in url else "https://" + url
    with _browser_client() as client:
        homepage: Fetched = fetch_text(client, raw)
    soup = BeautifulSoup(homepage.body, "html.parser") if homepage.body else BeautifulSoup("", "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = re.sub(r"\s+", " ", soup.title.string).strip()
    description = _meta_content(soup, name=re.compile("^description$", re.I)) or _meta_content(
        soup, property="og:description"
    )
    og_title = _meta_content(soup, property="og:title")
    h1 = _heading_texts(soup, "h1", 5)
    h2 = _heading_texts(soup, "h2", 8)
    _remove_chrome(soup)
    main = soup.select_one("main, [role='main'], #MainContent, #main-content, .main-content")
    root = main or soup.body or soup
    body_snippet = re.sub(r"\s+", " ", root.get_text(" ", strip=True)).strip()[:BODY_SNIPPET_CHARS]
    brand = infer_brand(homepage.final_url or raw, soup if homepage.ok else None)
    domain = registrable_host(homepage.final_url or raw)
    sample = f"{title}\n{(homepage.body or '')[:2500]}"
    challenged = bool(
        re.search(
            r"just a moment|cf-browser-verification|attention required|checking your browser",
            sample,
            re.I,
        )
    )
    ok = bool(homepage.ok and not challenged and (title or description or len(body_snippet) > 80))
    return {
        "ok": ok,
        "url": raw,
        "final_url": homepage.final_url,
        "domain": domain,
        "brand": brand,
        "title": title or og_title,
        "description": description,
        "h1": h1,
        "h2": h2,
        "body_snippet": body_snippet,
        "error": homepage.error if not homepage.ok else ("bot challenge" if challenged else None),
    }


def compose_intro_from_page(brief: dict[str, Any], brand: str) -> str:
    name = (brand or brief.get("brand") or "").strip()
    parts: list[str] = []
    if name:
        parts.append(f"【品牌】{name}")
    positioning = (brief.get("description") or "").strip() or " ".join(brief.get("h1") or [])
    if positioning:
        parts.append(f"【业务定位】{positioning}")
    products = [item for item in (brief.get("h2") or []) if item][:6]
    if products:
        parts.append("【核心产品/服务】" + "；".join(products))
    snippet = (brief.get("body_snippet") or "").strip()
    if snippet and snippet not in positioning:
        parts.append(f"【页面摘录】{snippet[:420]}")
    return "\n".join(parts).strip()[:INTRO_MAX_CHARS]


def fallback_intro(brand: str, domain: str, error: str = "") -> str:
    detail = f"（{error}）" if error else ""
    return f"【品牌】{brand}\n【业务定位】官网 {domain}。页面未能完整抓取{detail}，请核对后使用。"[:INTRO_MAX_CHARS]


def summarize_intro_with_llm(
    *,
    brief: dict[str, Any],
    brand: str,
    api_key: str,
    base_url: str,
    model: str,
) -> str:
    payload = {
        "brand_hint": brand,
        "domain": brief.get("domain"),
        "url": brief.get("final_url") or brief.get("url"),
        "title": brief.get("title"),
        "description": brief.get("description"),
        "h1": brief.get("h1"),
        "h2": brief.get("h2"),
        "body_snippet": (brief.get("body_snippet") or "")[:1200],
    }
    instruction = f"""You are a website analyst. Return ONLY JSON with no markdown.
Write a structured website introduction for GEO/AEO monitoring.
Facts MUST come ONLY from the scraped page payload. Do NOT invent products, customers, or claims.

Rules:
- intro: plain text with 【】 section headers, max {INTRO_MAX_CHARS} characters
- Include when evidence exists: 【品牌】【业务定位】【目标用户/场景】【核心产品/服务】【差异化/信任背书】【AI监测建议角度】
- brandName: best public brand name from title/h1/domain
- Be factual and neutral; prefer concrete nouns over marketing fluff

Output: {{"intro": "string", "brandName": "string"}}

INPUT:
{payload}
"""
    raw = collect_raw_answers(
        prompts=[instruction],
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    items = raw.get("items") or []
    answer = (items[0].get("answer") or "") if items else ""
    parsed = _extract_json(answer)
    intro = str(parsed.get("intro") or "").strip() if isinstance(parsed, dict) else ""
    return intro[:INTRO_MAX_CHARS]


def resolve_brand_intro(
    *,
    url: str,
    brand: str,
    existing: str = "",
    llm_api_key: str | None = None,
    llm_base_url: str = "https://api.openai.com/v1",
    llm_model: str = "gpt-4o-mini",
) -> dict[str, Any]:
    """If intro is blank, crawl the site (magup_v3 analyze-site). Optionally refine with LLM."""
    current = (existing or "").strip()
    if current:
        return {"intro": current[:INTRO_MAX_CHARS], "source": "user", "brand": brand, "brief": None}
    brief = extract_page_brief(url)
    source = "crawl"
    intro = ""
    if brief.get("ok"):
        if llm_api_key:
            try:
                intro = summarize_intro_with_llm(
                    brief=brief,
                    brand=brand,
                    api_key=llm_api_key,
                    base_url=llm_base_url,
                    model=llm_model,
                )
                if intro:
                    source = "llm"
            except Exception:
                intro = ""
        if not intro:
            intro = compose_intro_from_page(brief, brand)
            source = "crawl"
    if not intro:
        intro = fallback_intro(brand, brief.get("domain") or registrable_host(url), brief.get("error") or "")
        source = "fallback"
    return {
        "intro": intro[:INTRO_MAX_CHARS],
        "source": source,
        "brand": brand or brief.get("brand") or "",
        "brief": brief,
    }
