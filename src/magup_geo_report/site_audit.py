from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from magup_geo_report.http_util import Fetched, fetch_text, get_client

AI_BOTS = [
    "GPTBot",
    "ChatGPT-User",
    "Google-Extended",
    "PerplexityBot",
    "ClaudeBot",
    "anthropic-ai",
    "Applebot-Extended",
    "Bytespider",
    "CCBot",
    "cohere-ai",
]


@dataclass
class Check:
    id: str
    title: str
    status: str  # pass | warn | fail | skip
    detail: str
    evidence: str = ""
    code: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteAudit:
    requested_url: str
    final_url: str
    domain: str
    brand: str
    homepage: dict[str, Any]
    robots: dict[str, Any]
    llms_txt: dict[str, Any]
    sitemap: dict[str, Any]
    json_ld_types: list[str]
    onpage: dict[str, Any]
    bot_rules: list[dict[str, str]]
    checks: list[Check]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def registrable_host(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host.lower().removeprefix("www.")


def _host(url: str) -> str:
    return registrable_host(url)


def infer_brand(url: str, soup: BeautifulSoup | None) -> str:
    if soup:
        og = soup.find("meta", attrs={"property": "og:site_name"})
        if og and og.get("content"):
            return og["content"].strip()
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if title:
                return re.split(r"[|–—-]", title, maxsplit=1)[0].strip()[:80]
    host = _host(url)
    label = host.split(".")[0] if host else "Site"
    return label[:1].upper() + label[1:]


def _parse_robots(text: str) -> dict[str, list[str]]:
    """Map user-agent (lower) -> list of directive lines."""
    agents: dict[str, list[str]] = {}
    current: list[str] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            current = agents.setdefault(value.lower(), [])
        else:
            if not current:
                current = agents.setdefault("*", [])
            current.append(f"{key}: {value}")
    return agents


def _bot_status(agents: dict[str, list[str]], bot: str) -> tuple[str, str, dict[str, Any]]:
    key = bot.lower()
    star = agents.get("*", [])
    specific = agents.get(key)
    block_re = re.compile(r"^disallow:\s*/\s*$", re.I)
    if specific is not None:
        if any(block_re.match(item) for item in specific):
            return "fail", "bot_disallowed", {"bot": bot}
        if not specific:
            return "warn", "bot_empty_group", {"bot": bot}
        return "pass", "bot_dedicated", {"bot": bot}
    if any(block_re.match(item) for item in star):
        return "warn", "bot_star_disallow", {"bot": bot}
    if "*" in agents:
        return "pass", "bot_fallback_star", {"bot": bot}
    return "warn", "bot_no_group", {"bot": bot}


def _json_ld_types(soup: BeautifulSoup) -> list[str]:
    types: list[str] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                value = node.get("@type")
                if isinstance(value, list):
                    types.extend(str(item) for item in value)
                elif value:
                    types.append(str(value))
                graph = node.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
    # preserve order, unique
    seen: set[str] = set()
    ordered: list[str] = []
    for item in types:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _onpage(soup: BeautifulSoup, final_url: str) -> dict[str, Any]:
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = (desc_tag.get("content") or "").strip() if desc_tag else ""
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical = (canonical_tag.get("href") or "").strip() if canonical_tag else ""
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
    og_title = soup.find("meta", attrs={"property": "og:title"})
    robots_meta = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    text_len = len(soup.get_text(" ", strip=True) or "")
    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "h1": h1s[:8],
        "h1_count": len(h1s),
        "h2": h2s[:12],
        "h2_count": len(h2s),
        "has_article": bool(soup.find("article")),
        "has_main": bool(soup.find("main")),
        "has_section": bool(soup.find("section")),
        "text_length": text_len,
        "og_title": (og_title.get("content") or "").strip() if og_title else "",
        "meta_robots": (robots_meta.get("content") or "").strip() if robots_meta else "",
        "lang": soup.html.get("lang") if soup.html else "",
    }


def audit_url(url: str) -> SiteAudit:
    if not urlparse(url).scheme:
        url = "https://" + url

    checks: list[Check] = []
    with get_client() as client:
        homepage = fetch_text(client, url)
        soup = BeautifulSoup(homepage.body, "html.parser") if homepage.body else BeautifulSoup("", "html.parser")
        brand = infer_brand(homepage.final_url or url, soup if homepage.ok else None)
        domain = _host(homepage.final_url or url)

        origin = f"{urlparse(homepage.final_url or url).scheme}://{urlparse(homepage.final_url or url).netloc}"
        robots_fetched = fetch_text(client, urljoin(origin + "/", "robots.txt"))
        llms_fetched = fetch_text(client, urljoin(origin + "/", "llms.txt"))
        llms_full = fetch_text(client, urljoin(origin + "/", "llms-full.txt"))
        ai_txt = fetch_text(client, urljoin(origin + "/", "ai.txt"))

        robots_agents = _parse_robots(robots_fetched.body) if robots_fetched.ok else {}
        sitemap_urls: list[str] = []
        if robots_fetched.ok:
            for line in robots_fetched.body.splitlines():
                if line.lower().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
        if not sitemap_urls:
            sitemap_urls.append(urljoin(origin + "/", "sitemap.xml"))
        sitemap_fetched = fetch_text(client, sitemap_urls[0])

        bot_rules = []
        for bot in AI_BOTS:
            if robots_fetched.ok:
                status, code, params = _bot_status(robots_agents, bot)
            else:
                status, code, params = "skip", "robots_missing", {}
            bot_rules.append({"bot": bot, "status": status, "code": code, "params": params, "detail": ""})

        json_ld_types = _json_ld_types(soup) if homepage.ok else []
        onpage = _onpage(soup, homepage.final_url) if homepage.ok else {}

        checks.append(
            Check(
                "homepage",
                "Homepage fetch",
                "pass" if homepage.ok else "fail",
                "",
                homepage.final_url,
                code="http" if homepage.status else "error",
                params={"status": homepage.status} if homepage.status else {"error": homepage.error or "failed"},
            )
        )
        checks.append(
            Check(
                "robots",
                "robots.txt",
                "pass" if robots_fetched.ok else "fail",
                "",
                robots_fetched.final_url,
                code="found" if robots_fetched.ok else ("http" if robots_fetched.status else "error"),
                params={"status": robots_fetched.status} if robots_fetched.status else {"error": robots_fetched.error or "failed"},
            )
        )
        blocked_ai = [row["bot"] for row in bot_rules if row["status"] == "fail"]
        if blocked_ai:
            ai_status, ai_code, ai_params = "fail", "ai_blocked", {"bots": ", ".join(blocked_ai)}
        elif robots_fetched.ok:
            ai_status, ai_code, ai_params = "pass", "ai_ok", {}
        else:
            ai_status, ai_code, ai_params = "skip", "robots_missing", {}
        checks.append(
            Check(
                "ai-bots",
                "AI crawler robots groups",
                ai_status,
                "",
                code=ai_code,
                params=ai_params,
            )
        )
        llms_ok = llms_fetched.ok and len(llms_fetched.body.strip()) > 0
        checks.append(
            Check(
                "llms-txt",
                "llms.txt",
                "pass" if llms_ok else "warn",
                "",
                llms_fetched.final_url,
                code="found" if llms_ok else "llms_missing",
            )
        )
        sitemap_ok = sitemap_fetched.ok and (
            "urlset" in sitemap_fetched.body or "sitemapindex" in sitemap_fetched.body or "<url>" in sitemap_fetched.body.lower()
        )
        checks.append(
            Check(
                "sitemap",
                "Sitemap",
                "pass" if sitemap_ok else "warn",
                "",
                sitemap_fetched.final_url,
                code="sitemap_ok" if sitemap_ok else "sitemap_missing",
            )
        )
        checks.append(
            Check(
                "json-ld",
                "JSON-LD",
                "pass" if json_ld_types else "warn",
                "",
                code="jsonld_types" if json_ld_types else "jsonld_missing",
                params={"types": ", ".join(json_ld_types)} if json_ld_types else {},
            )
        )
        title_ok = bool(onpage.get("title"))
        h1_ok = onpage.get("h1_count", 0) >= 1
        checks.append(
            Check(
                "onpage",
                "Title / H1",
                "pass" if title_ok and h1_ok else "warn",
                "",
                code="title_h1",
                params={"title": title_ok, "h1_count": onpage.get("h1_count", 0)},
            )
        )

        return SiteAudit(
            requested_url=url,
            final_url=homepage.final_url,
            domain=domain,
            brand=brand,
            homepage=_fetched_dict(homepage),
            robots={**_fetched_dict(robots_fetched), "sitemaps_declared": sitemap_urls, "user_agents": sorted(robots_agents.keys())},
            llms_txt={
                "llms.txt": _fetched_dict(llms_fetched),
                "llms-full.txt": _fetched_dict(llms_full),
                "ai.txt": _fetched_dict(ai_txt),
            },
            sitemap=_fetched_dict(sitemap_fetched),
            json_ld_types=json_ld_types,
            onpage=onpage,
            bot_rules=bot_rules,
            checks=checks,
        )


def _fetched_dict(item: Fetched) -> dict[str, Any]:
    snippet = item.body[:400].replace("\x00", "") if item.body else ""
    return {
        "url": item.url,
        "final_url": item.final_url,
        "status": item.status,
        "ok": item.ok,
        "error": item.error,
        "content_type": item.content_type,
        "bytes": len(item.body.encode("utf-8")) if item.body else 0,
        "snippet": snippet,
    }
