"""Build magup_v3 dashboard JSON from this run's harvest, analysis, and site audit.

Does not invent Ahrefs DR, media, YouTube, Reddit, or Wikipedia scores.
Untested channels are marked 本轮未测 / not_tested.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import log10
from typing import Any
from urllib.parse import urlparse

from magup_geo_report.i18n import REPORT_PLATFORMS
from magup_geo_report.analyze import extract_competitor_names
from magup_geo_report.site_audit import SiteAudit

_PLATFORM_LABEL = {item["value"]: item["label"] for item in REPORT_PLATFORMS}
_ALL_PLATFORMS = [item["value"] for item in REPORT_PLATFORMS]
_URL_RE = re.compile(r"https?://[^\s\]\)>'\"<>]+", re.I)
_NEGATIVE = re.compile(
    r"不推荐|不建議|坑|避雷|骗局|詐騙|\bscam\b|\bavoid\b|don't use|do not use|不值得",
    re.I,
)
_POSITIVE = re.compile(
    r"推荐|值得|首选|最好|最佳|recommend(?:ed)?|\bbest\b|\btop\b",
    re.I,
)
_PHRASE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_PHRASE_QUOTE = re.compile(r"[「『“\"]([^」』”\"]{2,28})[」』”\"]")
_PHRASE_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "your", "their", "have",
    "best", "tools", "tool", "brand", "brands", "platform", "platforms", "using",
    "into", "also", "more", "than", "such", "which", "what", "when", "about",
    "official", "website", "search", "answers", "answer", "model", "models",
    "chatgpt", "gemini", "claude", "perplexity", "openai", "google", "llm", "llms",
    "geo", "aeo", "seo", "ai-powered",
}
DEFAULT_INDUSTRY_AUTHORITY = [68, 65, 75, 60, 55]
DEFAULT_SOURCE_INDUSTRY = [68, 55, 65, 75, 60, 60, 55]


def _pct(n: Any, d: Any) -> float:
    try:
        nn, dd = float(n), float(d)
    except (TypeError, ValueError):
        return 0.0
    if dd <= 0:
        return 0.0
    return round(nn / dd * 100, 1)


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


def _is_cjk(language: str) -> bool:
    key = (language or "").lower()
    return key.startswith("zh") or key.startswith("ja")


def _is_branded_prompt(prompt: str, brand: str, domain: str) -> bool:
    if brand and _hit_name(prompt, brand):
        return True
    host = _host(domain)
    if host and host in (prompt or "").lower():
        return True
    return False


def _display_name(platform: str) -> str:
    return _PLATFORM_LABEL.get(platform, platform or "LLM")


def _urls_from_text(text: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for match in _URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(").,;]")
        key = url.lower().rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": url, "title": "", "domain": _host(url), "usage": "applied"})
    return out


def _merge_sources(*groups: Any) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for group in groups:
        if not isinstance(group, list):
            continue
        for src in group:
            if not isinstance(src, dict):
                continue
            url = str(src.get("url") or "").strip()
            domain = str(src.get("domain") or "").strip() or _host(url)
            title = str(src.get("title") or "").strip()
            key = (url or domain).lower().rstrip("/")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "usage": str(src.get("usage") or "applied"),
                }
            )
    return out


def _sentiment(answer: str, mentioned: bool) -> str:
    if not mentioned:
        return "neutral"
    if _NEGATIVE.search(answer or ""):
        return "negative"
    if _POSITIVE.search(answer or ""):
        return "positive"
    return "neutral"


def _cloud_phrases(text: str, brand: str) -> list[str]:
    brand_l = (brand or "").strip().lower()
    out: list[str] = []
    for match in _PHRASE_BOLD.finditer(text or ""):
        out.append(match.group(1).strip())
    for match in _PHRASE_QUOTE.finditer(text or ""):
        out.append(match.group(1).strip())
    for token in re.findall(r"\b[A-Z][A-Za-z0-9][A-Za-z0-9.+-]{2,24}\b", text or ""):
        if token.lower() not in _PHRASE_STOP:
            out.append(token)
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in out:
        phrase = re.sub(r"\s+", " ", raw).strip(" .,-")
        if len(phrase) < 2 or len(phrase) > 28:
            continue
        key = phrase.lower()
        if brand_l and (key == brand_l or brand_l in key):
            continue
        if key in _PHRASE_STOP or key in seen:
            continue
        seen.add(key)
        cleaned.append(phrase)
    return cleaned


def _word_cloud(rows: list[dict[str, Any]], brand: str) -> dict[str, Any]:
    buckets: dict[str, Counter[str]] = {
        "positive": Counter(),
        "neutral": Counter(),
        "negative": Counter(),
    }
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for row in rows:
        if not row.get("ok") and not row.get("answer_markdown"):
            continue
        sent = str(row.get("brand_sentiment") or "neutral")
        if sent not in buckets:
            sent = "neutral"
        counts[sent] += 1
        for phrase in _cloud_phrases(str(row.get("answer_markdown") or ""), brand):
            buckets[sent][phrase] += 1
        for name in row.get("competitor_names") or []:
            if name:
                buckets[sent][str(name)] += 1

    def _terms(counter: Counter[str]) -> list[dict[str, Any]]:
        items = []
        for text, n in counter.most_common(28):
            items.append({"text": text, "count": int(n), "weight": int(n)})
        return items

    positive = _terms(buckets["positive"])
    neutral = _terms(buckets["neutral"])
    negative = _terms(buckets["negative"])
    empty = not (positive or neutral or negative)
    return {
        "method": "answer_phrase_extract",
        "answer_count": counts,
        "positive": positive,
        "neutral": neutral,
        "negative": negative,
        **({"empty_reason": "no_phrases_extracted"} if empty else {}),
    }


def _log_score(count: int, cap: int = 10000) -> float:
    n = max(0, int(count or 0))
    if n <= 0:
        return 0.0
    return round(min(100.0, log10(max(1, n)) / log10(cap) * 100), 1)


def _check_map(audit: SiteAudit | None) -> dict[str, Any]:
    if not audit:
        return {}
    return {check.id: check for check in audit.checks}


def _llms_status(audit: SiteAudit | None) -> str:
    if not audit:
        return "unknown"
    block = (audit.llms_txt or {}).get("llms.txt") or {}
    if block.get("ok") and int(block.get("bytes") or 0) > 0:
        return "deployed"
    homepage = audit.homepage or {}
    if homepage.get("ok"):
        return "missing"
    return "unknown"


def _channel_cards(
    audit: SiteAudit | None,
    language: str,
    offsite: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    zh = _is_cjk(language)
    checks = _check_map(audit)
    onpage = (audit.onpage if audit else {}) or {}
    has_crawl = bool(audit and (audit.homepage or {}).get("ok"))
    json_ld = list((audit.json_ld_types if audit else []) or [])
    desc = str(onpage.get("description") or "")
    semantic_present = any(onpage.get(key) for key in ("has_article", "has_main", "has_section"))
    semantic_all = all(onpage.get(key) for key in ("has_article", "has_main", "has_section"))
    llms = _llms_status(audit)

    def card(channel: str, status: str, headline: str, description: str, group: str) -> dict[str, Any]:
        return {
            "channel": channel,
            "status": status,
            "headline": headline,
            "description": description,
            "group": group,
        }

    schema_ok = bool(json_ld)
    schema = card(
        "Schema 结构化数据" if zh else "Schema markup",
        "active" if schema_ok else ("critical_gap" if has_crawl else "not_tested"),
        ("可见" if zh else "Present") if schema_ok else ("缺失" if zh else "Missing"),
        (
            (("已识别类型：" + " / ".join(json_ld[:4])) if json_ld else "抓取证据显示 JSON-LD 缺失或为空。")
            if zh
            else (("Types: " + " / ".join(json_ld[:4])) if json_ld else "Homepage crawl found no JSON-LD.")
        )
        if has_crawl
        else ("本轮未能完成官网抓取。" if zh else "Official-site crawl did not complete this run."),
        "official_site",
    )
    if has_crawl and not semantic_all and semantic_present:
        semantic_status, semantic_head = "partial", ("部分可见" if zh else "Partial")
    elif has_crawl and semantic_present:
        semantic_status, semantic_head = "active", ("可见" if zh else "Present")
    elif has_crawl:
        semantic_status, semantic_head = "critical_gap", ("缺失" if zh else "Missing")
    else:
        semantic_status, semantic_head = "not_tested", ("待复测" if zh else "Retest")
    semantic = card(
        "语义标签 · Semantic HTML" if zh else "Semantic HTML",
        semantic_status,
        semantic_head,
        ("检测到 article / main / section 语义边界。" if semantic_present else "主体内容机器边界不清。")
        if zh
        else ("Detected article / main / section landmarks." if semantic_present else "No clear content landmarks."),
        "official_site",
    )
    meta_ok = bool(desc.strip())
    meta_short = meta_ok and len(desc.strip()) < 50
    meta = card(
        "Meta Description",
        "partial" if meta_short else ("active" if meta_ok else ("critical_gap" if has_crawl else "not_tested")),
        ("偏短" if zh else "Short") if meta_short else (("可见" if zh else "Present") if meta_ok else ("空" if zh else "Empty")),
        (f"检测到首页 meta description（{len(desc.strip())} 字）。" if meta_ok else "首页 meta description 缺失会削弱官方一句话定义。")
        if zh
        else (
            f"Homepage meta description present ({len(desc.strip())} chars)."
            if meta_ok
            else "Missing homepage meta description."
        ),
        "official_site",
    )
    if llms == "deployed":
        llms_card = card("llms.txt", "active", "已部署" if zh else "Deployed", "检测到 llms.txt。" if zh else "llms.txt found.", "official_site")
    elif llms == "missing":
        llms_card = card(
            "llms.txt",
            "not_deployed",
            "未部署" if zh else "Not deployed",
            "非强制项，但可作为 AI 抓取声明 quick win。" if zh else "Optional, but a useful AI crawl declaration.",
            "official_site",
        )
    else:
        llms_card = card(
            "llms.txt",
            "not_tested",
            "待复测" if zh else "Retest",
            "本轮未能确认 llms.txt。" if zh else "Could not confirm llms.txt this run.",
            "official_site",
        )

    pending = "本轮未独立测试；保留为下一轮复测对象。" if zh else "Not independently tested this run; kept for retest."
    pending_head = "待复测" if zh else "Retest"
    signals = offsite if isinstance(offsite, dict) else {}
    probed = bool(signals.get("probed"))
    yt = signals.get("youtube") if isinstance(signals.get("youtube"), dict) else {}
    rd = signals.get("reddit") if isinstance(signals.get("reddit"), dict) else {}
    wiki = signals.get("wikipedia") if isinstance(signals.get("wikipedia"), dict) else {}
    bl = signals.get("backlinks") if isinstance(signals.get("backlinks"), dict) else {}

    def _search_card(
        channel: str,
        row: dict[str, Any],
        *,
        unit_zh: str,
        unit_en: str,
        empty_zh: str,
        empty_en: str,
        extra_zh: str = "",
        extra_en: str = "",
    ) -> dict[str, Any]:
        if not probed:
            return card(channel, "not_tested", pending_head, pending, "offsite_social")
        row = row if isinstance(row, dict) else {}
        if row.get("ok") is False and not row.get("result_count"):
            return card(
                channel,
                "not_tested",
                pending_head,
                (f"本轮检索失败：{row.get('error') or '接口不可用'}。" if zh else f"Search failed: {row.get('error') or 'unavailable'}."),
                "offsite_social",
            )
        count = int(row.get("result_count") or 0)
        if count <= 0:
            return card(channel, "critical_gap", "0" if zh else "0", empty_zh if zh else empty_en, "offsite_social")
        head = f"{count}+ {unit_zh}" if zh else f"{count}+ {unit_en}"
        desc = extra_zh if zh else extra_en
        official = bool(row.get("has_official_channel") or row.get("exists"))
        status = "active" if official or count >= 20 else "partial"
        return card(channel, status, head, desc, "offsite_social")

    yt_card = _search_card(
        "YouTube 视频" if zh else "YouTube",
        yt,
        unit_zh="条检索",
        unit_en="search hits",
        empty_zh="本轮已用品牌关键字 + site:youtube.com 检索，公开结果为空。",
        empty_en="Brand + site:youtube.com returned no public hits this run.",
        extra_zh=(
            f"公开搜索「品牌/域名 + site:youtube.com」约 {int(yt.get('result_count') or 0)}+ 条"
            + ("，检测到疑似官方频道。" if yt.get("has_official_channel") else "。")
            + "检索命中可能含同名或无关内容，不是精确品牌视频清单。"
        ),
        extra_en=(
            f"Public search brand/domain + site:youtube.com ≈ {int(yt.get('result_count') or 0)}+ hits"
            + ("; a likely official channel was detected." if yt.get("has_official_channel") else ".")
            + " Hits may include namesakes; not a verified brand-video inventory."
        ),
    )
    rd_card = _search_card(
        "Reddit / 论坛" if zh else "Reddit / forums",
        rd,
        unit_zh="条检索",
        unit_en="search hits",
        empty_zh="本轮已用品牌关键字 + site:reddit.com 检索，公开结果为空。",
        empty_en="Brand + site:reddit.com returned no public hits this run.",
        extra_zh=f"公开搜索约 {int(rd.get('result_count') or 0)}+ 条。命中可能含同名或品类泛词，不是逐帖核验后的品牌讨论清单。",
        extra_en=f"About {int(rd.get('result_count') or 0)}+ public hits. Not a human-verified brand-thread list.",
    )
    if probed:
        if wiki.get("exists"):
            wiki_card = card(
                "Wikipedia / 百科" if zh else "Wikipedia",
                "active",
                "有条目" if zh else "Article found",
                (f"检测到词条：{wiki.get('title') or wiki.get('url')}。" if zh else f"Article: {wiki.get('title') or wiki.get('url')}."),
                "offsite_social",
            )
        elif wiki.get("ok") is False and not wiki.get("result_count"):
            wiki_card = card("Wikipedia / 百科" if zh else "Wikipedia", "not_tested", pending_head, pending, "offsite_social")
        else:
            wiki_card = card(
                "Wikipedia / 百科" if zh else "Wikipedia",
                "critical_gap",
                "无条目" if zh else "No article",
                "本轮 Wikipedia 检索未找到品牌词条。" if zh else "No Wikipedia article found for this brand this run.",
                "offsite_social",
            )
    else:
        wiki_card = card("Wikipedia / 百科" if zh else "Wikipedia", "not_tested", pending_head, pending, "offsite_social")

    if bl.get("ok"):
        backlinks_n = int(bl.get("backlinks") or 0)
        referring = int(bl.get("referring_domains") or 0)
        rank = int(bl.get("rank") or 0)
        bl_card = card(
            "外链 / Backlinks" if zh else "Backlinks",
            "partial" if backlinks_n < 200 else "active",
            f"{backlinks_n:,}" if backlinks_n else (str(rank) if rank else "0"),
            (
                f"外链约 {backlinks_n:,} 条、引用域约 {referring:,} 个、权威分 {rank}。本报告仅展示聚合总量。"
                if zh
                else f"About {backlinks_n:,} backlinks, {referring:,} referring domains, rank {rank}. Aggregate only."
            ),
            "offsite_social",
        )
    else:
        bl_card = card(
            "外链 / Backlinks" if zh else "Backlinks",
            "not_tested",
            pending_head,
            (
                f"本轮未取得外链总量（{bl.get('error') or '接口不可用'}）。"
                if probed
                else pending
            )
            if zh
            else (
                f"Backlink summary unavailable ({bl.get('error') or 'not enabled'})."
                if probed
                else pending
            ),
            "offsite_social",
        )

    _ = checks
    return [schema, semantic, meta, llms_card, bl_card, yt_card, rd_card, wiki_card]


def _offsite_recommendation(*, zh: bool, brand: str, offsite: dict[str, Any] | None) -> dict[str, str]:
    signals = offsite if isinstance(offsite, dict) else {}
    probed = bool(signals.get("probed"))
    yt = signals.get("youtube") if isinstance(signals.get("youtube"), dict) else {}
    rd = signals.get("reddit") if isinstance(signals.get("reddit"), dict) else {}
    wiki = signals.get("wikipedia") if isinstance(signals.get("wikipedia"), dict) else {}
    bl = signals.get("backlinks") if isinstance(signals.get("backlinks"), dict) else {}
    if not probed:
        if zh:
            return {
                "priority": "P2",
                "action": "下一轮复测外链、媒体、视频与社区信源",
                "why": "本轮未独立测试站外信源，不能把未测写成 0 分。先完成复测再决定 PR / 视频 / 社区投入。",
                "expected_metric_change": "外链 / YouTube / Reddit / 百科由待复测转为有证据口径",
                "effort_band": "高 · 长周期内容 / 社区",
                "effort_code": "high",
                "evidence_basis": "untested_offsite",
            }
        return {
            "priority": "P2",
            "action": "Retest backlinks, media, video, and community sources next run",
            "why": "Off-site channels were not independently tested this run. Do not treat untested as a zero score.",
            "expected_metric_change": "Backlinks / YouTube / Reddit / Wikipedia move from pending to evidenced",
            "effort_band": "High · long-cycle content / community",
            "effort_code": "high",
            "evidence_basis": "untested_offsite",
        }
    yt_n = int(yt.get("result_count") or 0)
    rd_n = int(rd.get("result_count") or 0)
    wiki_bit = ("有条目" if wiki.get("exists") else "无条目") if zh else ("article found" if wiki.get("exists") else "no article")
    bl_bit = (
        f"外链 {int(bl.get('backlinks') or 0)} / 引用域 {int(bl.get('referring_domains') or 0)}"
        if bl.get("ok")
        else ("外链未返回" if zh else "backlinks unavailable")
    )
    if zh:
        return {
            "priority": "P2",
            "action": f"补齐 {brand} 的百科、视频与社区被检索足迹",
            "why": f"本轮站外检索：Wikipedia {wiki_bit}；YouTube 约 {yt_n}+；Reddit 约 {rd_n}+；{bl_bit}。缺口会让模型更依赖竞品内容来描述品牌。",
            "expected_metric_change": "百科条目、视频/社区检索命中与引用域可见度提升",
            "effort_band": "高 · 长周期内容 / 社区",
            "effort_code": "high",
            "evidence_basis": "measured_offsite",
        }
    return {
        "priority": "P2",
        "action": f"Fill encyclopedia, video, and community footprints for {brand}",
        "why": f"This run: Wikipedia {wiki_bit}; YouTube ~{yt_n}+; Reddit ~{rd_n}+; {bl_bit}. Gaps push models toward rival content.",
        "expected_metric_change": "Encyclopedia presence and video/community search hits",
        "effort_band": "High · long-cycle content / community",
        "effort_code": "high",
        "evidence_basis": "measured_offsite",
    }


def _recommendations(
    *,
    brand: str,
    language: str,
    audit: SiteAudit | None,
    unbranded_mentioned: int,
    unbranded_total: int,
    branded_cited: int,
    branded_total: int,
    lost_queries: list[str],
    rivals: list[str],
    offsite: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    zh = _is_cjk(language)
    has_crawl = bool(audit and (audit.homepage or {}).get("ok"))
    json_ld = list((audit.json_ld_types if audit else []) or [])
    onpage = (audit.onpage if audit else {}) or {}
    desc = str(onpage.get("description") or "")
    llms = _llms_status(audit)
    examples = [q for q in lost_queries if q][:3]
    rival_phrase = ("、" if zh else ", ").join(rivals[:2]) if rivals else ("头部竞品" if zh else "leading competitors")
    query_phrase = (
        ("".join(f"【{q}】" for q in examples) + "等无品牌高频问题")
        if zh and examples
        else (
            "; ".join(f"“{q}”" for q in examples) + " and similar unbranded questions"
            if examples
            else ("无品牌高频品类问题" if zh else "high-frequency unbranded category questions")
        )
    )
    recs: list[dict[str, str]] = []
    if zh:
        recs.append(
            {
                "priority": "P0",
                "action": "官网机器可读性与页面结构补强",
                "why": (
                    f"官网是 AI 认识 {brand} 的第一可信源。"
                    + ("本轮未能完成抓取，需先恢复可抓取再补 Schema / 语义结构 / 专题页。" if not has_crawl else "")
                    + ("" if json_ld else "当前 JSON-LD 不足，实体边界不清。")
                    + ("" if desc.strip() else "首页缺少 meta description。")
                    + ("建议补 llms.txt 作为抓取声明。" if llms != "deployed" else "")
                ),
                "expected_metric_change": "Schema / 语义标签 / Meta / llms.txt 复测由缺口转为可见",
                "effort_band": "低 · 一次性模板改动",
                "effort_code": "low",
                "evidence_basis": "measured_site_crawl",
            }
        )
        recs.append(
            {
                "priority": "P0",
                "action": "官网可引用内容与信息架构建设",
                "why": f"无品牌场景当前 {unbranded_mentioned}/{unbranded_total}。先把品类/对比页做成可引用事实，再谈外链与社媒。",
                "expected_metric_change": "无品牌提及率与官网引用率提升",
                "effort_band": "中 · 内容 + 工程",
                "effort_code": "medium",
                "evidence_basis": "measured_unbranded_gap",
            }
        )
        recs.append(
            {
                "priority": "P1",
                "action": f"针对{query_phrase}补可被引用的专题页",
                "why": f"这些提问是真实获客入口；{brand} 缺席时推荐位更容易被 {rival_phrase} 接管。",
                "expected_metric_change": "目标无品牌提问的提及率由缺席转为进入推荐列表",
                "effort_band": "中 · 内容 + 工程",
                "effort_code": "medium",
                "evidence_basis": "measured_lost_queries",
            }
        )
        recs.append(_offsite_recommendation(zh=True, brand=brand, offsite=offsite))
    else:
        recs.append(
            {
                "priority": "P0",
                "action": "Strengthen on-site machine readability and page structure",
                "why": (
                    f"The official site is the first trusted source AI uses to understand {brand}. "
                    + ("This run could not complete the crawl; restore access first. " if not has_crawl else "")
                    + ("JSON-LD is missing. " if not json_ld else "")
                    + ("Homepage meta description is empty. " if not desc.strip() else "")
                    + ("Add llms.txt as a crawl declaration. " if llms != "deployed" else "")
                ),
                "expected_metric_change": "Schema / semantic HTML / meta / llms.txt move from gap to visible on retest",
                "effort_band": "Low · one-time template change",
                "effort_code": "low",
                "evidence_basis": "measured_site_crawl",
            }
        )
        recs.append(
            {
                "priority": "P0",
                "action": "Build citable on-site content and information architecture",
                "why": f"Unbranded visibility is {unbranded_mentioned}/{unbranded_total}. Make category and comparison pages citable before investing off-site.",
                "expected_metric_change": "Unbranded mention rate and official-site citation rate",
                "effort_band": "Medium · content + engineering",
                "effort_code": "medium",
                "evidence_basis": "measured_unbranded_gap",
            }
        )
        recs.append(
            {
                "priority": "P1",
                "action": f"Publish citable topic pages for {query_phrase}",
                "why": f"These questions are the real acquisition entry. When {brand} is absent, {rival_phrase} take the recommendation slot.",
                "expected_metric_change": "Target unbranded prompts move from absent to listed",
                "effort_band": "Medium · content + engineering",
                "effort_code": "medium",
                "evidence_basis": "measured_lost_queries",
            }
        )
        recs.append(_offsite_recommendation(zh=False, brand=brand, offsite=offsite))
    if branded_total and branded_cited / max(branded_total, 1) < 0.4:
        if zh:
            recs.insert(
                2,
                {
                    "priority": "P1",
                    "action": "提高品牌词提问下的官网引用率",
                    "why": f"品牌词场景官网仅被引用 {branded_cited}/{branded_total}。识别品牌不等于调用官网。",
                    "expected_metric_change": "品牌词提问官网引用率提升",
                    "effort_band": "中 · 内容 + 工程",
                    "effort_code": "medium",
                    "evidence_basis": "measured_branded_cite",
                },
            )
        else:
            recs.insert(
                2,
                {
                    "priority": "P1",
                    "action": "Raise official-site citation on branded prompts",
                    "why": f"Official site cited in {branded_cited}/{branded_total} branded answers. Recognition is not the same as citing the site.",
                    "expected_metric_change": "Official-site citation rate on branded prompts",
                    "effort_band": "Medium · content + engineering",
                    "effort_code": "medium",
                    "evidence_basis": "measured_branded_cite",
                },
            )
    return recs[:6]


def _rows_from_analysis(
    analysis: dict[str, Any] | None,
    *,
    brand: str,
    domain: str,
    competitors: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in list((analysis or {}).get("items") or []):
        flags = item.get("analysis") or {}
        prompt = str(item.get("prompt") or "")
        answer = str(item.get("answer") or "")
        mentioned = bool(flags.get("brand_mentioned"))
        cited = bool(flags.get("own_site_cited"))
        comps = list(flags.get("competitors_mentioned") or [])
        if not comps:
            comps = [name for name in competitors if name and _hit_name(answer, name)]
        discovered = extract_competitor_names(answer, brand=brand, extras=comps)
        merged: list[str] = []
        seen_n: set[str] = set()
        for name in comps + discovered:
            key = str(name).lower()
            if not name or key in seen_n or key == brand.lower():
                continue
            seen_n.add(key)
            merged.append(str(name))
        comps = merged
        sources = _merge_sources(item.get("sources"), _urls_from_text(answer))
        rows.append(
            {
                "platform": str(item.get("platform") or "llm"),
                "question": prompt,
                "prompt_index": int(item.get("prompt_index") or 0),
                "mentioned": mentioned,
                "official_site_cited": cited,
                "semantic_accuracy": mentioned,
                "competitor_mentioned": bool(comps or flags.get("competitor_mentioned")),
                "competitor_names": comps,
                "collect_error": str(item.get("error") or "").strip(),
                "brand_sentiment": _sentiment(answer, mentioned),
                "answer_markdown": answer,
                "answer_excerpt": answer,
                "answer_sources": sources,
                "ok": bool(flags.get("ok")),
                "scenario_group": (
                    "branded_accuracy_validation"
                    if _is_branded_prompt(prompt, brand, domain)
                    else "unbranded_category_discovery"
                ),
            }
        )
    return rows


def build_dashboard(
    *,
    audit: SiteAudit | None,
    answers: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = meta or {}
    language = str(meta.get("language") or "zh-Hans")
    zh = _is_cjk(language)
    brand = str(meta.get("brand") or (analysis or {}).get("brand") or (audit.brand if audit else "") or "")
    domain = str((analysis or {}).get("domain") or (audit.domain if audit else "") or "")
    intro = str(meta.get("brand_intro") or "")
    competitors = [str(x).strip() for x in (meta.get("competitors") or []) if str(x).strip()][:4]
    offsite = meta.get("offsite") if isinstance(meta.get("offsite"), dict) else {}
    selected = [str(x) for x in (meta.get("platforms") or (analysis or {}).get("platforms") or []) if x]
    if not selected:
        selected = list(_ALL_PLATFORMS)

    rows = _rows_from_analysis(analysis, brand=brand, domain=domain, competitors=competitors)
    if not rows and answers:
        rows = _rows_from_analysis(
            {"items": list(answers.get("items") or [])},
            brand=brand,
            domain=domain,
            competitors=competitors,
        )

    branded = [r for r in rows if r.get("scenario_group") == "branded_accuracy_validation"]
    unbranded = [r for r in rows if r.get("scenario_group") == "unbranded_category_discovery"]
    if not branded and not unbranded and rows:
        branded = list(rows)
    branded_total = len(branded)
    unbranded_total = len(unbranded)
    branded_mentioned = sum(1 for r in branded if r.get("mentioned"))
    branded_cited = sum(1 for r in branded if r.get("official_site_cited"))
    branded_semantic = sum(1 for r in branded if r.get("semantic_accuracy"))
    branded_complete = sum(1 for r in branded if r.get("mentioned") and r.get("semantic_accuracy"))
    unbranded_mentioned = sum(1 for r in unbranded if r.get("mentioned"))
    unbranded_cited = sum(1 for r in unbranded if r.get("official_site_cited"))
    unbranded_takeover = sum(1 for r in unbranded if not r.get("mentioned") and r.get("competitor_mentioned"))
    unbranded_competitor = sum(1 for r in unbranded if r.get("competitor_mentioned"))
    unbranded_all_absent = max(0, unbranded_total - unbranded_takeover - unbranded_mentioned)
    total_samples = len(rows)

    official_cite_rate = (
        round(_pct(branded_cited, branded_total))
        if branded_total
        else round(_pct(unbranded_cited, unbranded_total))
    )
    official_auth = official_cite_rate
    yt = offsite.get("youtube") if isinstance(offsite.get("youtube"), dict) else {}
    rd = offsite.get("reddit") if isinstance(offsite.get("reddit"), dict) else {}
    wiki = offsite.get("wikipedia") if isinstance(offsite.get("wikipedia"), dict) else {}
    bl = offsite.get("backlinks") if isinstance(offsite.get("backlinks"), dict) else {}
    wiki_score = 72.0 if wiki.get("exists") else (8.0 if offsite.get("probed") else 10.0)
    media_score = _log_score(int(bl.get("referring_domains") or 0), 5000) if bl.get("ok") else (12.0 if not offsite.get("probed") else 8.0)
    yt_score = _log_score(int(yt.get("result_count") or 0)) if offsite.get("probed") else 0.0
    if yt.get("has_official_channel"):
        yt_score = min(100.0, yt_score + 12)
    rd_score = _log_score(int(rd.get("result_count") or 0)) if offsite.get("probed") else 0.0
    radar_target = [
        official_auth,
        wiki_score,
        media_score,
        round((yt_score + rd_score) / 2, 1) if offsite.get("probed") else 8.0,
        35.0 if not offsite.get("probed") else min(40.0, media_score),
    ]
    source_target = [official_auth, 0, wiki_score, media_score, yt_score, rd_score, radar_target[4]]
    source_status = [
        "tested",
        "not_independently_tested",
        "tested" if offsite.get("probed") else "not_independently_tested",
        "tested" if bl.get("ok") else "not_independently_tested",
        "tested" if offsite.get("probed") else "not_independently_tested",
        "tested" if offsite.get("probed") else "not_independently_tested",
        "not_independently_tested",
    ]
    source_labels = (
        ["官网", "开发者文档", "百科", "媒体 / PR", "YouTube 视频", "Reddit / 论坛", "B2B 评测 (G2 / Capterra)"]
        if zh
        else ["Official site", "Docs", "Encyclopedia", "Media / PR", "YouTube", "Reddit / forums", "B2B reviews"]
    )

    platform_data = []
    for code in selected:
        family_rows = [r for r in rows if str(r.get("platform") or "").lower() == code]
        p_unb = [r for r in family_rows if r.get("scenario_group") == "unbranded_category_discovery"]
        p_br = [r for r in family_rows if r.get("scenario_group") == "branded_accuracy_validation"]
        unb_den = len(p_unb)
        br_den = len(p_br)
        unb_mentions = sum(1 for r in p_unb if r.get("mentioned"))
        br_mentions = sum(1 for r in p_br if r.get("mentioned"))
        unb_cited_n = sum(1 for r in p_unb if r.get("official_site_cited"))
        competitor_count = sum(1 for r in p_unb if r.get("competitor_mentioned"))
        platform_data.append(
            {
                "id": code,
                "display_name": _display_name(code),
                "status": "tested" if family_rows else "pending",
                "total_results": len(family_rows),
                "mention_count": sum(1 for r in family_rows if r.get("mentioned")),
                "brand_visibility_rate": _pct(br_mentions, br_den),
                "branded_total": br_den,
                "branded_mention_count": br_mentions,
                "unbranded_total": unb_den,
                "unbranded_mention_count": unb_mentions,
                "unbranded_visibility_rate": _pct(unb_mentions, unb_den),
                "official_site_cited_count": unb_cited_n,
                "official_site_cited_rate": _pct(unb_cited_n, unb_den),
                "semantic_accuracy_count": sum(1 for r in p_unb if r.get("semantic_accuracy")),
                "semantic_accuracy_rate": _pct(sum(1 for r in p_unb if r.get("semantic_accuracy")), unb_den),
                "competitor_mention_count": competitor_count,
                "competitor_inverse_score": round(max(0, 100 - _pct(competitor_count, unb_den)), 1),
            }
        )
    untested = [ _display_name(code) for code in _ALL_PLATFORMS if code not in selected ]

    comp_unbranded_counts: Counter[str] = Counter()
    ranking_source = unbranded or rows
    for r in ranking_source:
        for name in r.get("competitor_names") or []:
            if name and str(name).lower() != brand.lower():
                comp_unbranded_counts[str(name)] += 1

    ranking_rows = [{"name": brand, "mentions": int(unbranded_mentioned), "is_target": True}]
    for name, cnt in comp_unbranded_counts.items():
        ranking_rows.append({"name": name, "mentions": int(cnt), "is_target": False})
    ranking_rows.sort(key=lambda r: r["mentions"], reverse=True)
    for i, row in enumerate(ranking_rows):
        row["rank"] = i + 1
        row["rate"] = _pct(row["mentions"], unbranded_total)
    target_rank = next((r["rank"] for r in ranking_rows if r.get("is_target")), None)

    focus_names: list[str] = list(competitors)
    for name, _cnt in comp_unbranded_counts.most_common(6):
        if name.lower() == brand.lower():
            continue
        if all(name.lower() != x.lower() for x in focus_names):
            focus_names.append(name)
        if len(focus_names) >= 6:
            break
    focus_competitors = []
    for name in focus_names:
        mentions = int(comp_unbranded_counts.get(name) or 0)
        rank_row = next((r for r in ranking_rows if str(r.get("name") or "").lower() == name.lower()), None)
        focus_competitors.append(
            {
                "name": name,
                "domain": "",
                "mentions": mentions,
                "unbranded_mentions": mentions,
                "rank": rank_row.get("rank") if rank_row else None,
                "present": mentions > 0,
                "in_ranking": bool(rank_row),
            }
        )

    target_x = _pct(unbranded_mentioned, unbranded_total) if unbranded_total else 0.0
    target_y = _pct(branded_cited, branded_total) if branded_total else 0.0
    target_dr = int(bl.get("rank") or 0) if bl.get("ok") else 0
    bubble_rows = [
        {
            "name": brand,
            "domain": domain,
            "dr": target_dr,
            "organic_traffic": 0,
            "organic_keywords": 0,
            "x_visibility": target_x,
            "y_source_share": target_y,
            "y_is_proxy": False,
            "is_target": True,
        }
    ]
    for name, hits in comp_unbranded_counts.most_common(8):
        if name.lower() == brand.lower():
            continue
        bubble_rows.append(
            {
                "name": name,
                "domain": "",
                "dr": 0,
                "organic_traffic": 0,
                "organic_keywords": 0,
                "x_visibility": _pct(hits, unbranded_total) if unbranded_total else 0.0,
                "y_source_share": 0.0,
                "y_is_proxy": True,
                "is_target": False,
            }
        )

    groups_map: dict[int, dict[str, Any]] = {}
    order: list[int] = []
    for r in rows:
        key = int(r.get("prompt_index") or 0)
        if key not in groups_map:
            order.append(key)
            groups_map[key] = {
                "question": r.get("question") or "",
                "scenario_group": r.get("scenario_group") or "",
                "answers": [],
            }
        grp = groups_map[key]
        if len(str(r.get("question") or "")) > len(str(grp.get("question") or "")):
            grp["question"] = r.get("question")
        grp["answers"].append(
            {
                "platform": _display_name(str(r.get("platform") or "")),
                "queried_as": r.get("question") or "",
                "mentioned": bool(r.get("mentioned")),
                "official_site_cited": bool(r.get("official_site_cited")),
                "semantic_accuracy": bool(r.get("semantic_accuracy")),
                "brand_sentiment": r.get("brand_sentiment") or "neutral",
                "competitor_names": r.get("competitor_names") or [],
                "evidence": "",
                "answer_excerpt": r.get("answer_markdown") or "",
                "answer_markdown": r.get("answer_markdown") or "",
                "answer_sources": r.get("answer_sources") or [],
                "collect_error": r.get("collect_error") or "",
            }
        )
    order.sort()
    prompt_explorer = {
        "note": "",
        "groups": [groups_map[k] for k in order],
    }

    pos = sum(1 for r in rows if r.get("brand_sentiment") == "positive")
    neu = sum(1 for r in rows if r.get("brand_sentiment") == "neutral")
    neg = sum(1 for r in rows if r.get("brand_sentiment") == "negative")
    sent_total = pos + neu + neg
    by_platform_sent: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
    plat_order: list[str] = []
    for r in rows:
        pid = _display_name(str(r.get("platform") or ""))
        if pid not in plat_order:
            plat_order.append(pid)
        sent = str(r.get("brand_sentiment") or "neutral")
        if sent not in ("positive", "negative"):
            sent = "neutral"
        by_platform_sent[pid][sent] += 1

    lost_queries: list[str] = []
    seen_q: set[str] = set()
    for r in unbranded:
        if r.get("mentioned"):
            continue
        q = str(r.get("question") or "").strip()
        if q and q not in seen_q:
            seen_q.add(q)
            lost_queries.append(q)
        if len(lost_queries) >= 3:
            break
    sample_qs: list[str] = []
    seen_s: set[str] = set()
    for r in unbranded:
        q = str(r.get("question") or "").strip()
        if q and q not in seen_s:
            seen_s.add(q)
            sample_qs.append(q)
        if len(sample_qs) >= 3:
            break
    branded_rate = round(_pct(branded_mentioned, branded_total)) if branded_total else 0
    if sample_qs and unbranded_total > 0:
        q_labels = "".join(f"【{q}】" for q in sample_qs) if zh else "; ".join(f"“{q}”" for q in sample_qs)
        cover_headline = (
            f"AI 能识别 {brand}——被点名时应答率 {branded_rate}%。"
            f"但当用户问的是{q_labels}这类尚未决定品牌的问题时，"
            f"{brand} 只出现在 {unbranded_mentioned}/{unbranded_total} 的场景里，"
            f"其中 {unbranded_takeover} 条回答在 {brand} 缺席时出现了至少一个竞品。"
            if zh
            else (
                f"AI recognizes {brand} when named ({branded_rate}%). "
                f"On unbranded questions such as {q_labels}, "
                f"{brand} appears in {unbranded_mentioned}/{unbranded_total} answers, "
                f"with {unbranded_takeover} competitor takeovers when absent."
            )
        )
    else:
        cover_headline = (
            f"{brand} 的 AI 可见性诊断"
            if zh
            else f"AI visibility diagnostic for {brand}"
        )

    today = datetime.now(timezone.utc).date().isoformat()
    business = intro.strip() if intro.strip() else (domain or brand)
    prompt_per_platform = 0
    if selected:
        counts = [sum(1 for r in rows if str(r.get("platform") or "").lower() == code) for code in selected]
        prompt_per_platform = max(counts) if counts else 0
    planned = list(meta.get("prompts") or [])
    if planned:
        prompt_per_platform = len(planned)

    recs = _recommendations(
        brand=brand,
        language=language,
        audit=audit,
        unbranded_mentioned=unbranded_mentioned,
        unbranded_total=unbranded_total,
        branded_cited=branded_cited,
        branded_total=branded_total,
        lost_queries=lost_queries,
        rivals=[n for n, _ in comp_unbranded_counts.most_common(2)] or competitors,
        offsite=offsite,
    )

    has_crawl = bool(audit and (audit.homepage or {}).get("ok"))
    onpage = (audit.onpage if audit else {}) or {}
    json_ld = list((audit.json_ld_types if audit else []) or [])
    if zh:
        expr = (
            f"schema={'可见' if json_ld else '缺失'}；meta={'可见' if onpage.get('description') else '空'}；"
            f"H1={int(onpage.get('h1_count') or 0)}"
            if has_crawl
            else "本轮无可用官网抓取证据，表达层缺口待复测"
        )
        supply = (
            f"外链 {int(bl.get('backlinks') or 0)}、引用域 {int(bl.get('referring_domains') or 0)}、权威分 {int(bl.get('rank') or 0)}"
            if bl.get("ok")
            else "本轮未采集外链 / 自然流量 / 域名权威分，供给层待复测"
        )
        dist = (
            f"无品牌 {unbranded_mentioned}/{unbranded_total}；竞品出现 {unbranded_competitor}/{unbranded_total}；"
            f"缺席且竞品接管 {unbranded_takeover} 次"
        )
        legal = "诊断报告，仅作为现状判断与下一轮复测口径定义，不构成实施承诺、报价或合同条款。"
        tested = [f"{p['display_name']} {p['total_results']}" for p in platform_data] + (["官网抓取证据"] if has_crawl else [])
        if offsite.get("probed"):
            tested += ["YouTube 检索", "Reddit 检索", "Wikipedia 检索"]
        if bl.get("ok"):
            tested.append("外链汇总")
        not_tested = []
        if not bl.get("ok"):
            not_tested.append("外链/DR")
        if not offsite.get("probed"):
            not_tested += ["YouTube", "Reddit", "Wikipedia / 百科"]
        not_tested.append("媒体 / PR 专项")
        proxy = ["跨类目基准雷达（固定对照）"]
        if offsite.get("probed"):
            proxy.append("YouTube/Reddit 检索量为公开搜索估算，不是人工核验清单")
    else:
        expr = (
            f"schema={'present' if json_ld else 'missing'}; meta={'present' if onpage.get('description') else 'empty'}; "
            f"H1={int(onpage.get('h1_count') or 0)}"
            if has_crawl
            else "No usable homepage crawl this run; expression-layer gaps pending retest"
        )
        supply = (
            f"Backlinks {int(bl.get('backlinks') or 0)}, referring domains {int(bl.get('referring_domains') or 0)}, rank {int(bl.get('rank') or 0)}"
            if bl.get("ok")
            else "Backlinks / organic traffic / domain rating were not collected this run"
        )
        dist = (
            f"Unbranded {unbranded_mentioned}/{unbranded_total}; competitor present {unbranded_competitor}/{unbranded_total}; "
            f"takeover when absent {unbranded_takeover}"
        )
        legal = "Diagnostic only. Not an implementation commitment, quote, or contract."
        tested = [f"{p['display_name']} {p['total_results']}" for p in platform_data] + (["Official-site crawl"] if has_crawl else [])
        if offsite.get("probed"):
            tested += ["YouTube search", "Reddit search", "Wikipedia search"]
        if bl.get("ok"):
            tested.append("Backlink summary")
        not_tested = []
        if not bl.get("ok"):
            not_tested.append("Backlinks / DR")
        if not offsite.get("probed"):
            not_tested += ["YouTube", "Reddit", "Wikipedia"]
        not_tested.append("Media / PR audit")
        proxy = ["Cross-category radar baseline"]
        if offsite.get("probed"):
            proxy.append("YouTube/Reddit hit counts are public-search estimates, not a verified inventory")

    return {
        "schema_version": "magup-masked-sales-dashboard-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "brand_name": brand,
        "target_domain": domain,
        "delivery_language": language,
        "cover": {
            "eyebrow": "诊断报告" if zh else "Diagnostic report",
            "headline": cover_headline,
            "business_definition": business,
            "tested_platforms": [_display_name(code) for code in selected],
            "platform_count": len(selected),
            "prompt_count_per_platform": prompt_per_platform,
            "total_answer_samples": total_samples,
            "report_date": today,
            "audience": "本报告供品牌增长、市场与业务负责人快速决策。" if zh else "For brand growth, marketing, and business decision-makers.",
        },
        "executive_kpis": {
            "unbranded_visibility": {"mentioned": unbranded_mentioned, "total": unbranded_total},
            "branded_recognition": {"mentioned": branded_mentioned, "total": branded_total},
            "competitor_takeover_when_target_absent": {
                "count": unbranded_takeover,
                "total_unbranded": unbranded_total,
                "absent_unbranded": max(0, unbranded_total - unbranded_mentioned),
            },
            "domain_rating": {
                "target": int(bl.get("rank") or 0) if bl.get("ok") else 0,
                "competitor_min": 0,
                "competitor_max": 0,
            },
        },
        "top_distribution": {
            "funnel": {
                "tiers": ["我方可见", "需改进 / 被竞品占位", "完全缺席"] if zh else ["Visible", "Weak / competitor", "Absent"],
                "scenarios": [
                    {
                        "name": "品牌提示词" if zh else "Branded prompts",
                        "total": branded_total,
                        "segments": [
                            {"label": "完整可见" if zh else "Fully visible", "count": branded_complete},
                            {"label": "部分可见" if zh else "Partial", "count": max(0, branded_mentioned - branded_complete)},
                            {"label": "品牌缺席" if zh else "Absent", "count": max(0, branded_total - branded_mentioned)},
                        ],
                    },
                    {
                        "name": "无品牌提示词" if zh else "Unbranded prompts",
                        "total": unbranded_total,
                        "segments": [
                            {"label": "我方出现" if zh else "Present", "count": unbranded_mentioned},
                            {"label": "竞品占位" if zh else "Competitor takeover", "count": unbranded_takeover},
                            {"label": "全部缺席" if zh else "All absent", "count": unbranded_all_absent},
                        ],
                    },
                ],
                "denominator": total_samples,
            },
            "scenario_breakdown": {
                "branded": {
                    "total": branded_total,
                    "mentioned": branded_mentioned,
                    "official_site_cited": branded_cited,
                    "semantic_accurate": branded_semantic,
                },
                "unbranded": {
                    "total": unbranded_total,
                    "mentioned": unbranded_mentioned,
                    "competitor_present_when_target_absent": unbranded_takeover,
                    "all_absent": unbranded_all_absent,
                },
            },
        },
        "platform_performance": {"platforms": platform_data, "untested_platforms": untested},
        "authority_radar": {
            "axes": ["官方信源", "百科权威", "媒体覆盖", "社区活跃 (Reddit / 论坛)", "专业度 (评测 / 口碑)"]
            if zh
            else ["Official source", "Encyclopedia", "Media", "Community", "Professional reviews"],
            "target_scores": radar_target,
            "industry_baseline_scores": DEFAULT_INDUSTRY_AUTHORITY,
            "caveat": (
                "官方信源轴来自本轮官网引用率（实测）。百科/媒体/社区/专业度为方向性占位，本轮未独立测试，不是 0 分实绩。"
                if zh
                else "Official-source axis is this run's official-site citation rate. Other axes are directional placeholders, not measured zeros."
            ),
        },
        "source_quality": {
            "scale": "0-100",
            "channels": [
                {
                    "name": name,
                    "target_score": source_target[i],
                    "industry_score": DEFAULT_SOURCE_INDUSTRY[i],
                    "evidence_status": source_status[i] if i < len(source_status) else "not_independently_tested",
                }
                for i, name in enumerate(source_labels)
            ],
        },
        "competitor_gap": {
            "bubble_axes": {
                "x": "无品牌 AI 可见度 (%)" if zh else "Unbranded AI visibility (%)",
                "y": "有品牌问题官网引用率 (%)" if zh else "Branded official-site citation (%)",
            },
            "rows": bubble_rows,
            "dr_ranking": [[r["name"], r["dr"]] for r in bubble_rows],
        },
        "channel_gap_cards": _channel_cards(audit, language, offsite),
        "root_cause_stack": {
            "layers": [
                {"layer": "UPSTREAM · 上游" if zh else "UPSTREAM", "name": "表达根因" if zh else "Expression", "evidence": expr},
                {"layer": "MIDSTREAM · 中游" if zh else "MIDSTREAM", "name": "供给根因" if zh else "Supply", "evidence": supply},
                {"layer": "DOWNSTREAM · 下游" if zh else "DOWNSTREAM", "name": "分发根因" if zh else "Distribution", "evidence": dist},
            ]
        },
        "recommendations": recs,
        "boundary": {
            "tested_evidence": tested,
            "not_independently_tested": not_tested,
            "proxy_estimates": proxy,
            "forbidden": ["把未测渠道写成 0 分实绩"] if zh else ["Treat untested channels as a measured zero"],
            "legal_boundary": legal,
        },
        "sentiment": {
            "positive": pos,
            "neutral": neu,
            "negative": neg,
            "total": sent_total,
            "positive_pct": _pct(pos, sent_total),
            "neutral_pct": _pct(neu, sent_total),
            "negative_pct": _pct(neg, sent_total),
            "by_platform": [
                {"platform": p, **by_platform_sent[p], "total": sum(by_platform_sent[p].values())}
                for p in plat_order
            ],
            "word_cloud": _word_cloud(rows, brand),
        },
        "competitor_ranking": {
            "metric": (
                f"无品牌提问中各品牌出现的回答数（共 {unbranded_total} 条）"
                if zh
                else f"Unbranded answer presence by brand (n={unbranded_total})"
            ),
            "denominator": unbranded_total,
            "counting_unit": "answer_presence_per_brand",
            "total_brands": len(ranking_rows),
            "target_rank": target_rank,
            "rows": ranking_rows,
        },
        "focus_competitors": focus_competitors,
        "prompt_explorer": prompt_explorer,
        "raw_summary": {
            "aeo_summary": {
                "total_results": total_samples,
                "mention_count": sum(1 for r in rows if r.get("mentioned")),
                "official_site_cited_count": sum(1 for r in rows if r.get("official_site_cited")),
            }
        },
    }
