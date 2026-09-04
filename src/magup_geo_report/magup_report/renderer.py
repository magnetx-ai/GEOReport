#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render Magup masked sales dashboard HTML from structured dashboard JSON."""
from __future__ import annotations

import argparse
import base64
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
import copy

from magup_geo_report.magup_report.i18n import (
    SCHEMA_V2,
    flatten_v2_for_render,
    get_ui_strings,
    is_cjk_locale,
    locale_bcp47,
    normalize_locale,
    pending_label as i18n_pending,
    resolve_ui_strings,
    t as i18n_t,
)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TEMPLATE_PATH = Path(__file__).resolve().parent / "template.html"
LOGO_PATH = ASSETS_DIR / "magup-wordmark.png"
LOGO_SVG_PATH = ASSETS_DIR / "magup-mark.svg"
PLATFORM_LOGO_FILES = {
    "chatgpt": ASSETS_DIR / "platform-chatgpt.png",
    "google-ai": ASSETS_DIR / "platform-google-ai.png",
    "perplexity": ASSETS_DIR / "platform-perplexity.png",
    "claude": ASSETS_DIR / "platform-claude.png",
}


COLORS = {
    "target": "#533afd",
    "client_bar": "#533afd",
    "industry_bar": "#8a9bb0",
    "industry": "#8a9bb0",
    "blue": "#0ea5e9",
    "ok": "#0ea5e9",
    "warn": "#f59e0b",
    "risk": "#dc2626",
    "muted": "#a0aec0",
}
COMP_COLORS = ["#533afd", "#0ea5e9", "#f59e0b", "#22c55e", "#64748b", "#7b5fff"]
# Sample-distribution funnel: 3 tiers shared across both scenarios (good / weak / absent).
TIER_COLORS = ["#533afd", "#f59e0b", "#c9d3df"]


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def e(value: Any) -> str:
    return escape("" if value is None else str(value), quote=False)


def _safe_href(url: str) -> str:
    u = str(url or "").strip()
    if not u:
        return ""
    if re.match(r"^https?://", u, re.I):
        return u
    if re.match(r"^www\.", u, re.I):
        return f"https://{u}"
    return ""


def _is_md_table_separator(line: str) -> bool:
    s = line.strip().strip("|").strip()
    if not s:
        return False
    cells = [c.strip() for c in s.split("|")]
    if not cells:
        return False
    return all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells)


def _split_md_table_row(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [c.strip() for c in raw.split("|")]


def render_answer_markdown(md: str) -> str:
    """Render common LLM markdown to safe HTML (no external markdown dependency).

    Supports GFM pipe tables so comparison matrices in model answers render as HTML.
    """
    text = str(md or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    fences: list[str] = []

    def _store_fence(match: re.Match[str]) -> str:
        code = match.group(2) or ""
        fences.append(
            f'<pre class="qa-code"><code>{escape(code.rstrip(), quote=False)}</code></pre>'
        )
        return f"\n@@QA_FENCE_{len(fences) - 1}@@\n"

    text = re.sub(r"```([^\n`]*)\n(.*?)```", _store_fence, text, flags=re.S)

    lines = text.split("\n")
    html_parts: list[str] = []
    list_type: str | None = None
    para: list[str] = []
    i = 0

    def _inline(raw: str) -> str:
        s = escape(raw, quote=False)
        s = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
            r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
            s,
        )
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        # Keep emphasis markers as plain text weight, never italic in the QA modal.
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)
        return s

    def _flush_para() -> None:
        nonlocal para
        if para:
            html_parts.append(f"<p>{_inline(' '.join(para))}</p>")
            para = []

    def _close_list() -> None:
        nonlocal list_type
        if list_type:
            html_parts.append(f"</{list_type}>")
            list_type = None

    def _consume_table(start: int) -> tuple[str, int] | None:
        if start + 1 >= len(lines):
            return None
        header_line = lines[start]
        sep_line = lines[start + 1]
        if "|" not in header_line or not _is_md_table_separator(sep_line):
            return None
        headers = _split_md_table_row(header_line)
        if not headers:
            return None
        rows: list[list[str]] = []
        j = start + 2
        while j < len(lines):
            row_line = lines[j]
            if not row_line.strip() or "|" not in row_line:
                break
            if _is_md_table_separator(row_line):
                j += 1
                continue
            cells = _split_md_table_row(row_line)
            # Pad / trim to header width for ragged LLM tables.
            if len(cells) < len(headers):
                cells = cells + [""] * (len(headers) - len(cells))
            elif len(cells) > len(headers):
                cells = cells[: len(headers)]
            rows.append(cells)
            j += 1
        thead = "".join(f"<th>{_inline(h)}</th>" for h in headers)
        body_rows = []
        for row in rows:
            body_rows.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
        table_html = (
            '<div class="qa-table-wrap"><table class="qa-table">'
            f"<thead><tr>{thead}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody>"
            "</table></div>"
        )
        return table_html, j

    while i < len(lines):
        line = lines[i]
        fence_m = re.fullmatch(r"@@QA_FENCE_(\d+)@@", line.strip())
        if fence_m:
            _flush_para()
            _close_list()
            html_parts.append(fences[int(fence_m.group(1))])
            i += 1
            continue

        if not line.strip():
            _flush_para()
            _close_list()
            i += 1
            continue

        table = _consume_table(i)
        if table:
            _flush_para()
            _close_list()
            html_parts.append(table[0])
            i = table[1]
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            _flush_para()
            _close_list()
            level = len(heading.group(1))
            html_parts.append(f"<h{level}>{_inline(heading.group(2).strip())}</h{level}>")
            i += 1
            continue

        # Markdown thematic break (--- / *** / ___) — must run before list detection.
        if re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})\s*", line.strip()):
            _flush_para()
            _close_list()
            html_parts.append('<hr class="qa-hr"/>')
            i += 1
            continue

        ul = re.match(r"^[-*+]\s+(.*)$", line)
        if ul:
            _flush_para()
            if list_type != "ul":
                _close_list()
                html_parts.append("<ul>")
                list_type = "ul"
            html_parts.append(f"<li>{_inline(ul.group(1).strip())}</li>")
            i += 1
            continue

        ol = re.match(r"^\d+[.)]\s+(.*)$", line)
        if ol:
            _flush_para()
            if list_type != "ol":
                _close_list()
                html_parts.append("<ol>")
                list_type = "ol"
            html_parts.append(f"<li>{_inline(ol.group(1).strip())}</li>")
            i += 1
            continue

        quote = re.match(r"^>\s?(.*)$", line)
        if quote:
            _flush_para()
            _close_list()
            html_parts.append(f"<blockquote>{_inline(quote.group(1).strip())}</blockquote>")
            i += 1
            continue

        _close_list()
        para.append(line.strip())
        i += 1

    _flush_para()
    _close_list()
    return "".join(html_parts)


def _citation_indices_in_answer(answer_md: str) -> set[int]:
    """Parse 1-based footnote markers like [1], [12] (Perplexity / ChatGPT style).

    Ignores 4+ digit groups (e.g. years) and markdown link labels that are not
    pure digits — only bare [n] citation chips count.
    """
    text = str(answer_md or "")
    out: set[int] = set()
    for m in re.finditer(r"\[(\d{1,3})\](?!\()", text):
        n = int(m.group(1))
        if 1 <= n <= 200:
            out.add(n)
    return out


def _source_appears_in_answer(
    *,
    answer_md: str,
    url: str = "",
    domain: str = "",
    source_index: int = 0,
    citation_indices: set[int] | None = None,
    usage: str = "",
) -> bool:
    """Whether a listed source is referenced in the answer body.

    Perplexity (and many LLM answers) cite via [n] chips without writing the
    domain/URL into the prose. Match those by 1-based list order first, then
    fall back to domain/URL substring checks (ChatGPT-style inline links).
    """
    usage_l = str(usage or "").strip().lower()
    if usage_l in {"applied", "cited", "in_answer"}:
        return True

    indices = citation_indices if citation_indices is not None else _citation_indices_in_answer(answer_md)
    if source_index >= 1 and source_index in indices:
        return True

    answer_l = str(answer_md or "").lower()
    if not answer_l:
        return False

    url_l = str(url or "").strip().lower()
    if url_l and url_l in answer_l:
        return True

    domain_l = str(domain or "").strip().lower().removeprefix("www.")
    if not domain_l and url_l:
        try:
            domain_l = re.sub(r"^https?://", "", url_l).split("/")[0].removeprefix("www.")
        except Exception:
            domain_l = ""
    if domain_l and len(domain_l) >= 3 and domain_l in answer_l:
        return True
    return False


def _build_answer_sources_html(
    sources: list[Any],
    data: dict[str, Any],
    *,
    answer_md: str = "",
) -> str:
    items = []
    citation_indices = _citation_indices_in_answer(answer_md)
    source_ord = 0
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or "").strip()
        title = str(src.get("title") or "").strip()
        domain = str(src.get("domain") or "").strip()
        label = title or domain or url
        if not label:
            continue
        source_ord += 1
        href = _safe_href(url)
        if href:
            link = f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'
        else:
            link = e(label)
        meta = f'<span class="qa-src-domain">{e(domain)}</span>' if domain and domain.lower() not in label.lower() else ""
        cited = _source_appears_in_answer(
            answer_md=answer_md,
            url=url,
            domain=domain,
            source_index=source_ord,
            citation_indices=citation_indices,
            usage=str(src.get("usage") or src.get("cite_usage") or ""),
        )
        cite_tag = (
            f'<span class="qa-src-cite on">{e(ui(data, "qa_source_cited"))}</span>'
            if cited
            else f'<span class="qa-src-cite">{e(ui(data, "qa_source_listed"))}</span>'
        )
        items.append(f'<li><div class="qa-src-main">{link}{meta}</div>{cite_tag}</li>')
    if not items:
        return f'<div class="qa-empty">{e(ui(data, "qa_no_sources"))}</div>'
    return f'<ol class="qa-src-list">{"".join(items)}</ol>'


def _answer_mentions_brand(text: str, brand_name: str, aliases: list[str] | None = None) -> bool:
    hay = str(text or "")
    if not hay.strip():
        return False
    hay_l = hay.lower()
    needles: list[str] = []
    for raw in [brand_name, *(aliases or [])]:
        n = str(raw or "").strip()
        if n and n.lower() not in {x.lower() for x in needles}:
            needles.append(n)
    return any(_find_name_in_answer_text(hay_l, n) >= 0 for n in needles)


_COMPETITOR_TOKEN_STOPWORDS = {
    "ai",
    "seo",
    "geo",
    "aeo",
    "llm",
    "brand",
    "radar",
    "toolkit",
    "platform",
    "platforms",
    "tools",
    "tool",
    "suite",
    "visibility",
    "mention",
    "mentions",
    "shadow",
    "marketing",
    "search",
    "chat",
    "gpt",
}


def _competitor_primary_token(name: str) -> str:
    return re.split(r"[\s./_-]+", str(name or "").strip().lower())[0]


def _competitor_name_quality(name: str) -> int:
    """Higher is better for canonical labels (prefer Semrush over long one-off phrases)."""
    text = str(name or "").strip()
    parts = [p for p in re.split(r"[\s./_-]+", text) if p]
    score = 40
    score -= max(0, len(parts) - 2) * 8
    score -= max(0, len(text) - 18)
    if len(parts) == 2 and parts[1].lower().rstrip(".") in {"ai", "io", "hq"}:
        score += 4  # Otterly.AI / Peec AI style
    return score


def _competitor_name_variants(name: str) -> list[str]:
    """Match variants like Otterly.AI ↔ Otterly, Peec AI ↔ Peec."""
    n = str(name or "").strip()
    if not n:
        return []
    variants = [n]
    spaced = re.sub(r"[.]+", " ", n)
    spaced = re.sub(r"\s+", " ", spaced).strip()
    if spaced.lower() not in {v.lower() for v in variants}:
        variants.append(spaced)
    parts = [p for p in re.split(r"[\s./_-]+", n) if p]
    token = parts[0] if parts else ""
    token_l = token.lower()
    allow_token = False
    if token and len(token) >= 4 and token_l not in _COMPETITOR_TOKEN_STOPWORDS:
        if len(parts) == 1:
            allow_token = True
        elif "." in n:
            allow_token = True
        elif parts and all(
            p.lower().rstrip(".") in _COMPETITOR_TOKEN_STOPWORDS
            or p.lower().rstrip(".") in {"ai", "io", "hq", "inc", "llc", "ltd"}
            for p in parts[1:]
        ):
            # Peec AI / Ahrefs Brand Radar / HubSpot AEO → match primary token
            allow_token = True
    if allow_token and token_l not in {v.lower() for v in variants}:
        variants.append(token)
    return variants


def _find_name_in_answer_text(text_l: str, name: str) -> int:
    """Return earliest case-insensitive hit for name variants, else -1."""
    hay = str(text_l or "")
    if not hay:
        return -1
    best = -1
    for variant in _competitor_name_variants(name):
        needle = variant.lower().strip()
        if len(needle) < 3:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
        m = re.search(pattern, hay)
        if m and (best < 0 or m.start() < best):
            best = m.start()
    return best


def _collect_competitor_catalog(data: dict[str, Any], brand_name: str) -> list[str]:
    """Canonical rival names from ranking / focus for recovering missed classifier lists.

    Ranking often stores fragmented labels (Otterly / Otterly.AI / Otterly AI). Collapse
    by primary token, preferring higher mention counts and cleaner labels.
    """
    brand_l = str(brand_name or "").strip().lower()
    best: dict[str, tuple[int, int, str]] = {}

    def _add(raw: Any, mentions: int = 0) -> None:
        name = str(raw or "").strip()
        if not name:
            return
        key = name.lower()
        if key == brand_l:
            return
        token = _competitor_primary_token(name)
        if len(name) < 3 or token in _COMPETITOR_TOKEN_STOPWORDS:
            return
        cluster = token if len(token) >= 4 else key
        quality = _competitor_name_quality(name)
        prev = best.get(cluster)
        cand = (int(mentions or 0), quality, name)
        if prev is None or cand[:2] > prev[:2]:
            best[cluster] = cand

    ranking = data.get("competitor_ranking") if isinstance(data, dict) else None
    if isinstance(ranking, dict):
        for row in ranking.get("rows") or []:
            if not isinstance(row, dict) or row.get("is_target"):
                continue
            mentions_raw = row.get("mentions") or 0
            try:
                mentions = int(mentions_raw)
            except (TypeError, ValueError):
                mentions = 0
            _add(row.get("name"), mentions)

    for row in (data.get("focus_competitors") or []) if isinstance(data, dict) else []:
        if isinstance(row, dict):
            _add(row.get("name") or row.get("brand"), 0)
        else:
            _add(row, 0)

    ordered = sorted(best.values(), key=lambda t: (-t[0], -t[1], t[2].lower()))
    return [name for _m, _q, name in ordered]


def _canonicalize_competitor_label(name: str, catalog: list[str], brand_name: str) -> str | None:
    """Map a free-form rival label onto the canonical catalog name when possible."""
    text = str(name or "").strip()
    if not text:
        return None
    brand_l = str(brand_name or "").strip().lower()
    if text.lower() == brand_l:
        return None
    token = _competitor_primary_token(text)
    if token in _COMPETITOR_TOKEN_STOPWORDS:
        return None
    for canon in catalog or []:
        if canon.lower() == text.lower():
            return canon
        if _competitor_primary_token(canon) == token and len(token) >= 4:
            return canon
    # Keep classifier-only labels if they look like a real brand (not ultra-generic).
    if len(text) >= 3 and token not in _COMPETITOR_TOKEN_STOPWORDS:
        return text
    return None


def _competitors_present_in_answer(
    answer_md: str,
    competitor_names: list[Any],
    catalog: list[str],
    brand_name: str,
) -> list[str]:
    """Merge classifier names + catalog, keep only those that appear in the answer body.

    Classifier often returns [] even when rivals are clearly listed in the answer
    (especially ChatGPT/Perplexity). Ranking/chips must recover from body text.
    """
    text_l = str(answer_md or "").lower()
    brand_l = str(brand_name or "").strip().lower()
    candidates: list[str] = []
    seen: set[str] = set()

    def _push(raw: Any) -> None:
        canon = _canonicalize_competitor_label(str(raw or ""), catalog, brand_name)
        if not canon:
            return
        key = canon.lower()
        if key == brand_l or key in seen:
            return
        seen.add(key)
        candidates.append(canon)

    for raw in list(competitor_names or []) + list(catalog or []):
        _push(raw)

    scored: list[tuple[int, int, str]] = []
    for name in candidates:
        pos = _find_name_in_answer_text(text_l, name)
        if pos < 0:
            continue
        scored.append((pos, -len(name), name))
    scored.sort()

    # Prefer longer canonical labels when variants share a primary token (Otterly vs Otterly.AI).
    out: list[str] = []
    tokens_used: set[str] = set()
    for _pos, _neg_len, name in scored:
        token = _competitor_primary_token(name)
        if token and token in tokens_used:
            continue
        if token:
            tokens_used.add(token)
        out.append(name)
    return out


def _mention_rank_rows(
    *,
    brand_name: str,
    mentioned: bool,
    competitor_names: list[Any],
    answer_md: str,
    competitor_catalog: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Order brand + competitors by first appearance in the answer text when possible.

    Target brand is ranked only when the string appears in the answer body.
    Classifier ``mentioned=true`` without textual evidence is treated as absent
    (guards false positives that confuse the query/title with the answer).
    Competitors are recovered from answer text against the report catalog when
    ``competitor_names`` is empty/incomplete — only names present in the body
    receive a rank (no fake ranks for missing rivals).
    """
    text = str(answer_md or "")
    text_l = text.lower()
    brand = str(brand_name or "").strip()
    brand_pos = _find_name_in_answer_text(text_l, brand) if brand else -1
    brand_in_text = brand_pos >= 0
    # Trust body text over classifier for ranking presence.
    effective_mentioned = bool(mentioned) and brand_in_text

    present_comps = _competitors_present_in_answer(
        text,
        competitor_names,
        competitor_catalog or [],
        brand,
    )

    names: list[tuple[str, bool]] = []
    if brand:
        names.append((brand, True))
    for name in present_comps:
        names.append((name, False))

    scored: list[tuple[int, int, str, bool]] = []
    for idx, (name, is_target) in enumerate(names):
        pos = _find_name_in_answer_text(text_l, name)
        if is_target and not effective_mentioned and pos < 0:
            scored.append((10_000_000 + idx, idx, name, is_target))
        elif pos < 0:
            # Competitors not in body are already filtered; skip any residual.
            continue
        else:
            scored.append((pos, idx, name, is_target))
    scored.sort(key=lambda x: (x[0], x[1]))
    rows = []
    rank = 0
    absent_rows: list[dict[str, Any]] = []
    for pos, _idx, name, is_target in scored:
        absent = is_target and (not brand_in_text or not effective_mentioned)
        if absent:
            absent_rows.append({"name": name, "rank": None, "is_target": True, "absent": True})
            continue
        rank += 1
        rows.append({"name": name, "rank": rank, "is_target": is_target, "absent": False})
    # Show target absence first, then rivals in answer order.
    return absent_rows + rows


def _build_mention_rank_html(rows: list[dict[str, Any]], data: dict[str, Any]) -> str:
    if not rows:
        return f'<div class="qa-empty">{e(ui(data, "qa_no_rank"))}</div>'
    items = []
    for row in rows:
        klass = "target" if row.get("is_target") else ""
        if row.get("absent"):
            rank_lbl = e(ui(data, "qa_rank_absent"))
            klass = f"{klass} absent".strip()
        else:
            rank_lbl = f"#{int(row.get('rank') or 0)}"
        items.append(
            f'<li class="{klass}"><span class="qa-rank-n">{rank_lbl}</span>'
            f'<span class="qa-rank-name">{e(row.get("name"))}</span></li>'
        )
    return f'<ol class="qa-rank-list">{"".join(items)}</ol>'


def tighten_brand_spacing(text: str, brand_name: str) -> str:
    """Collapse spaces around brand only when adjacent to CJK (zh copy style).

    Do NOT strip spaces for Latin locales — that produces glued words like
    ``aMagUpmostra`` from ``a MagUp mostra``.
    """
    if not text or not brand_name:
        return text
    esc = re.escape(brand_name)
    text = re.sub(rf"([\u4e00-\u9fff]) {esc}", rf"\1{brand_name}", text)
    text = re.sub(rf"{esc} ([\u4e00-\u9fff])", rf"{brand_name}\1", text)
    return text


_TX_ALLOWED_INLINE = re.compile(r"&lt;(/?)(b|strong|em|i)\s*&gt;", re.I)
_TX_ALLOWED_BR = re.compile(r"&lt;br\s*/?\s*&gt;", re.I)


def tx(value: Any, brand_name: str) -> str:
    """Escape narrative HTML, then restore a small allowlist of safe tags.

    LLM narrative often wraps metrics/channel names in ``<b>…</b>`` / ``<br/>``.
    Full escaping left those tags visible as literal text in production reports.
    """
    text = tighten_brand_spacing("" if value is None else str(value), brand_name)
    out = e(text)
    out = _TX_ALLOWED_BR.sub("<br/>", out)
    out = _TX_ALLOWED_INLINE.sub(lambda m: f"<{m.group(1)}{m.group(2).lower()}>", out)
    return out


def pct_display(numerator: Any, denominator: Any, digits: int = 1) -> str:
    try:
        n = float(numerator or 0)
        d = float(denominator or 0)
    except (TypeError, ValueError):
        return "0"
    if d <= 0:
        return "0"
    value = 100.0 * n / d
    if digits <= 0:
        return str(int(round(value)))
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    color = (hex_color or "#533afd").lstrip("#")
    if len(color) != 6:
        return f"rgba(83,58,253,{alpha})"
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def num(value: Any, default: str = "0") -> str:
    try:
        if value is None:
            return default
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return default


# GEO-ML-REVIEW:#14 prepare_render_data — 渲染前总闸（ui_copy / boundary / 残差 / scrub）
def prepare_render_data(raw: dict[str, Any], delivery_language: str = "") -> dict[str, Any]:
    locale = normalize_locale(delivery_language or raw.get("delivery_language") or "en")
    # Force delivery language before flatten so pack selection cannot prefer stale default_locale.
    if isinstance(raw, dict):
        raw = dict(raw)
        raw["delivery_language"] = locale
    locales = raw.get("locales") if isinstance(raw.get("locales"), dict) else {}
    has_target_pack = isinstance(locales.get(locale), dict) and bool(locales.get(locale))
    missing_target_pack = bool(locales) and raw.get("schema_version") == SCHEMA_V2 and not has_target_pack

    data = flatten_v2_for_render(raw)
    data["delivery_language"] = locale
    catalog, chrome_fallback = resolve_ui_strings(locale)
    # Catalog wins; for non-zh drop leftover zh chrome keys from packs.
    if is_cjk_locale(locale):
        data["ui_copy"] = {**(data.get("ui_copy") or {}), **catalog}
    else:
        prior = data.get("ui_copy") or {}
        merged = {
            k: v
            for k, v in prior.items()
            if not str(k).endswith("_zh") and not any("\u4e00" <= ch <= "\u9fff" for ch in str(v or ""))
        }
        data["ui_copy"] = {**merged, **catalog}
    if chrome_fallback:
        data["chrome_fallback"] = chrome_fallback
    from magup_geo_report.magup_report.i18n import (
        _default_chart_labels,
        apply_channel_label_locale,
        localize_authority_radar,
        localize_boundary,
        localize_recommendations_effort,
        sanitize_recommendation_prose,
    )

    def localize_prompt_explorer_rationale(explorer, locale, source_locale=None):  # noqa: ARG001
        return explorer

    def _pack_has_residual_source(*_a, **_k):
        return False

    def _collect_residual_items(*_a, **_k):
        return []

    def _llm_translate_text_items(*_a, **_k):
        return {}

    def _apply_translated_items(data, *_a, **_k):
        return data

    def _reject_cjk_for_target(*_a, **_k):
        return False

    def attach_locale_guard(data, **_k):
        return data

    def pack_has_residual_issues(*_a, **_k):
        return False

    def scrub_chrome_only(data, locale):  # noqa: ARG001
        return data

    def display_residual_issues(*_a, **_k):
        return []

    if missing_target_pack:
        data = attach_locale_guard(
            data,
            target_locale=locale,
            retries=0,
            mode="missing_target_pack",
            shipped=False,
            chrome_fallback=chrome_fallback,
            status="failed_locale",
        )
        raise RuntimeError(
            f"prepare_render_data: missing locales[{locale}] pack; refusing silent fallback render"
        )

    source_locale = normalize_locale(
        raw.get("source_locale")
        or data.get("source_locale")
        or ("en" if is_cjk_locale(locale) else "zh-Hans")
    )
    data["chart_labels"] = {
        **(data.get("chart_labels") or {}),
        **_default_chart_labels(locale),
    }
    # Axes/caveat live in shared metrics; always rewrite labels for delivery language.
    data = localize_authority_radar(data, locale)
    # Conclusory boundary notes (not raw prompts / word-cloud).
    if isinstance(data.get("boundary"), dict) or data.get("boundary") is None:
        data["boundary"] = localize_boundary(data.get("boundary") or {}, locale)
    # Effort band is closed-vocabulary chrome — always remap (do not wait for residual gate).
    data = localize_recommendations_effort(data, locale)
    # Recommendation why/metric must be real prose — never CJK-strip punctuation soup.
    data = sanitize_recommendation_prose(data, locale)
    if not is_cjk_locale(locale):
        # Remap structural Chinese channel/axis labels for non-zh delivery.
        data = apply_channel_label_locale(data, locale)
        data = localize_authority_radar(data, locale)

    explorer = data.get("prompt_explorer") or data.get("qa_section")
    if isinstance(explorer, dict):
        localized = localize_prompt_explorer_rationale(
            explorer,
            locale,
            source_locale=source_locale,
        )
        data["prompt_explorer"] = localized
        if "qa_section" in data:
            data["qa_section"] = localized

    if _pack_has_residual_source(data, source_locale, locale):
        residual = _collect_residual_items(data, source_locale, locale)
        if residual:
            localized_fields = _llm_translate_text_items(residual, source_locale, locale)
            if localized_fields:
                data = _apply_translated_items(
                    data,
                    localized_fields,
                    reject_cjk=_reject_cjk_for_target(locale),
                )
                if not is_cjk_locale(locale):
                    data = apply_channel_label_locale(data, locale)

    # Chrome-only scrub: never overwrite LLM narrative/recs with EN templates.
    if pack_has_residual_issues(data, locale):
        data = scrub_chrome_only(data, locale)
        data["delivery_language"] = locale
        data["chart_labels"] = {
            **(data.get("chart_labels") or {}),
            **_default_chart_labels(locale),
        }
        data = apply_channel_label_locale(data, locale)
        data = localize_authority_radar(data, locale)
        data["boundary"] = localize_boundary(data.get("boundary") or {}, locale)

    leftovers = display_residual_issues(data, locale)
    if leftovers or chrome_fallback:
        data = attach_locale_guard(
            data,
            target_locale=locale,
            retries=0,
            mode="scrub_chrome_only",
            shipped=not bool(leftovers),
            chrome_fallback=chrome_fallback,
            status="ok" if not leftovers else "soft_ship",
        )
    return data


def ui(data: dict[str, Any], key: str, **fmt: Any) -> str:
    return i18n_t(data, key, **fmt)


def pct(value: Any, data: dict[str, Any] | None = None) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return i18n_pending(data or {})


def ratio(obj: dict[str, Any], n_key: str = "mentioned", d_key: str = "total") -> str:
    return f"{num(obj.get(n_key))} / {num(obj.get(d_key))}"


def pct_class(n: Any, total: Any) -> str:
    """Performance-based colour class for a ``n / total`` attribute row.

    Higher ratio = better, so colour reflects actual performance instead of a
    blanket per-scenario colour. Used for the branded attribute rows where a low
    ratio (e.g. official-site citation 2/30) must read as a gap, not as ``ok``.
    """
    try:
        n_f, t_f = float(n), float(total)
    except (TypeError, ValueError):
        return "muted"
    if t_f <= 0:
        return "muted"
    r = n_f / t_f * 100
    if r >= 80:
        return "ok"
    if r >= 40:
        return "warn"
    return "risk"


def cite_rate_class(n: Any, total: Any) -> str:
    """Citation-rate colour: >=80% default ink (black), 40-80% warn, <40% risk."""
    try:
        n_f, t_f = float(n), float(total)
    except (TypeError, ValueError):
        return "muted"
    if t_f <= 0:
        return "muted"
    r = n_f / t_f * 100
    if r >= 80:
        return ""
    if r >= 40:
        return "warn"
    return "risk"


def cite_rate_class_from_pct(rate: Any) -> str:
    """Same thresholds as :func:`cite_rate_class`, for pre-computed percentage values."""
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return "muted"
    if r >= 80:
        return ""
    if r >= 40:
        return "warn"
    return "risk"


def _funnel_group_labels(data: dict[str, Any]) -> tuple[str, str]:
    """Canonical branded / unbranded group names for funnel / scenario cards."""
    labels = (data.get("chart_labels") or {}) if data else {}
    branded_name = str(labels.get("funnel_branded") or "")
    unbranded_name = str(labels.get("funnel_unbranded") or "")
    if not branded_name or branded_name in {"品牌问", "有品牌提问"} or "品类" in branded_name:
        branded_name = "品牌词提问" if is_cjk_locale(str(data.get("delivery_language") or "")) else "Branded queries"
    if (
        not unbranded_name
        or "品类" in unbranded_name
        or unbranded_name in {"无品牌问", "无品牌提问", "无品牌提示词"}
    ):
        # Funnel / TOP-distribution wording stays 「不带品牌提问」, distinct from QA tag 「无品牌提示词」.
        unbranded_name = (
            "不带品牌提问" if is_cjk_locale(str(data.get("delivery_language") or "")) else "Non-branded queries"
        )
    return branded_name, unbranded_name


def _apply_funnel_group_labels(funnel: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Force scenario names onto chart_labels / UI chrome (index 0 branded, 1 unbranded).

    Replaces legacy labels such as 品类词提问 with 不带品牌提问 / locale equivalents.
    """
    branded_name, unbranded_name = _funnel_group_labels(data)
    out = dict(funnel)
    scenarios = [dict(s) for s in (funnel.get("scenarios") or [])]
    # Convention from the data builder: first = branded, second = unbranded.
    if scenarios:
        scenarios[0]["name"] = branded_name
    if len(scenarios) > 1:
        scenarios[1]["name"] = unbranded_name
    out["scenarios"] = scenarios
    return out


def build_funnel(data: dict[str, Any]) -> dict[str, Any]:
    """Two-scenario sample funnel for the 100% stacked bar.

    Prefers the explicit ``top_distribution.funnel`` emitted by the data builder.
    Falls back to deriving it from ``scenario_breakdown`` for older JSON files that
    predate the funnel field (uses semantic-accurate as a proxy for "complete").
    """
    top = data.get("top_distribution", {}) or {}
    funnel = top.get("funnel")
    if funnel and funnel.get("scenarios"):
        locale = str(data.get("delivery_language") or "")
        funnel_blob = " ".join(
            [
                *[str(t or "") for t in (funnel.get("tiers") or [])],
                *[
                    str(x or "")
                    for s in funnel.get("scenarios") or []
                    for x in [s.get("name"), *((seg.get("label") for seg in (s.get("segments") or [])))]
                ],
            ]
        )
        if is_cjk_locale(locale) or not re.search(r"[\u4e00-\u9fff]", funnel_blob):
            return _apply_funnel_group_labels(funnel, data)
    sb = top.get("scenario_breakdown", {}) or {}
    b = sb.get("branded", {}) or {}
    u = sb.get("unbranded", {}) or {}
    b_total = int(b.get("total", 0) or 0)
    b_mentioned = int(b.get("mentioned", 0) or 0)
    b_complete = min(b_mentioned, int(b.get("semantic_accurate", 0) or 0))
    u_total = int(u.get("total", 0) or 0)
    u_mentioned = int(u.get("mentioned", 0) or 0)
    u_takeover = int(u.get("competitor_present_when_target_absent", 0) or 0)
    u_absent = int(u.get("all_absent", max(0, u_total - u_mentioned - u_takeover)) or 0)
    labels = (data.get("chart_labels") or {}) if data else {}
    tiers = labels.get("funnel_tiers") or [ui(data, "legend_visible"), ui(data, "legend_improve"), ui(data, "legend_absent")]
    branded_name, unbranded_name = _funnel_group_labels(data)
    seg_branded = [
        {"label": labels.get("funnel_seg_complete") or ui(data, "funnel_seg_complete"), "count": b_complete},
        {"label": labels.get("funnel_seg_partial") or ui(data, "funnel_seg_partial"), "count": max(0, b_mentioned - b_complete)},
        {"label": labels.get("funnel_seg_brand_absent") or ui(data, "funnel_seg_brand_absent"), "count": max(0, b_total - b_mentioned)},
    ]
    seg_unbranded = [
        {"label": labels.get("funnel_seg_mine") or ui(data, "funnel_seg_mine"), "count": u_mentioned},
        {"label": labels.get("funnel_seg_comp") or ui(data, "funnel_seg_comp"), "count": u_takeover},
        {"label": labels.get("funnel_seg_all_blank") or ui(data, "funnel_seg_all_blank"), "count": u_absent},
    ]
    return {
        "tiers": tiers,
        "scenarios": [
            {"name": branded_name, "total": b_total, "segments": seg_branded},
            {"name": unbranded_name, "total": u_total, "segments": seg_unbranded},
        ],
        "denominator": (top.get("donut", {}) or {}).get("denominator", b_total + u_total),
    }


def css_class_for_status(status: str) -> str:
    s = (status or "").lower()
    if s in {"available", "tested", "measured", "proxy_or_tested", "active"}:
        return "measured"
    if s in {"proxy", "proxy_evidence", "代理证据", "partial"}:
        return "proxy"
    if s in {"critical_gap", "gap", "unavailable", "failed", "blocked"}:
        return "gap"
    return "untested"


def label_for_status(status: str, data: dict[str, Any] | None = None) -> str:
    normalized = (status or "").lower()
    status_keys = {
        "available": "status_tested",
        "tested": "status_tested",
        "proxy": "status_proxy",
        "proxy_or_tested": "status_mixed",
        "not_tested": "status_not_tested",
        "not_independently_tested": "status_not_independent",
        "unavailable": "status_unavailable",
        "failed": "status_failed",
        "blocked": "status_blocked",
        "active": "status_detected",
        "partial": "status_partial",
        "not_deployed": "status_not_deployed",
        "critical_gap": "status_critical_gap",
        "gap": "status_critical_gap",
    }
    if data and normalized in status_keys:
        return ui(data, status_keys[normalized])
    mapping = {
        "available": "已实测",
        "tested": "已实测",
        "proxy": "代理证据",
        "proxy_or_tested": "混合证据",
        "active": "已检测",
        "partial": "部分覆盖",
        "not_tested": "本轮未测",
        "not_independently_tested": "未独立测试",
        "not_deployed": "未部署",
        "critical_gap": "严重缺口",
        "gap": "严重缺口",
        "unavailable": "不可用",
        "failed": "采集失败",
        "blocked": "抓取被拦截",
        "pro_only": "pro_only",
    }
    locale = str((data or {}).get("delivery_language") or "")
    if data and not is_cjk_locale(locale):
        en_map = {
            "available": "Measured",
            "tested": "Measured",
            "proxy": "Proxy evidence",
            "proxy_or_tested": "Mixed evidence",
            "active": "Detected",
            "partial": "Partial coverage",
            "not_tested": "Not tested this run",
            "not_independently_tested": "Not independently tested",
            "not_deployed": "Not deployed",
            "critical_gap": "Critical gap",
            "gap": "Critical gap",
            "unavailable": "Unavailable",
            "failed": "Collection failed",
            "blocked": "Crawl blocked",
        }
        return en_map.get(normalized, status or i18n_pending(data))
    return mapping.get(normalized, status or (i18n_pending(data) if data else "待复测"))


def magup_logo_img() -> str:
    if LOGO_PATH.is_file():
        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
        return f'<img src="data:image/png;base64,{encoded}" alt="MagUp" />'
    if LOGO_SVG_PATH.is_file():
        encoded = base64.b64encode(LOGO_SVG_PATH.read_bytes()).decode("ascii")
        return f'<img src="data:image/svg+xml;base64,{encoded}" alt="MagUp" />'
    return ""


def platform_short_label(name: str) -> str:
    low = name.lower()
    if "gpt" in low or "chatgpt" in low or "openai" in low:
        return "ChatGPT"
    if "google" in low or "gemini" in low or "ai_mode" in low or "ai mode" in low:
        return "Gemini"
    if "claude" in low or "anthropic" in low:
        return "Claude"
    if "perplexity" in low:
        return "Perplexity"
    return name.split("·")[0].strip() if "·" in name else name.strip()


def platform_logo_key(name: str) -> str:
    low = name.lower()
    if "gpt" in low or "chatgpt" in low or "openai" in low:
        return "chatgpt"
    if "google" in low or "gemini" in low or "ai_mode" in low or "ai mode" in low:
        return "google-ai"
    if "claude" in low or "anthropic" in low:
        return "claude"
    if "perplexity" in low:
        return "perplexity"
    return ""


def cover_platform_entries(data: dict[str, Any]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for platform in (data.get("platform_performance", {}) or {}).get("platforms", []) or []:
        raw = str(platform.get("display_name") or platform.get("id") or "")
        key = platform_logo_key(raw)
        label = platform_short_label(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        entries.append((key, label))
    if not entries:
        for platform_id in (data.get("cover", {}) or {}).get("tested_platforms", []) or []:
            raw = str(platform_id)
            key = platform_logo_key(raw)
            label = platform_short_label(raw)
            if not key or key in seen:
                continue
            seen.add(key)
            entries.append((key, label))
    return entries


def cover_platform_phrase(data: dict[str, Any], platform_count: Any) -> str:
    labels = [label for _, label in cover_platform_entries(data)]
    count = int(platform_count or len(labels) or 0)
    joined = ", ".join(labels) if not is_cjk_locale(str(data.get("delivery_language") or "")) else "、".join(labels)
    if joined and count > len(labels):
        return ui(data, "cover_platforms_and_more", joined=joined, count=count)
    if joined:
        return joined
    return ui(data, "cover_platforms_count_only", count=count)


def platform_logo_img(key: str, label: str) -> str:
    logo_path = PLATFORM_LOGO_FILES.get(key)
    if not logo_path or not logo_path.is_file():
        return ""
    mime = "image/png" if logo_path.suffix.lower() == ".png" else "image/svg+xml"
    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    return f'<img src="data:{mime};base64,{encoded}" alt="{e(label)}" />'


def build_cover_platform_logos(data: dict[str, Any], prompt_per_platform: Any = 0) -> str:
    rows = []
    for key, label in cover_platform_entries(data):
        img = platform_logo_img(key, label)
        if img:
            mark = f'<span class="platform-logo platform-logo--{e(key)}" title="{e(label)}">{img}</span>'
        else:
            mark = f'<span class="platform-logo-text" title="{e(label)}">{e(label)}</span>'
        rows.append(f'<div class="platform-row">{mark}</div>')
    if not rows:
        return '<span class="meta-platforms-fallback">—</span>'
    try:
        per_platform = int(float(prompt_per_platform or 0))
    except (TypeError, ValueError):
        per_platform = 0
    cover = data.get("cover") or {}
    by_platform = cover.get("prompt_counts_by_platform") or {}
    counts = [int(v or 0) for v in by_platform.values()] if isinstance(by_platform, dict) else []
    uneven = bool(counts) and min(counts) != max(counts)
    if uneven and per_platform:
        note_text = ui(data, "meta_per_platform_prompts_partial", planned=per_platform)
    elif per_platform:
        note_text = ui(data, "meta_per_platform_prompts", count=per_platform)
    else:
        note_text = ""
    note_html = (
        f'<div class="meta-platforms-note"><span class="note-mark">※</span><span>{e(note_text)}</span></div>'
        if note_text
        else ""
    )
    return f'<div class="meta-platforms"><div class="meta-platforms-list">{"".join(rows)}</div>{note_html}</div>'


def platform_card_brand(name: str) -> str:
    raw = str(name)
    key = platform_logo_key(raw)
    label = platform_short_label(raw)
    img = platform_logo_img(key, label) if key else ""
    if img:
        return (
            f'<div class="name">'
            f'<span class="platform-brand-logo platform-brand-logo--{e(key)}" title="{e(label)}">{img}</span>'
            f"</div>"
        )
    return f'<div class="name">{e(label or raw)}</div>'


def build_platform_compare(platforms: list[dict[str, Any]], untested: list[Any], data: dict[str, Any] | None = None) -> str:
    """Per-platform visibility comparison as logo-led HTML bars (no legend).

    Each platform is one row: its logo on the left, then three labelled bars for
    the visibility metrics that share a "higher = better" direction. Bars use the
    platform's brand colour, so the logo identifies the row and no colour legend
    is needed. Replaces the Chart.js radar/grouped-bar legend layout.
    """
    metrics = [
        (ui(data or {}, "compare_unbranded"), "unbranded_visibility_rate"),
        (ui(data or {}, "compare_branded"), "brand_visibility_rate"),
        (ui(data or {}, "compare_competitor_inverse"), "competitor_inverse_score"),
    ]
    rows: list[str] = []
    for p in platforms:
        raw = str(p.get("display_name") or p.get("id") or "")
        key = platform_logo_key(raw)
        label = platform_short_label(raw)
        color = platform_chart_color(str(p.get("id", "")), raw)
        img = platform_logo_img(key, label) if key else ""
        if img:
            logo_html = f'<span class="pc-logo pc-logo--{e(key)}" title="{e(label)}">{img}</span>'
        else:
            logo_html = f'<span class="pc-logo-text">{e(label or raw)}</span>'
        bars = ""
        for m_label, m_key in metrics:
            val = p.get(m_key)
            try:
                w = max(0.0, min(100.0, float(val)))
            except (TypeError, ValueError):
                w = 0.0
            bars += (
                f'<div><div class="pc-head"><span>{e(m_label)}</span>'
                f'<span class="pc-val">{pct(val)}</span></div>'
                f'<div class="pc-track"><div class="pc-fill" style="width:{w}%;background:{color}"></div></div></div>'
            )
        rows.append(
            f'<div class="pc-row"><span class="pc-logo">{logo_html}</span>'
            f'<div class="pc-bars">{bars}</div></div>'
        )
    for name in untested or []:
        raw = str(name)
        key = platform_logo_key(raw)
        label = platform_short_label(raw)
        img = platform_logo_img(key, label) if key else ""
        logo_html = (
            f'<span class="pc-logo pc-logo--{e(key)}" title="{e(label)}">{img}</span>'
            if img else f'<span class="pc-logo-text">{e(label or raw)}</span>'
        )
        rows.append(
            f'<div class="pc-row"><span class="pc-logo">{logo_html}</span>'
            f'<div class="pc-bars"><span class="pc-pending">{e(ui(data or {}, "compare_pending"))}</span></div></div>'
        )
    return f'<div class="plat-compare">{"".join(rows)}</div>'


def platform_class(name: str) -> str:
    low = name.lower()
    if "openai" in low or "gpt" in low or "chat" in low:
        return "openai"
    if "gemini" in low or "google" in low:
        return "gemini"
    if "claude" in low or "anthropic" in low:
        return "claude"
    if "perplexity" in low:
        return "perplexity"
    return "openai"


def platform_chart_color(platform_id: str, display_name: str = "") -> str:
    key = f"{platform_id} {display_name}".lower()
    if "perplexity" in key:
        return "#1a9e80"
    if "claude" in key or "anthropic" in key:
        return "#d97706"
    if "gpt" in key or "openai" in key or "chat" in key:
        return "#533afd"
    return "#0ea5e9"


def build_platform_cards(data: dict[str, Any]) -> str:
    perf = data.get("platform_performance", {})
    cards: list[str] = []
    for p in perf.get("platforms", []) or []:
        name = p.get("display_name") or p.get("id") or "AI Platform"
        cards.append(f"""
      <div class="platform {platform_class(name)}">
        <div class="top">
          {platform_card_brand(name)}
        </div>
        <div class="metrics">
          <div class="m"><div class="k">{e(ui(data, "platform_brand_visibility"))}</div><div class="v {cite_rate_class_from_pct(p.get('brand_visibility_rate'))}">{pct(p.get('brand_visibility_rate'))}</div><div class="sub">{num(p.get('branded_mention_count'))}/{num(p.get('branded_total'))} {e(ui(data, "platform_samples_mentioned"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_unbranded_visibility"))}</div><div class="v {cite_rate_class_from_pct(p.get('unbranded_visibility_rate'))}">{pct(p.get('unbranded_visibility_rate'))}</div><div class="sub">{num(p.get('unbranded_mention_count'))}/{num(p.get('unbranded_total'))} {e(ui(data, "platform_unbranded_samples"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_official_cite"))}</div><div class="v {cite_rate_class_from_pct(p.get('official_site_cited_rate'))}">{pct(p.get('official_site_cited_rate'))}</div><div class="sub">{num(p.get('official_site_cited_count'))}/{num(p.get('unbranded_total'))} {e(ui(data, "platform_cited_official"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_competitor_mentions"))}</div><div class="v risk">{num(p.get('competitor_mention_count'))}</div><div class="sub">{e(ui(data, "platform_competitive_strength", pct=pct(p.get('competitor_inverse_score'))))}</div></div>
        </div>
        <div class="footer-note">{e(ui(data, "platform_footer"))}</div>
      </div>""")
    for name in perf.get("untested_platforms", []) or []:
        cards.append(f"""
      <div class="platform {platform_class(name)} pending">
        <div class="top">
          {platform_card_brand(name)}
          <span class="status pending">{e(ui(data, "platform_pending"))}</span>
        </div>
        <div class="metrics">
          <div class="m"><div class="k">{e(ui(data, "platform_brand_visibility"))}</div><div class="v">— —</div><div class="sub">{e(ui(data, "platform_pending_sub"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_unbranded_visibility"))}</div><div class="v">— —</div><div class="sub">{e(ui(data, "platform_pending_sub"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_official_cite"))}</div><div class="v">— —</div><div class="sub">{e(ui(data, "platform_pending_sub"))}</div></div>
          <div class="m"><div class="k">{e(ui(data, "platform_competitor_mentions"))}</div><div class="v">— —</div><div class="sub">{e(ui(data, "platform_pending_sub"))}</div></div>
        </div>
        <div class="footer-note">{e(ui(data, "platform_untested_note", name=name))}</div>
      </div>""")
    return "\n".join(cards)


def expanded_channel_description(item: dict[str, Any], data: dict[str, Any] | None = None) -> str:
    channel = str(item.get("channel") or "")
    desc = str(item.get("description") or "")
    status = str(item.get("status") or "").lower()
    untested = status in {"not_tested", "not_independently_tested"}
    view = data or {}
    if "Backlinks" in channel or "外链" in channel:
        return ui(view, "ch_desc_backlinks", desc=desc)
    if "YouTube" in channel:
        key = "ch_desc_youtube_untested" if untested else "ch_desc_youtube_tested"
        return ui(view, key, desc=desc) if not untested else ui(view, key)
    if "Reddit" in channel:
        key = "ch_desc_reddit_untested" if untested else "ch_desc_reddit_tested"
        return ui(view, key, desc=desc) if not untested else ui(view, key)
    if "Wikipedia" in channel or "百科" in channel:
        return ui(view, "ch_desc_wikipedia", desc=desc)
    if "Schema" in channel:
        return ui(view, "ch_desc_schema", desc=desc)
    if "Semantic" in channel or "语义标签" in channel:
        return ui(view, "ch_desc_semantic", desc=desc)
    if "Meta" in channel:
        return ui(view, "ch_desc_meta", desc=desc)
    if "llms" in channel.lower():
        return ui(view, "ch_desc_llms", desc=desc)
    return desc


def build_channel_cards(data: dict[str, Any]) -> str:
    items = list(data.get("channel_gap_cards", []) or [])

    def _group_of(item: dict[str, Any]) -> str:
        explicit = str(item.get("group") or "").strip()
        if explicit in {"official_site", "offsite_social"}:
            return explicit
        channel = str(item.get("channel") or "")
        if any(
            token in channel
            for token in ("Schema", "语义", "Semantic", "Meta", "llms")
        ):
            return "official_site"
        return "offsite_social"

    def _render_card(item: dict[str, Any]) -> str:
        status = item.get("status", "")
        muted = " muted" if status in {"not_tested", "not_independently_tested", "not_deployed"} else ""
        return f"""
      <div class="ch-card">
        <div class="tag-row"><span class="ch-name">{e(item.get('channel'))}</span><span class="ch-tag {css_class_for_status(status)}">{e(label_for_status(status, data))}</span></div>
        <div class="ch-big num{muted}">{e(item.get('headline'))}</div>
        <div class="ch-desc">{e(expanded_channel_description(item, data))}</div>
      </div>"""

    official = [item for item in items if _group_of(item) == "official_site"]
    offsite = [item for item in items if _group_of(item) == "offsite_social"]
    # Backward-compatible fallback when older packs still use the previous order.
    if not official and not offsite and items:
        official, offsite = items[4:8], items[:4]

    blocks: list[str] = []
    if official:
        cards = "\n".join(_render_card(item) for item in official)
        blocks.append(
            f"""
    <div class="channel-group channel-group--official">
      <div class="channel-group-head">
        <div class="channel-group-kicker">{e(ui(data, "channel_group_official_kicker"))}</div>
        <div class="channel-group-title">{e(ui(data, "channel_group_official_title"))}</div>
        <div class="channel-group-note">{e(ui(data, "channel_group_official_note"))}</div>
      </div>
      <div class="status-grid">{cards}</div>
    </div>"""
        )
    if offsite:
        cards = "\n".join(_render_card(item) for item in offsite)
        blocks.append(
            f"""
    <div class="channel-group channel-group--offsite">
      <div class="channel-group-head">
        <div class="channel-group-kicker">{e(ui(data, "channel_group_offsite_kicker"))}</div>
        <div class="channel-group-title">{e(ui(data, "channel_group_offsite_title"))}</div>
        <div class="channel-group-note">{e(ui(data, "channel_group_offsite_note"))}</div>
      </div>
      <div class="status-grid">{cards}</div>
    </div>"""
        )
    return f'<div class="channel-groups">{"".join(blocks)}</div>'

def build_recommendations(data: dict[str, Any]) -> str:
    rows = []
    markup_actions = {
        ui(data, "recs_site_markup_action_zh"),
        ui(data, "recs_site_markup_action_en"),
        "站点机器可读性补全",
        "官网结构化标记补全",
        "官网机器可读性与页面结构补强",
        "恢复官网可抓取并完成机器可读性审计",
        "Strengthen on-site machine readability and page structure",
        "Complete on-site structured markup",
        "Restore crawl access and audit on-site machine readability",
    }
    content_actions = {
        ui(data, "recs_site_content_action_zh"),
        ui(data, "recs_site_content_action_en"),
        "官网可引用内容与信息架构建设",
        "无品牌品类入口页建设（官网）",
        "无品牌品类入口页建设",
        "Build citable on-site content and information architecture",
        "Build unbranded category landing pages on the official site",
        "Build unbranded category landing pages",
    }
    for rec in data.get("recommendations", []) or []:
        pri = rec.get("priority", "")
        pri_class = "pri-1" if pri == "P0" else ("pri-2" if pri == "P1" else "pri-3")
        action = str(rec.get("action") or "")
        brand = str(data.get("brand_name") or ui(data, "default_target_brand"))
        if action in markup_actions:
            action_extra = (
                f'<br/><span style="color:var(--muted);font-size:12px">{e(ui(data, "recs_site_markup_hint"))}</span>'
            )
        elif action in content_actions:
            action_extra = (
                f'<br/><span style="color:var(--muted);font-size:12px">{e(ui(data, "recs_site_content_hint"))}</span>'
            )
        else:
            action_extra = ""
        rows.append(f"""
        <tr>
          <td class="pri {pri_class}">{e(pri)}</td>
          <td>{tx(action, brand)}{action_extra}</td>
          <td>{tx(rec.get('why'), brand)}</td>
          <td class="gain">{tx(rec.get('expected_metric_change'), brand)}</td>
          <td>{e(rec.get('effort_band'))}</td>
        </tr>""")
    return "\n".join(rows)


def expanded_root_evidence(layer: dict[str, Any], data: dict[str, Any] | None = None) -> str:
    name = str(layer.get("name") or "")
    evidence = str(layer.get("evidence") or "")
    view = data or {}
    brand = str(view.get("brand_name") or ui(view, "default_target_brand"))
    nc = view.get("narrative_copy") or {}
    if "表达" in name or "Expression" in name or "Expressão" in name or "Expressao" in name:
        if nc.get("root_cause_expression") or nc.get("root_cause_表达"):
            return tighten_brand_spacing(nc.get("root_cause_expression") or nc["root_cause_表达"], brand)
        return tighten_brand_spacing(ui(view, "fallback_root_expression", brand=brand, evidence=evidence), brand)
    if "供给" in name or "Supply" in name or "Suprimento" in name or "Oferta" in name:
        if nc.get("root_cause_supply") or nc.get("root_cause_供给"):
            return tighten_brand_spacing(nc.get("root_cause_supply") or nc["root_cause_供给"], brand)
        return tighten_brand_spacing(ui(view, "fallback_root_supply", brand=brand, evidence=evidence), brand)
    if "分发" in name or "Distribution" in name or "Distribuição" in name or "Distribuicao" in name:
        if nc.get("root_cause_distribution") or nc.get("root_cause_分发"):
            return tighten_brand_spacing(nc.get("root_cause_distribution") or nc["root_cause_分发"], brand)
        return tighten_brand_spacing(ui(view, "fallback_root_distribution", brand=brand, evidence=evidence), brand)
    return tighten_brand_spacing(evidence, brand)


def build_root_stack(data: dict[str, Any]) -> str:
    layers = (data.get("root_cause_stack", {}) or {}).get("layers", []) or []
    html = []
    for idx, layer in enumerate(layers[:3]):
        arrow = '<div class="arrow">→</div>' if idx < min(len(layers), 3) - 1 else ""
        brand = str(data.get("brand_name") or ui(data, "default_target_brand"))
        ev = tx(expanded_root_evidence(layer, data), brand)
        ev = re.sub(r"(\d+\s*/\s*\d+|\d+)", r'<span class="ev-num">\1</span>', ev)
        html.append(f"""
      <div class="root">
        <div class="layer">{e(layer.get('layer'))}</div>
        <div class="name">{e(layer.get('name'))}</div>
        <p class="ev">{ev}</p>
        {arrow}
      </div>""")
    return "\n".join(html)

# GEO-ML-REVIEW:#20 build_boundary — HTML 底部「数据说明 / DATA NOTES」
def build_boundary(data: dict[str, Any]) -> str:
    b = data.get("boundary", {}) or {}
    sep = "、" if is_cjk_locale(str(data.get("delivery_language") or "")) else ", "
    tested = sep.join(str(x) for x in b.get("tested_evidence", []) or [])
    not_tested = sep.join(str(x) for x in b.get("not_independently_tested", []) or [])
    proxy = sep.join(str(x) for x in b.get("proxy_estimates", []) or [])
    legal = b.get("legal_boundary") or ui(data, "boundary_legal")
    if isinstance(legal, str) and ("诊断报告" in legal or "本报告" in legal or "This report" in legal):
        legal = ui(data, "boundary_legal")
    not_tested_li = (
        f'      <li><b>{e(ui(data, "boundary_not_tested"))}</b>{e(ui(data, "boundary_not_tested_note"))}：{e(not_tested)}。</li>\n'
        if not_tested else ""
    )
    return f"""
  <div class="boundary">
    <h4>{e(ui(data, "boundary_title"))}</h4>
    <ul>
      <li><b>{e(ui(data, "boundary_tested"))}</b>{e(tested)}。</li>
{not_tested_li}      <li><b>{e(ui(data, "boundary_proxy"))}</b>{e(ui(data, "boundary_proxy_note"))}：{e(proxy)}。</li>
      <li>{e(ui(data, "boundary_scope"))}</li>
      <li>{e(legal)}</li>
    </ul>
  </div>"""


def _funnel_seg_count(scenario: dict[str, Any], index: int) -> int:
    segs = scenario.get("segments") or []
    if index >= len(segs):
        return 0
    return int((segs[index] or {}).get("count", 0) or 0)


def build_sample_distribution_split(
    branded: dict[str, Any],
    funnel: dict[str, Any],
    data: dict[str, Any],
    total_samples: Any,
) -> str:
    """Two-column TOP-distribution: branded parent+children | unbranded total."""
    scenarios = funnel.get("scenarios") or []
    b_scen = scenarios[0] if scenarios else {}
    u_scen = scenarios[1] if len(scenarios) > 1 else {}
    b_total = int(b_scen.get("total") or branded.get("total") or 0)
    u_total = int(u_scen.get("total") or 0)
    try:
        total_n = int(total_samples or 0)
    except (TypeError, ValueError):
        total_n = 0
    if total_n <= 0:
        total_n = b_total + u_total
    u_comp = _funnel_seg_count(u_scen, 1)
    u_blank = _funnel_seg_count(u_scen, 2)
    absent_n = u_comp + u_blank
    return (
        f'<div class="funnel-split">'
        f'<div class="funnel-pane funnel-pane--branded">'
        f'<div class="funnel-pane-kicker">{e(ui(data, "scenario_group_kicker_branded", count=num(b_total), total=num(total_n)))}</div>'
        f'<div class="funnel-pane-title">{e(ui(data, "scenario_group_branded", total=num(b_total)))}</div>'
        f'<div class="chart-wrap funnel-bar funnel-bar--parent"><canvas id="sampleBarRecognized"></canvas></div>'
        f'<div class="funnel-children">'
        f'<div class="funnel-children-note">{e(ui(data, "scenario_children_note", total=num(b_total)))}</div>'
        f'<div class="chart-wrap funnel-bar funnel-bar--child"><canvas id="sampleBarBranded"></canvas></div>'
        f'<div class="chart-wrap funnel-bar funnel-bar--child"><canvas id="sampleBarCited"></canvas></div>'
        f"</div></div>"
        f'<div class="funnel-pane funnel-pane--unbranded">'
        f'<div class="funnel-pane-kicker">{e(ui(data, "scenario_group_kicker_unbranded", count=num(u_total), total=num(total_n)))}</div>'
        f'<div class="funnel-pane-title">{e(ui(data, "scenario_group_unbranded", total=num(u_total)))}</div>'
        f'<div class="chart-wrap funnel-bar funnel-bar--parent"><canvas id="sampleBarUnbranded"></canvas></div>'
        f'<div class="funnel-pane-note">{e(ui(data, "scenario_unbranded_gap_note", comp_pct=pct_display(u_comp, u_total, digits=0), blank_pct=pct_display(u_blank, u_total, digits=0), absent_pct=pct_display(absent_n, u_total, digits=0)))}</div>'
        f"</div></div>"
    )


def build_branded_scenario_attrs(branded: dict[str, Any], data: dict[str, Any]) -> str:
    """Deprecated alias — split layout now owns both scenario panes."""
    funnel = build_funnel(data)
    total = (data.get("cover") or {}).get("total_answer_samples") or funnel.get("denominator")
    return build_sample_distribution_split(branded, funnel, data, total)


def _binary_attr_bar_payload(
    row_label: str,
    yes_count: int,
    total: int,
    yes_seg_label: str,
    no_seg_label: str,
    bar_thickness: int = 28,
) -> tuple[list[str], list[dict[str, Any]]]:
    """100% stacked bar payload (yes=purple / no=grey) matching sampleBar* style."""
    yes_n = max(0, int(yes_count or 0))
    tot = max(0, int(total or 0))
    no_n = max(0, tot - yes_n)
    labels = [row_label]

    def _seg(label: str, count: int, color: str) -> dict[str, Any]:
        return {
            "label": label,
            "data": [round(count / tot * 100, 1) if tot else 0],
            "counts": [count],
            "totals": [tot],
            "segLabels": [label],
            "backgroundColor": color,
            "borderColor": "#fff",
            "borderWidth": 2,
            "barThickness": bar_thickness,
        }

    return labels, [
        _seg(yes_seg_label, yes_n, TIER_COLORS[0]),
        _seg(no_seg_label, no_n, TIER_COLORS[2]),
    ]


def build_scenario_detail_card(branded: dict[str, Any], unbranded: dict[str, Any], data: dict[str, Any]) -> str:
    """Deprecated layout helper (right card removed). Kept for callers/tests."""
    return build_branded_scenario_attrs(branded, data)


def _senti_pill(kind: str, data: dict[str, Any] | None = None) -> str:
    view = data or {}
    key_map = {"positive": "senti_positive", "neutral": "senti_neutral", "negative": "senti_negative"}
    klass_map = {"positive": "ok", "neutral": "neutral", "negative": "risk"}
    icon_map = {"positive": "▲", "neutral": "●", "negative": "▼"}
    normalized = str(kind or "neutral").lower()
    if normalized not in key_map:
        normalized = "neutral"
    label = ui(view, key_map[normalized])
    klass = klass_map[normalized]
    icon = icon_map[normalized]
    return (
        f'<span class="senti-pill {klass}" title="{e(label)}">'
        f'<span class="senti-ico" aria-hidden="true">{icon}</span>{e(label)}</span>'
    )


def _normalize_sentiment(value: Any) -> str:
    sent = str(value or "neutral").lower()
    return sent if sent in {"positive", "neutral", "negative"} else "neutral"


def _aggregate_group_sentiment(answers: list[dict[str, Any]]) -> str:
    """Row-level sentiment: negative wins, else positive if any, else neutral."""
    kinds = {_normalize_sentiment(a.get("brand_sentiment")) for a in answers}
    if "negative" in kinds:
        return "negative"
    if "positive" in kinds:
        return "positive"
    return "neutral"


def _is_partial_visible(answer: dict[str, Any], brand_name: str = "") -> bool:
    """Branded-funnel rule: mentioned + brand in answer body + semantic_accuracy false.

    Requires textual brand evidence so classifier false-positives (brand only in
    query/title) do not show as「部分可见」.
    """
    if not answer.get("mentioned"):
        return False
    if "semantic_accuracy" not in answer:
        return False
    if bool(answer.get("semantic_accuracy")):
        return False
    text = str(answer.get("answer_markdown") or answer.get("answer_excerpt") or "")
    if brand_name and not _answer_mentions_brand(text, brand_name):
        return False
    return True


def _partial_visible_badge(data: dict[str, Any]) -> str:
    label = ui(data, "qa_badge_partial_visible")
    return (
        f'<span class="qa-b warn qa-partial" title="{e(label)}">'
        f'<span class="qa-partial-ico" aria-hidden="true">◐</span>{e(label)}</span>'
    )


def _word_cloud_terms(cloud: dict[str, Any], polarity: str) -> list[dict[str, Any]]:
    rows = cloud.get(polarity) if isinstance(cloud.get(polarity), list) else []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        count = max(1, int(row.get("count") or row.get("weight") or 1))
        weight = max(1, int(row.get("weight") or count))
        out.append({"text": text, "count": count, "weight": weight})
    return out


def _render_word_cloud_tags_html(terms: list[dict[str, Any]], polarity: str, tip_tpl: str) -> str:
    """Server-rendered weighted tags so the cloud is visible without JS/CDN."""
    if not terms:
        return ""
    max_w = max(int(t["weight"]) for t in terms) or 1
    klass = {"positive": "pos", "neutral": "neu", "negative": "neg"}.get(polarity, "pos")
    bits: list[str] = ['<div class="senti-cloud-fallback">']
    for t in terms:
        ratio = float(t["weight"]) / float(max_w)
        size = 14 + int(round(ratio * 22))
        tip = tip_tpl.replace("{count}", str(t["count"]))
        bits.append(
            f'<span class="senti-cloud-tag {klass}" style="font-size:{size}px" title="{e(tip)}">{e(t["text"])}</span>'
        )
    bits.append("</div>")
    return "".join(bits)


def build_sentiment_section(data: dict[str, Any], brand_name: str) -> str:
    """SECTION · sentiment — positive / neutral / negative ratios + word cloud."""
    s = data.get("sentiment") or {}
    total = int(s.get("total", 0) or 0)
    pos, neu, neg = int(s.get("positive", 0) or 0), int(s.get("neutral", 0) or 0), int(s.get("negative", 0) or 0)
    pos_pct, neu_pct, neg_pct = s.get("positive_pct", 0), s.get("neutral_pct", 0), s.get("negative_pct", 0)
    pos_lbl, neu_lbl, neg_lbl = ui(data, "senti_positive"), ui(data, "senti_neutral"), ui(data, "senti_negative")
    bar = (
        f'<div class="senti-bar">'
        f'<span class="seg ok" style="width:{pos_pct}%" title="{e(pos_lbl)} {pos}"></span>'
        f'<span class="seg neutral" style="width:{neu_pct}%" title="{e(neu_lbl)} {neu}"></span>'
        f'<span class="seg risk" style="width:{neg_pct}%" title="{e(neg_lbl)} {neg}"></span>'
        f'</div>'
    )
    stat = (
        '<div class="senti-stats">'
        f'<div class="senti-stat"><div class="sv ok">{pct(pos_pct)}</div><div class="sl">{e(ui(data, "senti_stat_line", label=pos_lbl, count=num(pos)))}</div></div>'
        f'<div class="senti-stat"><div class="sv">{pct(neu_pct)}</div><div class="sl">{e(ui(data, "senti_stat_line", label=neu_lbl, count=num(neu)))}</div></div>'
        f'<div class="senti-stat"><div class="sv risk">{pct(neg_pct)}</div><div class="sl">{e(ui(data, "senti_stat_line", label=neg_lbl, count=num(neg)))}</div></div>'
        '</div>'
    )
    plat_rows = ""
    for p in s.get("by_platform", []) or []:
        pt = int(p.get("total", 0) or 0)
        pp = round(p.get("positive", 0) / pt * 100, 1) if pt else 0
        pn = round(p.get("neutral", 0) / pt * 100, 1) if pt else 0
        pg = round(p.get("negative", 0) / pt * 100, 1) if pt else 0
        plat_rows += (
            f'<div class="senti-plat"><div class="pp-name">{e(p.get("platform"))}</div>'
            f'<div class="senti-bar sm"><span class="seg ok" style="width:{pp}%"></span>'
            f'<span class="seg neutral" style="width:{pn}%"></span>'
            f'<span class="seg risk" style="width:{pg}%"></span></div>'
            f'<div class="pp-cnt">{e(ui(data, "senti_plat_counts", pos=num(p.get("positive")), neu=num(p.get("neutral")), neg=num(p.get("negative"))))}</div></div>'
        )
    if total:
        insight = ui(
            data,
            "senti_insight_with_data",
            total=num(total),
            pos=num(pos),
            pos_pct=pct(pos_pct),
            neg=num(neg),
            neg_pct=pct(neg_pct),
            brand_name=brand_name,
            neu_pct=pct(neu_pct),
        )
    else:
        insight = ui(data, "senti_insight_no_data")

    cloud = s.get("word_cloud") if isinstance(s.get("word_cloud"), dict) else {}
    empty_reason = str(cloud.get("empty_reason") or "").strip()
    empty_map = {
        "artifact_missing": "senti_cloud_empty_missing",
        "artifact_unreadable": "senti_cloud_empty_missing",
        "no_pos_neg_answers": "senti_cloud_empty_no_answers",
        "no_mentioned_answers": "senti_cloud_empty_no_answers",
        "no_phrases_extracted": "senti_cloud_empty_no_phrases",
    }
    empty_key = empty_map.get(empty_reason, "senti_cloud_empty_generic")
    empty_msg = e(ui(data, empty_key))
    tip_tpl = ui(data, "senti_cloud_tooltip_count")
    term_counts = {polarity: len(_word_cloud_terms(cloud, polarity)) for polarity in ("positive", "neutral", "negative")}
    default_polarity = max(
        ("positive", "neutral", "negative"),
        key=lambda key: (term_counts[key], {"neutral": 2, "positive": 1, "negative": 0}[key]),
    )
    if not any(term_counts.values()):
        default_polarity = "positive"
    panes: list[str] = []
    for polarity in ("positive", "neutral", "negative"):
        active = polarity == default_polarity
        terms = _word_cloud_terms(cloud, polarity)
        tags = _render_word_cloud_tags_html(terms, polarity, tip_tpl)
        show_empty = not terms
        empty_hidden = "" if show_empty else " hidden"
        active_attr = " is-active" if active else ""
        hidden_attr = "" if active else " hidden"
        panes.append(
            f'<div class="senti-cloud-pane{active_attr}" data-polarity="{polarity}"{hidden_attr}>'
            f'<div class="senti-cloud-canvas" data-cloud-host="1">{tags}</div>'
            f'<div class="senti-cloud-empty"{empty_hidden}>{empty_msg if show_empty else e(ui(data, "senti_cloud_empty_generic"))}</div>'
            f"</div>"
        )
    def _tab(polarity: str, label: str) -> str:
        on = polarity == default_polarity
        return (
            f'<button type="button" class="senti-cloud-tab{" active" if on else ""}" data-polarity="{polarity}" '
            f'role="tab" aria-selected="{"true" if on else "false"}">{e(label)}</button>'
        )
    cloud_block = f"""
    <div class="card senti-cloud-card">
      <h3>{e(ui(data, "senti_cloud_title"))} <span class="badge tested">{e(ui(data, "senti_cloud_badge"))}</span></h3>
      <div class="h-note">{e(ui(data, "senti_cloud_note", brand_name=brand_name))}</div>
      <div class="senti-cloud-tabs" role="tablist">
        {_tab("positive", ui(data, "senti_cloud_tab_positive"))}
        {_tab("neutral", ui(data, "senti_cloud_tab_neutral"))}
        {_tab("negative", ui(data, "senti_cloud_tab_negative"))}
      </div>
      <div class="senti-cloud-wrap" id="sentiWordCloud">
        {"".join(panes)}
      </div>
    </div>"""

    return f"""
  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_03_no"))}</div><h2 class="sec-title">{e(ui(data, "section_03_title", brand_name=brand_name))}</h2><p class="sec-desc">{e(ui(data, "section_03_desc", brand_name=brand_name))}</p></div></div>
    <div class="grid-asym">
      <div class="card"><h3>{e(ui(data, "senti_overall_title"))} <span class="badge tested">{e(ui(data, "badge_data_samples", count=num(total)))}</span></h3><div class="h-note">{e(ui(data, "senti_overall_note", total=num(total)))}</div>{stat}{bar}<div class="legend"><span><i style="background:#0ea5e9"></i>{e(pos_lbl)}</span><span><i style="background:#8a9bb0"></i>{e(neu_lbl)}</span><span><i style="background:#dc2626"></i>{e(neg_lbl)}</span></div></div>
      <div class="card"><h3>{e(ui(data, "senti_platform_title"))}</h3><div class="h-note">{e(ui(data, "senti_platform_note"))}</div><div class="senti-plats">{plat_rows}</div></div>
    </div>
    {cloud_block}
    <div class="insight"><p class="lead">{tx(insight, brand_name)}</p></div>
  </section>
"""


def build_focus_competitors_block(data: dict[str, Any]) -> str:
    items = [row for row in (data.get("focus_competitors") or []) if isinstance(row, dict)]
    if not items:
        return ""
    chips = []
    for row in items:
        name = str(row.get("name") or row.get("input") or "").strip()
        if not name:
            continue
        domain = str(row.get("domain") or "").strip()
        mentions = row.get("unbranded_mentions")
        rank = row.get("rank")
        meta_bits = []
        if domain and domain.lower() not in name.lower():
            meta_bits.append(domain)
        if mentions is not None:
            meta_bits.append(ui(data, "focus_comp_mentions", count=num(mentions)))
        if rank:
            meta_bits.append(ui(data, "focus_comp_rank", rank=rank))
        elif row.get("in_ranking") is False:
            meta_bits.append(ui(data, "focus_comp_absent"))
        meta = f'<span class="focus-comp-meta">{e(" · ".join(meta_bits))}</span>' if meta_bits else ""
        chips.append(f'<span class="focus-comp-chip"><span class="focus-comp-name">{e(name)}</span>{meta}</span>')
    if not chips:
        return ""
    return f"""
    <div class="focus-comp-panel">
      <div class="focus-comp-head">
        <div class="focus-comp-kicker">{e(ui(data, "focus_comp_kicker"))}</div>
        <div class="focus-comp-title">{e(ui(data, "focus_comp_title"))}</div>
        <div class="focus-comp-note">{e(ui(data, "focus_comp_note"))}</div>
      </div>
      <div class="focus-comp-chips">{"".join(chips)}</div>
    </div>"""


def build_ranking_section(data: dict[str, Any], brand_name: str) -> str:
    cr = data.get("competitor_ranking") or {}
    rows = cr.get("rows", []) or []
    target_rank = cr.get("target_rank")
    total_brands = cr.get("total_brands", len(rows))
    denom = cr.get("denominator", 0)
    max_m = max((int(r.get("mentions", 0) or 0) for r in rows), default=1) or 1
    top_n = 12
    you_tag = f'<span class="you">{e(ui(data, "rank_you_tag"))}</span>'
    focus_tag = f'<span class="focus">{e(ui(data, "rank_focus_tag"))}</span>'
    focus_names = {
        str(row.get("name") or "").strip().lower()
        for row in (data.get("focus_competitors") or [])
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    }
    focus_domains = {
        str(row.get("domain") or "").strip().lower()
        for row in (data.get("focus_competitors") or [])
        if isinstance(row, dict) and str(row.get("domain") or "").strip()
    }

    def _is_focus(r: dict[str, Any]) -> bool:
        name = str(r.get("name") or "").strip().lower()
        if not name:
            return False
        if name in focus_names:
            return True
        return any(dom and dom in name for dom in focus_domains)

    def _rank_row_html(r: dict[str, Any]) -> str:
        is_t = bool(r.get("is_target"))
        is_f = (not is_t) and _is_focus(r)
        w = round(int(r.get("mentions", 0) or 0) / max_m * 100, 1)
        cls = " target" if is_t else (" focus" if is_f else "")
        name_html = e(r.get("name"))
        if is_t:
            name_html += you_tag
        elif is_f:
            name_html += focus_tag
        return (
            f'<div class="rank-row{cls}">'
            f'<div class="rk">#{r.get("rank")}</div>'
            f'<div class="rn">{name_html}</div>'
            f'<div class="rbar"><span style="width:{w}%"></span></div>'
            f'<div class="rc">{e(ui(data, "rank_count_line", mentions=num(r.get("mentions")), rate=pct(r.get("rate"))))}</div>'
            f'</div>'
        )

    visible = list(rows[:top_n])
    target_row = next((r for r in rows if r.get("is_target")), None)
    target_in_visible = any(bool(r.get("is_target")) for r in visible)
    # Also surface focus competitors outside top-N.
    focus_extra = []
    visible_names = {str(r.get("name") or "").strip().lower() for r in visible}
    for r in rows:
        if _is_focus(r) and str(r.get("name") or "").strip().lower() not in visible_names:
            focus_extra.append(r)
    items = "".join(_rank_row_html(r) for r in visible)
    if focus_extra or (target_row is not None and not target_in_visible):
        items += (
            '<div class="rank-row gap" aria-hidden="true">'
            '<div class="rk">···</div>'
            '<div class="rn"></div>'
            '<div class="rbar"></div>'
            '<div class="rc"></div>'
            '</div>'
        )
    for r in focus_extra:
        items += _rank_row_html(r)
    if target_row is not None and not target_in_visible:
        items += _rank_row_html(target_row)
    rank_phrase = ui(data, "rank_phrase", rank=target_rank) if target_rank else ui(data, "rank_not_listed")
    bn = e(tighten_brand_spacing(brand_name, brand_name))
    if target_rank:
        headline = ui(
            data,
            "rank_headline_ranked",
            total_brands=num(total_brands),
            brand_name=bn,
            rank_phrase=rank_phrase,
        )
    else:
        headline = ui(data, "rank_headline_unranked", total_brands=num(total_brands), brand_name=bn)
    focus_block = build_focus_competitors_block(data)
    return f"""
  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_08_no"))}</div><h2 class="sec-title">{e(ui(data, "section_08_title"))}</h2><p class="sec-desc">{e(ui(data, "section_08_desc", brand_name=brand_name, denom=num(denom)))}</p></div></div>
    {focus_block}
    <div class="card"><h3>{e(ui(data, "rank_card_title"))} <span class="badge tested">DATA · {e(ui(data, "rank_card_badge", denom=num(denom)))}</span></h3><div class="h-note">{e(ui(data, "rank_card_note", brand_name=brand_name))}</div><div class="rank-list">{items}</div></div>
    <div class="insight"><p class="lead">{tx(headline, brand_name)}</p></div>
  </section>
"""


CITE_RANK_DISPLAY_LIMIT = 30


def _official_report_domain(data: dict[str, Any]) -> str:
    raw = str(data.get("target_domain") or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    return raw.split("/")[0].split("?")[0].removeprefix("www.")


def _cite_rank_is_official(domain: str, official_domain: str) -> bool:
    if not official_domain or not domain:
        return False
    return domain == official_domain or domain.endswith("." + official_domain)


def _cite_rank_url_items(urls: list[Any], data: dict[str, Any]) -> str:
    items: list[str] = []
    for src in urls or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or "").strip()
        title = str(src.get("title") or "").strip()
        label = title or url
        if not label:
            continue
        href = _safe_href(url)
        count = ui(data, "cite_rank_count", count=num(src.get("count")))
        if href:
            link = f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{e(label)}</a>'
        else:
            link = e(label)
        display_url = url or href
        url_line = ""
        if display_url and display_url != label:
            if href:
                url_line = (
                    f'<div class="cite-rank-url-href">'
                    f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">{e(display_url)}</a>'
                    f"</div>"
                )
            else:
                url_line = f'<div class="cite-rank-url-href">{e(display_url)}</div>'
        items.append(
            f'<li class="cite-rank-url"><div class="cite-rank-url-main">{link}{url_line}</div>'
            f'<span class="cite-rank-url-count num">{e(count)}</span></li>'
        )
    if not items:
        return ""
    return f'<ol class="cite-rank-urls">{"".join(items)}</ol>'


def _cite_rank_valid_domains(bucket: dict[str, Any]) -> list[dict[str, Any]]:
    domains = bucket.get("domains") if isinstance(bucket, dict) else []
    if not isinstance(domains, list):
        return []
    out: list[dict[str, Any]] = []
    for row in domains:
        if not isinstance(row, dict):
            continue
        if not str(row.get("domain") or "").strip():
            continue
        out.append(row)
    return out


def _cite_rank_official_entry(
    rows: list[dict[str, Any]], official_domain: str
) -> tuple[int | None, dict[str, Any] | None]:
    """Return 1-based rank and row for the target domain, if cited."""
    if not official_domain:
        return None, None
    for i, row in enumerate(rows, start=1):
        if str(row.get("domain") or "").strip() == official_domain:
            return i, row
    return None, None


def _cite_rank_item_html(
    *,
    row: dict[str, Any],
    rank_label: str,
    max_c: int,
    official_domain: str,
    data: dict[str, Any],
    extra_class: str = "",
) -> str:
    domain = str(row.get("domain") or "").strip()
    count = int(row.get("count") or 0)
    width = round(count / max_c * 100, 1) if max_c else 0
    is_official = _cite_rank_is_official(domain, official_domain)
    cls = " cite-rank-item official" if is_official else " cite-rank-item"
    if extra_class:
        cls += f" {extra_class}"
    urls = row.get("urls") if isinstance(row.get("urls"), list) else []
    url_n = len(urls)
    meta = ui(data, "cite_rank_urls_n", count=num(url_n)) if url_n else ""
    official_tag = f'<span class="cite-rank-you">{e(ui(data, "cite_rank_official"))}</span>'
    name_html = e(domain) + (official_tag if is_official else "")
    sub_html = f'<span class="cite-rank-sub">{e(meta)}</span>' if meta else ""
    return (
        f'<details class="{cls.strip()}">'
        f"<summary>"
        f'<span class="cite-rank-rk num">{e(rank_label)}</span>'
        f'<span class="cite-rank-dn">{name_html}</span>'
        f'<span class="cite-rank-bar" aria-hidden="true"><span style="width:{width}%"></span></span>'
        f'<span class="cite-rank-meta">'
        f'<span class="cite-rank-count num">{e(ui(data, "cite_rank_count", count=num(count)))}</span>'
        f"{sub_html}"
        f"</span>"
        f"</summary>"
        f"{_cite_rank_url_items(urls, data)}"
        f"</details>"
    )


def _cite_rank_domain_items(bucket: dict[str, Any], data: dict[str, Any], official_domain: str) -> str:
    rows = _cite_rank_valid_domains(bucket)
    if not rows:
        return f'<div class="cite-rank-empty">{e(ui(data, "cite_rank_empty"))}</div>'
    total = len(rows)
    shown = rows[:CITE_RANK_DISPLAY_LIMIT]
    shown_domains = {str(row.get("domain") or "").strip() for row in shown}
    official_rank, official_row = _cite_rank_official_entry(rows, official_domain)
    pin_official = bool(official_domain) and official_domain not in shown_domains
    display_counts = [int(row.get("count") or 0) for row in shown]
    if pin_official:
        display_counts.append(int((official_row or {}).get("count") or 0))
    max_c = max(display_counts, default=1) or 1
    bits: list[str] = []
    for i, row in enumerate(shown, start=1):
        bits.append(
            _cite_rank_item_html(
                row=row,
                rank_label=f"#{i}",
                max_c=max_c,
                official_domain=official_domain,
                data=data,
            )
        )
    if total > CITE_RANK_DISPLAY_LIMIT:
        bits.append(
            f'<p class="cite-rank-more">{e(ui(data, "cite_rank_truncated", n=num(CITE_RANK_DISPLAY_LIMIT), total=num(total)))}</p>'
        )
    if pin_official:
        pinned = official_row or {"domain": official_domain, "count": 0, "urls": []}
        rank_label = f"#{official_rank}" if official_rank else ui(data, "cite_rank_unlisted")
        bits.append(
            _cite_rank_item_html(
                row=pinned,
                rank_label=str(rank_label),
                max_c=max_c,
                official_domain=official_domain,
                data=data,
                extra_class="cite-rank-item-outside",
            )
        )
    return f'<div class="cite-rank-list">{"".join(bits)}</div>'


def _cite_rank_tab_button(tab_id: str, bucket: dict[str, Any], data: dict[str, Any], *, selected: bool) -> str:
    label_key = "cite_rank_tab_branded" if tab_id == "branded" else "cite_rank_tab_unbranded"
    meta = ui(
        data,
        "cite_rank_tab_meta",
        answers=num(bucket.get("answer_count")),
        citations=num(bucket.get("citation_count")),
    )
    on = " on" if selected else ""
    pressed = "true" if selected else "false"
    return (
        f'<button type="button" class="cite-rank-tab{on}" data-cite-tab="{tab_id}" '
        f'role="tab" aria-selected="{pressed}">'
        f'<span class="cite-rank-tab-label">{e(ui(data, label_key))}</span>'
        f'<span class="cite-rank-tab-meta">{e(meta)}</span>'
        f"</button>"
    )


def build_citation_source_ranking_section(data: dict[str, Any]) -> str:
    ranking = data.get("citation_source_ranking") if isinstance(data.get("citation_source_ranking"), dict) else {}
    branded = ranking.get("branded") if isinstance(ranking.get("branded"), dict) else {}
    unbranded = ranking.get("unbranded") if isinstance(ranking.get("unbranded"), dict) else {}
    official = _official_report_domain(data)
    branded_panel = _cite_rank_domain_items(branded, data, official)
    unbranded_panel = _cite_rank_domain_items(unbranded, data, official)
    return f"""
  <section id="citeRank">
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_12_no"))}</div><h2 class="sec-title">{e(ui(data, "section_12_title"))}</h2><p class="sec-desc">{e(ui(data, "section_12_desc"))}</p></div><div class="sec-tag bench">EVIDENCE</div></div>
    <div class="card">
      <div class="cite-rank-tabs" role="tablist">
        {_cite_rank_tab_button("branded", branded, data, selected=True)}
        {_cite_rank_tab_button("unbranded", unbranded, data, selected=False)}
      </div>
      <div class="cite-rank-panel" data-cite-panel="branded">{branded_panel}</div>
      <div class="cite-rank-panel" data-cite-panel="unbranded" hidden>{unbranded_panel}</div>
    </div>
  </section>
  <script>
(function(){{
  const root = document.getElementById('citeRank');
  if (!root) return;
  const tabs = root.querySelectorAll('[data-cite-tab]');
  const panels = root.querySelectorAll('[data-cite-panel]');
  tabs.forEach(function(btn){{
    btn.addEventListener('click', function(){{
      const tab = btn.getAttribute('data-cite-tab');
      tabs.forEach(function(b){{
        const on = b === btn;
        b.classList.toggle('on', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
      }});
      panels.forEach(function(p){{
        p.hidden = p.getAttribute('data-cite-panel') !== tab;
      }});
    }});
  }});
}})();
  </script>
"""


def build_prompt_explorer_section(data: dict[str, Any], brand_name: str) -> str:
    pe = data.get("prompt_explorer") or {}
    groups = pe.get("groups", []) or []
    note = pe.get("note", "") or ui(data, "qa_section_note")
    # Prefer static UI note for modal UX (legacy builder note still describes accordion).
    if "展开" in str(note) or "Expand" in str(note) or "accordion" in str(note).lower():
        note = ui(data, "qa_section_note")
    GROUP_LABEL = {
        "branded_accuracy_validation": (ui(data, "qa_group_branded"), "warn"),
        "unbranded_category_discovery": (ui(data, "qa_group_unbranded"), "risk"),
    }
    payload_groups: list[dict[str, Any]] = []
    panels_html = ""
    rows_html = ""
    competitor_catalog = _collect_competitor_catalog(data, brand_name)
    for gi, g in enumerate(groups):
        label, lcls = GROUP_LABEL.get(g.get("scenario_group", ""), (ui(data, "qa_group_default"), "neutral"))
        answers = g.get("answers", []) or []
        dots = ""
        meta_answers: list[dict[str, Any]] = []
        group_has_partial = False
        for ai, a in enumerate(answers):
            answer_md = str(a.get("answer_markdown") or a.get("answer_excerpt") or "").strip()
            # Display-time text gate: do not trust classifier mentioned without body evidence.
            mentioned_effective = bool(a.get("mentioned")) and (
                not brand_name or _answer_mentions_brand(answer_md, brand_name)
            )
            semantic_effective = bool(a.get("semantic_accuracy")) if mentioned_effective else False
            a_view = {
                **a,
                "mentioned": mentioned_effective,
                "semantic_accuracy": semantic_effective,
            }
            on = "on" if mentioned_effective else ""
            dot_lbl = ui(data, "qa_dot_mentioned") if mentioned_effective else ui(data, "qa_dot_not_mentioned")
            dots += f'<span class="qa-dot {on}" title="{e(a.get("platform"))}: {e(dot_lbl)}"></span>'
            sources = a.get("answer_sources") if isinstance(a.get("answer_sources"), list) else []
            sources_html = _build_answer_sources_html(sources, data, answer_md=answer_md)
            comps = _competitors_present_in_answer(
                answer_md,
                a.get("competitor_names") or [],
                competitor_catalog,
                brand_name,
            )
            rank_rows = _mention_rank_rows(
                brand_name=brand_name,
                mentioned=mentioned_effective,
                competitor_names=comps,
                answer_md=answer_md,
                competitor_catalog=competitor_catalog,
            )
            sentiment = _normalize_sentiment(a.get("brand_sentiment"))
            if not mentioned_effective and sentiment == "positive":
                sentiment = "neutral"
            is_partial = _is_partial_visible(a_view, brand_name=brand_name)
            if is_partial:
                group_has_partial = True
            badges_html = []
            if mentioned_effective:
                badges_html.append(f'<span class="qa-b ok">{e(ui(data, "qa_badge_mentioned"))}</span>')
            else:
                badges_html.append(f'<span class="qa-b risk">{e(ui(data, "qa_badge_not_mentioned"))}</span>')
            if is_partial:
                badges_html.append(_partial_visible_badge(data))
            elif mentioned_effective and semantic_effective is True:
                badges_html.append(
                    f'<span class="qa-b ok">{e(ui(data, "qa_badge_fully_visible"))}</span>'
                )
            if a.get("official_site_cited"):
                badges_html.append(f'<span class="qa-b ok">{e(ui(data, "qa_badge_cite_official"))}</span>')
            else:
                badges_html.append(f'<span class="qa-b muted">{e(ui(data, "qa_badge_cite_missing"))}</span>')
            badges_html.append(_senti_pill(sentiment, data))
            queried = a.get("queried_as") or ""
            show_queried = bool(queried and queried != g.get("question"))
            collect_error = str(a.get("collect_error") or a.get("error") or "").strip()
            if answer_md:
                md_html = render_answer_markdown(answer_md)
            elif collect_error:
                md_html = (
                    f'<div class="qa-excerpt muted">{e(ui(data, "qa_no_excerpt"))}'
                    f"<br>{e(collect_error)}</div>"
                )
            else:
                md_html = f'<div class="qa-excerpt muted">{e(ui(data, "qa_no_excerpt"))}</div>'
            if comps:
                comps_html = (
                    '<div class="qa-comp-chips">'
                    + "".join(f'<span class="qa-chip">{e(n)}</span>' for n in comps)
                    + "</div>"
                )
            else:
                comps_html = f'<div class="qa-empty">{e(ui(data, "qa_no_competitors"))}</div>'
            evidence = a.get("evidence") or ""
            if bool(a.get("mentioned")) and not mentioned_effective:
                note = ui(data, "qa_evidence_corrected")
                original = ui(data, "qa_evidence_corrected_original", evidence=evidence) if evidence else note
                evidence = original if evidence else note
            panels_html += (
                f'<div class="qa-panel" data-qa-group="{gi}" data-qa-ans="{ai}" hidden>'
                f'<div data-slot="prompt" data-has-prompt="{1 if show_queried else 0}">{e(queried) if show_queried else ""}</div>'
                f'<div data-slot="answer">{md_html}</div>'
                f'<div data-slot="badges">{"".join(badges_html)}</div>'
                f'<div data-slot="rank">{_build_mention_rank_html(rank_rows, data)}</div>'
                f'<div data-slot="comps">{comps_html}</div>'
                f'<div data-slot="evidence">{e(evidence)}</div>'
                f'<div data-slot="sources">{sources_html}</div>'
                f"</div>"
            )
            meta_answers.append(
                {
                    "platform": a.get("platform") or "",
                    "mentioned": mentioned_effective,
                    "partial_visible": is_partial,
                    "brand_sentiment": sentiment,
                }
            )
        row_flags = _senti_pill(_aggregate_group_sentiment(answers), data)
        if group_has_partial:
            row_flags += _partial_visible_badge(data)
        payload_groups.append(
            {
                "id": gi,
                "tag": label,
                "tagClass": lcls,
                "qnum": f"Q{gi + 1:02d}",
                "question": g.get("question") or "",
                "answers": meta_answers,
                "hasPartial": group_has_partial,
                "sentiment": _aggregate_group_sentiment(answers),
            }
        )
        dots_title = e(ui(data, "qa_dots_legend"))
        rows_html += (
            f'<button type="button" class="qa-row" data-qa-open="{gi}">'
            f'<span class="qa-tag {lcls}">{e(label)}</span>'
            f'<span class="qa-qnum">Q{gi + 1:02d}</span>'
            f'<span class="qa-q">{e(g.get("question"))}</span>'
            f'<span class="qa-flags">{row_flags}</span>'
            f'<span class="qa-dots" title="{dots_title}">{dots}</span>'
            f'<span class="qa-open-hint">{e(ui(data, "qa_open_modal"))}</span>'
            f"</button>"
        )

    labels_js = {
        "actualPrompt": ui(data, "qa_modal_actual_prompt"),
        "noPlatform": ui(data, "qa_no_platform"),
    }
    payload_json = json.dumps(
        {"groups": payload_groups, "labels": labels_js},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")

    return f"""
  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_13_no"))}</div><h2 class="sec-title">{e(ui(data, "section_13_title"))}</h2><p class="sec-desc">{e(note)}</p></div><div class="sec-tag bench">EVIDENCE</div></div>
    <div class="qa-wrap">{rows_html}</div>
    <div id="qaExplorerPanels" hidden>{panels_html}</div>
  </section>
  <dialog class="qa-modal" id="qaExplorerModal" aria-label="{e(ui(data, "section_13_title"))}">
    <div class="qa-modal-shell">
      <header class="qa-modal-head">
        <div class="qa-modal-head-main">
          <div class="qa-modal-meta"><span class="qa-tag" id="qaModalTag"></span><span class="qa-qnum" id="qaModalQnum"></span></div>
          <h3 class="qa-modal-title" id="qaModalQuestion"></h3>
        </div>
        <button type="button" class="qa-modal-close" id="qaModalClose" aria-label="{e(ui(data, "qa_modal_close"))}">×</button>
      </header>
      <div class="qa-modal-tabs" id="qaModalTabs" role="tablist"></div>
      <div class="qa-modal-body">
        <div class="qa-modal-left">
          <div class="qa-modal-k" id="qaModalPromptLabel"></div>
          <div class="qa-modal-prompt" id="qaModalPrompt"></div>
          <div class="qa-md" id="qaModalAnswer"></div>
        </div>
        <aside class="qa-modal-right">
          <div class="qa-side-block">
            <div class="qa-side-title">{e(ui(data, "qa_modal_status"))}</div>
            <div class="qa-badges" id="qaModalBadges"></div>
          </div>
          <div class="qa-side-block">
            <div class="qa-side-title">{e(ui(data, "qa_modal_ranking"))}</div>
            <div id="qaModalRank"></div>
          </div>
          <div class="qa-side-block">
            <div class="qa-side-title">{e(ui(data, "qa_modal_competitors"))}</div>
            <div id="qaModalComps"></div>
          </div>
          <div class="qa-side-block">
            <div class="qa-side-title">{e(ui(data, "qa_evidence")).rstrip("：:")}</div>
            <div class="qa-ev-body" id="qaModalEvidence"></div>
          </div>
          <div class="qa-side-block">
            <div class="qa-side-title">{e(ui(data, "qa_sources"))}</div>
            <div id="qaModalSources"></div>
          </div>
        </aside>
      </div>
    </div>
  </dialog>
  <script type="application/json" id="qaExplorerData">{payload_json}</script>
  <script>
(function(){{
  const dataEl = document.getElementById('qaExplorerData');
  const modal = document.getElementById('qaExplorerModal');
  const panelsRoot = document.getElementById('qaExplorerPanels');
  if (!dataEl || !modal || !panelsRoot) return;
  let payload;
  try {{ payload = JSON.parse(dataEl.textContent || '{{}}'); }} catch (err) {{ return; }}
  const groups = payload.groups || [];
  const labels = payload.labels || {{}};
  const tabsEl = document.getElementById('qaModalTabs');
  const tagEl = document.getElementById('qaModalTag');
  const qnumEl = document.getElementById('qaModalQnum');
  const qEl = document.getElementById('qaModalQuestion');
  const promptLabelEl = document.getElementById('qaModalPromptLabel');
  const promptEl = document.getElementById('qaModalPrompt');
  const answerEl = document.getElementById('qaModalAnswer');
  const badgesEl = document.getElementById('qaModalBadges');
  const rankEl = document.getElementById('qaModalRank');
  const compsEl = document.getElementById('qaModalComps');
  const evidenceEl = document.getElementById('qaModalEvidence');
  const sourcesEl = document.getElementById('qaModalSources');
  let activeGroup = null;

  function esc(s) {{
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}

  function panelSlot(groupId, ansIdx, slot) {{
    const panel = panelsRoot.querySelector('.qa-panel[data-qa-group="' + groupId + '"][data-qa-ans="' + ansIdx + '"]');
    if (!panel) return null;
    return panel.querySelector('[data-slot="' + slot + '"]');
  }}

  function renderAnswer(groupId, idx) {{
    const promptSlot = panelSlot(groupId, idx, 'prompt');
    const answerSlot = panelSlot(groupId, idx, 'answer');
    const badgesSlot = panelSlot(groupId, idx, 'badges');
    const rankSlot = panelSlot(groupId, idx, 'rank');
    const compsSlot = panelSlot(groupId, idx, 'comps');
    const evidenceSlot = panelSlot(groupId, idx, 'evidence');
    const sourcesSlot = panelSlot(groupId, idx, 'sources');
    if (!answerSlot) {{
      answerEl.innerHTML = '<div class="qa-excerpt muted">' + esc(labels.noPlatform || '') + '</div>';
      badgesEl.innerHTML = '';
      rankEl.innerHTML = '';
      compsEl.innerHTML = '';
      evidenceEl.textContent = '';
      sourcesEl.innerHTML = '';
      promptEl.textContent = '';
      promptLabelEl.textContent = '';
      return;
    }}
    const hasPrompt = promptSlot && promptSlot.getAttribute('data-has-prompt') === '1';
    promptLabelEl.textContent = hasPrompt ? (labels.actualPrompt || '') : '';
    promptEl.textContent = hasPrompt ? (promptSlot.textContent || '') : '';
    promptEl.style.display = hasPrompt ? '' : 'none';
    promptLabelEl.style.display = hasPrompt ? '' : 'none';
    answerEl.innerHTML = answerSlot.innerHTML;
    badgesEl.innerHTML = badgesSlot ? badgesSlot.innerHTML : '';
    rankEl.innerHTML = rankSlot ? rankSlot.innerHTML : '';
    compsEl.innerHTML = compsSlot ? compsSlot.innerHTML : '';
    evidenceEl.textContent = evidenceSlot ? (evidenceSlot.textContent || '') : '';
    sourcesEl.innerHTML = sourcesSlot ? sourcesSlot.innerHTML : '';
  }}

  function setTab(idx) {{
    if (!activeGroup) return;
    Array.prototype.forEach.call(tabsEl.querySelectorAll('.qa-tab'), function(btn, i) {{
      const on = i === idx;
      btn.classList.toggle('on', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    }});
    renderAnswer(activeGroup.id, idx);
  }}

  function openGroup(id) {{
    activeGroup = groups.find(function(g) {{ return g.id === id; }}) || null;
    if (!activeGroup) return;
    tagEl.textContent = activeGroup.tag || '';
    tagEl.className = 'qa-tag ' + (activeGroup.tagClass || 'neutral');
    qnumEl.textContent = activeGroup.qnum || '';
    qEl.textContent = activeGroup.question || '';
    const answers = activeGroup.answers || [];
    tabsEl.innerHTML = answers.map(function(a, i) {{
      const classes = ['qa-tab'];
      if (a.mentioned) classes.push('mentioned');
      if (a.partial_visible) classes.push('partial');
      return '<button type="button" class="' + classes.join(' ') + '" role="tab" data-tab="' + i + '">' + esc(a.platform || ('#' + (i+1))) + '</button>';
    }}).join('') || ('<div class="qa-empty">' + esc(labels.noPlatform || '') + '</div>');
    setTab(0);
    if (typeof modal.showModal === 'function') modal.showModal();
    else modal.setAttribute('open', '');
  }}

  document.querySelectorAll('[data-qa-open]').forEach(function(btn) {{
    btn.addEventListener('click', function() {{
      openGroup(Number(btn.getAttribute('data-qa-open')));
    }});
  }});
  tabsEl.addEventListener('click', function(ev) {{
    const t = ev.target.closest('[data-tab]');
    if (!t) return;
    setTab(Number(t.getAttribute('data-tab')));
  }});
  function closeModal() {{
    if (typeof modal.close === 'function') modal.close();
    else modal.removeAttribute('open');
  }}
  document.getElementById('qaModalClose').addEventListener('click', closeModal);
  modal.addEventListener('click', function(ev) {{
    if (ev.target === modal) closeModal();
  }});
}})();
  </script>
"""

def build_body(data: dict[str, Any]) -> str:
    cover = data.get("cover", {})
    kpis = data.get("executive_kpis", {})
    top = data.get("top_distribution", {})
    scenario = top.get("scenario_breakdown", {})
    branded = scenario.get("branded", {})
    unbranded = scenario.get("unbranded", {})
    funnel = build_funnel(data)
    funnel_scenarios = funnel.get("scenarios", []) or []
    funnel_branded_total = funnel_scenarios[0].get("total", 0) if len(funnel_scenarios) > 0 else 0
    funnel_unbranded_total = funnel_scenarios[1].get("total", 0) if len(funnel_scenarios) > 1 else 0
    authority = data.get("authority_radar", {})
    comp = data.get("competitor_gap", {})
    rows = comp.get("rows", []) or []
    target = rows[0] if rows else {}
    platform_count = cover.get("platform_count") or len((data.get("platform_performance", {}) or {}).get("platforms", []) or [])
    prompt_per_platform = cover.get("prompt_count_per_platform", 0)
    total_samples = cover.get("total_answer_samples") or funnel.get("denominator") or (top.get("donut", {}) or {}).get("denominator", 0)
    comp_min = kpis.get("domain_rating", {}).get("competitor_min")
    comp_max = kpis.get("domain_rating", {}).get("competitor_max")
    kpi_dr = kpis.get("domain_rating", {})
    kpi_unbranded = kpis.get("unbranded_visibility") or {}
    kpi_takeover = kpis.get("competitor_takeover_when_target_absent") or {}
    unbranded_mentioned_n = kpi_unbranded.get("mentioned", 0)
    unbranded_total_n = kpi_unbranded.get("total", 0)
    unbranded_absent_n = unbranded_total_n - unbranded_mentioned_n
    kpi_branded = kpis.get("branded_recognition") or {}
    branded_mentioned_n = kpi_branded.get("mentioned", 0)
    branded_total_n = kpi_branded.get("total", 0)
    branded_rate = round(branded_mentioned_n / branded_total_n * 100) if branded_total_n else 0
    takeover_n = kpi_takeover.get("count", 0)
    absent_n = kpi_takeover.get("absent_unbranded", unbranded_absent_n)
    # narrative_copy is generated from this report's evidence before rendering.
    # Deterministic fallbacks remain only for backwards-compatible rendering of old data files.
    nc = data.get("narrative_copy") or {}

    auth_rows = ""
    axes = authority.get("axes", []) or []
    target_scores = authority.get("target_scores", []) or []
    base_scores = authority.get("industry_baseline_scores", []) or []
    for i, axis in enumerate(axes):
        value = target_scores[i] if i < len(target_scores) else ui(data, "status_pending")
        base = base_scores[i] if i < len(base_scores) else ui(data, "status_pending")
        klass = "warn" if i == 0 or i == len(axes) - 1 else "risk"
        auth_rows += f'<div class="row-line"><span class="lbl">{e(axis)}</span><span class="val {klass}">{e(value)} <span style="color:var(--muted-2)">{e(ui(data, "vs_label"))} {e(base)}</span></span></div>\n'

    search_rows = ""
    for row in rows:
        search_rows += (
            f'<div class="row-line"><span class="lbl">{e(row.get("name"))}</span>'
            f'<span class="val">{e(ui(data, "search_dr_row", dr=num(row.get("dr")), organic=num(row.get("organic_traffic")), keywords=num(row.get("organic_keywords"))))}</span></div>\n'
        )

    logo_html = magup_logo_img()
    logo_block = f'    <div class="cover-logo">{logo_html}</div>\n' if logo_html else ""
    rival_labels = [
        str(r.get("name"))
        for r in rows
        if r.get("name") and str(r.get("name")) != str(data.get("brand_name"))
    ][:4]
    rival_phrase = (
        ", ".join(rival_labels)
        if rival_labels and not is_cjk_locale(str(data.get("delivery_language") or ""))
        else ("、".join(rival_labels) if rival_labels else ui(data, "rivals_fallback"))
    )
    brand_name = str(data.get("brand_name") or ui(data, "default_target_brand"))
    platform_phrase = cover_platform_phrase(data, platform_count)
    cover_platform_logos_html = build_cover_platform_logos(data, prompt_per_platform)
    _takeover_rate = round(takeover_n / absent_n * 100) if absent_n else 0
    _sub_line = ui(
        data,
        "report_sub",
        platform_phrase=platform_phrase,
        total_samples=num(total_samples),
        brand_name=brand_name,
    )

    # Precompute narrative strings: nc (from skill) takes priority; fallback to renderer templates.
    _s01_desc = tighten_brand_spacing(
        nc.get("section_01_desc")
        or ui(
            data,
            "fallback_section_01_desc",
            brand_name=brand_name,
            unbranded_mentioned=num(unbranded_mentioned_n),
            unbranded_total=num(unbranded_total_n),
            takeover=num(takeover_n),
            branded_mentioned=num(branded_mentioned_n),
            branded_total=num(branded_total_n),
            branded_rate=num(branded_rate),
        ),
        brand_name,
    )
    _main_insight = tighten_brand_spacing(
        nc.get("main_insight")
        or ui(
            data,
            "fallback_main_insight",
            brand_name=brand_name,
            unbranded_absent=num(unbranded_absent_n),
            unbranded_total=num(unbranded_total_n),
            takeover=num(takeover_n),
            rivals=rival_phrase,
            branded_mentioned=num(branded_mentioned_n),
            branded_total=num(branded_total_n),
            branded_rate=num(branded_rate),
        ),
        brand_name,
    )
    _s05_insight = tighten_brand_spacing(
        nc.get("section_06_insight") or nc.get("section_05_insight")
        or ui(data, "fallback_section_05_insight", brand_name=brand_name),
        brand_name,
    )
    _s06_dr_note = tighten_brand_spacing(
        nc.get("section_07_dr_note") or nc.get("section_06_dr_note")
        or ui(
            data,
            "fallback_section_06_dr_note",
            brand_name=brand_name,
            dr=num(kpi_dr.get("target")),
            comp_min=num(comp_min),
            comp_max=num(comp_max),
        ),
        brand_name,
    )
    _s07_insight = tighten_brand_spacing(
        nc.get("section_09_insight") or nc.get("section_07_insight")
        or ui(data, "fallback_section_07_insight", brand_name=brand_name),
        brand_name,
    )
    _s08_desc = tighten_brand_spacing(
        nc.get("section_10_desc") or nc.get("section_08_desc")
        or ui(data, "fallback_section_08_desc", brand_name=brand_name),
        brand_name,
    )
    _s09_insight = tighten_brand_spacing(
        nc.get("section_11_insight") or nc.get("section_09_insight")
        or ui(data, "fallback_section_09_insight", brand_name=brand_name),
        brand_name,
    )

    sample_split = build_sample_distribution_split(branded, funnel, data, total_samples)
    _perf = data.get("platform_performance", {}) or {}
    platform_compare_html = build_platform_compare(
        _perf.get("platforms", []) or [], _perf.get("untested_platforms", []) or [], data
    )
    sentiment_section = build_sentiment_section(data, brand_name)
    ranking_section = build_ranking_section(data, brand_name)
    citation_ranking_section = ""  # Section 12 引用信源排行 omitted by product request
    prompt_explorer_section = build_prompt_explorer_section(data, brand_name)

    return f"""<div class="container">
  <header class="cover">
{logo_block}    <h1>{e(ui(data, 'report_title_suffix'))}<br/><span class="accent">{e(data.get('brand_name'))}</span></h1>
    <p class="sub">{e(_sub_line)}<br/>{e(ui(data, 'report_audience'))}</p>
    <div class="meta">
      <div><div class="k">{e(ui(data, 'meta_subject'))}</div><div class="v">{e(data.get('target_domain'))}</div></div>
      <div class="meta-col-business"><div class="k">{e(ui(data, 'meta_business'))}</div><div class="v">{e(cover.get('business_definition'))}</div></div>
      <div class="meta-col-samples"><div class="k">{e(ui(data, 'meta_platforms'))}</div><div class="v">{cover_platform_logos_html}</div></div>
      <div class="meta-col-date-code">
        <div class="k">{e(ui(data, 'meta_date'))}</div>
        <div class="v">{e(cover.get('report_date'))}</div>
        {f'<div class="k meta-k-secondary">{e(ui(data, "meta_report_code"))}</div><div class="v">{e(cover.get("report_code"))}</div>' if cover.get("report_code") else ""}
      </div>
    </div>
  </header>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_02_no"))}</div><h2 class="sec-title">{e(ui(data, "section_02_title", total_samples=num(total_samples), brand_name=brand_name))}</h2><p class="sec-desc">{e(ui(data, "section_02_desc"))}</p></div></div>
    <div class="card">
      <h3>{e(ui(data, "section_02_card_title"))} <span class="badge tested">{e(ui(data, "badge_data_samples", count=num(total_samples)))}</span></h3>
      <div class="h-note">{e(ui(data, "section_02_card_note", branded_total=num(funnel_branded_total), unbranded_total=num(funnel_unbranded_total)))}</div>
      {sample_split}
      <div class="legend"><span><i style="background:#533afd"></i>{e(ui(data, "legend_visible"))}</span><span><i style="background:#f59e0b"></i>{e(ui(data, "legend_improve"))}</span><span><i style="background:#c9d3df"></i>{e(ui(data, "legend_absent"))}</span></div>
    </div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, 'section_01_no'))}</div><h2 class="sec-title">{e(ui(data, 'section_01_title'))}</h2><p class="sec-desc">{tx(_s01_desc, brand_name)}</p></div></div>
    <div class="kpi-row">
      <div class="kpi risk"><div class="label">{e(ui(data, 'kpi_unbranded'))}</div><div class="big num"><span>{pct_display(unbranded_mentioned_n, unbranded_total_n)}<span class="pct">%</span></span><span class="unit">{num(unbranded_mentioned_n)}/{num(unbranded_total_n)}</span></div><div class="note">{e(ui(data, 'kpi_unbranded_note', brand_name=brand_name))}</div></div>
      <div class="kpi ok"><div class="label">{e(ui(data, 'kpi_branded'))}</div><div class="big num"><span>{pct_display(branded_mentioned_n, branded_total_n)}<span class="pct">%</span></span><span class="unit">{num(branded_mentioned_n)}/{num(branded_total_n)}</span></div><div class="note">{e(ui(data, 'kpi_branded_note'))}</div></div>
      <div class="kpi risk"><div class="label">{e(ui(data, 'kpi_competitor'))}</div><div class="big num"><span>{pct_display(takeover_n, absent_n)}<span class="pct">%</span></span><span class="unit">{num(takeover_n)}/{num(absent_n)}</span></div><div class="note">{e(ui(data, 'kpi_competitor_note', rate=_takeover_rate))}</div></div>
      <div class="kpi warn"><div class="label">{e(ui(data, 'kpi_dr'))}</div><div class="big num">{num(kpi_dr.get('target'))}</div><div class="note">{e(ui(data, 'kpi_dr_note', comp_min=num(comp_min), comp_max=num(comp_max)))}</div></div>
    </div>
    <div class="insight"><p class="lead">{tx(_main_insight, brand_name)}</p></div>
  </section>
{sentiment_section}
  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_04_no"))}</div><h2 class="sec-title">{e(ui(data, "section_04_title"))}</h2><p class="sec-desc">{e(ui(data, "section_04_desc"))}</p></div></div>
    <div class="grid-3">{build_platform_cards(data)}</div>
    <div class="grid-2" style="margin-top:16px"><div class="card"><h3>{e(ui(data, "plat_compare_title"))}</h3><div class="h-note">{e(ui(data, "plat_compare_note"))}</div>{platform_compare_html}</div><div class="card"><h3>{e(ui(data, "plat_matrix_title"))}</h3><div class="h-note">{e(ui(data, "plat_matrix_note"))}</div><div class="chart-scroll"><div class="chart-wrap chart-wrap--pan" style="height:340px;min-width:420px"><canvas id="platMatrix"></canvas></div></div></div></div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_05_no"))}</div><h2 class="sec-title">{e(ui(data, "section_05_title"))}</h2><p class="sec-desc">{e(ui(data, "section_05_desc"))}</p></div></div>
    <div class="grid-2"><div class="card"><h3>{e(ui(data, "auth_radar_title"))}</h3><div class="h-note">{e(ui(data, "auth_radar_note"))}</div><div class="chart-scroll"><div class="chart-wrap chart-wrap--pan" style="height:380px;min-width:420px"><canvas id="authRadar"></canvas></div></div><div class="legend"><span><i style="background:#0ea5e9"></i>{e(ui(data, "legend_radar_industry"))}</span><span><i style="background:#533afd"></i>{e(ui(data, "legend_radar_current", brand_name=brand_name))}</span></div></div><div class="card"><h3>{e(ui(data, "auth_dim_title"))}</h3><div class="h-note">{e(ui(data, "auth_dim_note"))}</div><div class="metric-rows">{auth_rows}</div><hr class="thin"/><div style="font-size:12px;color:var(--muted);line-height:1.65">{e(ui(data, "auth_focus_note"))}</div></div></div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_06_no"))}</div><h2 class="sec-title">{e(ui(data, "section_06_title"))}</h2><p class="sec-desc">{e(ui(data, "section_06_desc"))}</p></div></div>
    <div class="card"><h3>{e(ui(data, "src_bar_title"))}</h3><div class="h-note">{e(ui(data, "src_bar_note", brand_name=brand_name))}</div><div class="chart-scroll"><div class="chart-wrap chart-wrap--pan" style="height:380px"><canvas id="srcBar"></canvas></div></div><div class="legend"><span><i style="background:#533afd"></i>{e(ui(data, "legend_radar_current", brand_name=brand_name))}</span><span><i style="background:#8a9bb0"></i>{e(ui(data, "legend_peer_ref"))}</span></div></div><div class="insight warn"><p class="lead">{tx(_s05_insight, brand_name)}</p></div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_07_no"))}</div><h2 class="sec-title">{e(ui(data, "section_07_title"))}</h2><p class="sec-desc">{e(ui(data, "section_07_desc"))}</p></div></div>
    <div class="grid-asym"><div class="card"><h3>{e(ui(data, "comp_bubble_title"))}</h3><div class="h-note">{e(ui(data, "comp_bubble_note"))}</div><div class="chart-scroll"><div class="chart-wrap chart-wrap--pan" style="height:420px;min-width:480px"><canvas id="compBubble"></canvas></div></div></div><div class="card"><h3>{e(ui(data, "dr_bar_title"))}</h3><div class="h-note">{e(ui(data, "dr_bar_note"))}</div><div class="chart-scroll"><div class="chart-wrap chart-wrap--pan" style="height:340px;min-width:420px"><canvas id="drBar"></canvas></div></div><hr class="thin"/><div style="font-size:12px;color:var(--muted);line-height:1.7">{tx(_s06_dr_note, brand_name)}</div></div></div>
  </section>

{ranking_section}
  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_09_no"))}</div><h2 class="sec-title">{e(ui(data, "section_09_title"))}</h2><p class="sec-desc">{e(ui(data, "section_09_desc"))}</p></div></div>
    {build_channel_cards(data)}<div class="insight"><p class="lead">{tx(_s07_insight, brand_name)}</p></div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_10_no"))}</div><h2 class="sec-title">{e(ui(data, "section_10_title", brand_name=brand_name))}</h2><p class="sec-desc">{tx(_s08_desc, brand_name)}</p></div></div>
    <div class="root-stack">{build_root_stack(data)}</div>
  </section>

  <section>
    <div class="sec-head"><div class="left"><div class="sec-no">{e(ui(data, "section_11_no"))}</div><h2 class="sec-title">{e(ui(data, "section_11_title"))}</h2><p class="sec-desc">{e(ui(data, "section_11_desc"))}</p></div></div>
    <div class="insight"><p class="lead">{tx(_s09_insight, brand_name)}</p></div>
    <table class="recs"><thead><tr><th style="width:9%">{e(ui(data, "recs_col_priority"))}</th><th style="width:22%">{e(ui(data, "recs_col_action"))}</th><th style="width:31%">{e(ui(data, "recs_col_why"))}</th><th style="width:19%">{e(ui(data, "recs_col_metric"))}</th><th style="width:19%">{e(ui(data, "recs_col_effort"))}</th></tr></thead><tbody>{build_recommendations(data)}</tbody></table>
  </section>
{citation_ranking_section}
{prompt_explorer_section}
{build_boundary(data)}
</div>

{build_script(data)}"""


def build_script(data: dict[str, Any]) -> str:
    funnel = build_funnel(data)
    chart_labels = data.get("chart_labels") or {}
    # Non-Chinese locales use English chrome fallbacks when chart_labels omit a key.
    latin = not is_cjk_locale(str(data.get("delivery_language") or ""))
    radar_industry = chart_labels.get("radar_industry") or ("Cross-category baseline" if latin else "跨类目基准")
    radar_suffix = chart_labels.get("radar_target_suffix") or (" current" if latin else "当前")
    dr_label = chart_labels.get("dr_label") or ("Domain authority score" if latin else "域名权威分")
    matrix_ideal = chart_labels.get("matrix_ideal") or ("Ideal zone · visible, low competitor" if latin else "理想区 · 可见且少竞品")
    matrix_risk = chart_labels.get("matrix_risk") or ("Risk zone · absent, high competitor" if latin else "高危区 · 缺席且多竞品")
    plat_bubble_x = chart_labels.get("platform_bubble_x") or ("Unbranded visibility (higher is better)" if latin else "无品牌可见度（越右越好）")
    plat_bubble_y = chart_labels.get("platform_bubble_y") or ("Competitor share (lower is better)" if latin else "竞品占位率（越低越好）")
    bubble_x = chart_labels.get("bubble_x") or ("Unbranded AI visibility (%)" if latin else "无品牌 AI 可见度 (%)")
    bubble_y = chart_labels.get("bubble_y") or ("Source citation share (%)" if latin else "信源引用占比 (%)")
    industry_mean = ui(data, "industry_mean")
    brand_current = f"{data.get('brand_name')}{radar_suffix}"
    tooltip_seg_tpl = ui(data, "chart_tooltip_seg")
    tooltip_plat_tpl = ui(data, "chart_tooltip_plat_bubble")
    tooltip_comp_tpl = ui(data, "chart_tooltip_comp_scatter")
    tooltip_comp_proxy = ui(data, "chart_tooltip_comp_proxy")
    funnel_scenarios = funnel.get("scenarios", []) or []
    funnel_tiers = funnel.get("tiers", []) or []

    def _funnel_chart_payload(
        scenario_index: int,
        row_label: str | None = None,
        bar_thickness: int = 28,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        if scenario_index >= len(funnel_scenarios):
            return [], []
        scenario = funnel_scenarios[scenario_index]
        labels = [row_label or str(scenario.get("name") or "")]
        datasets: list[dict[str, Any]] = []
        for tier_i, tier_name in enumerate(funnel_tiers):
            segs = scenario.get("segments", []) or []
            seg = segs[tier_i] if tier_i < len(segs) else {}
            cnt = int(seg.get("count", 0) or 0)
            tot = int(scenario.get("total", 0) or 0)
            datasets.append(
                {
                    "label": tier_name,
                    "data": [round(cnt / tot * 100, 1) if tot else 0],
                    "counts": [cnt],
                    "totals": [tot],
                    "segLabels": [seg.get("label", tier_name)],
                    "backgroundColor": TIER_COLORS[tier_i % len(TIER_COLORS)],
                    "borderColor": "#fff",
                    "borderWidth": 2,
                    "barThickness": bar_thickness,
                }
            )
        return labels, datasets

    sample_bar_branded_labels, sample_bar_branded_datasets = _funnel_chart_payload(
        0, ui(data, "scenario_visibility_mix"), 18
    )
    sample_bar_unbranded_labels, sample_bar_unbranded_datasets = _funnel_chart_payload(1, bar_thickness=32)
    branded_attrs = (data.get("top_distribution", {}) or {}).get("scenario_breakdown", {}) or {}
    branded = branded_attrs.get("branded", {}) or {}
    b_total_attr = int(branded.get("total", 0) or 0)
    b_mentioned_attr = int(branded.get("mentioned", 0) or 0)
    b_cited_attr = int(branded.get("official_site_cited", 0) or 0)
    sample_bar_recognized_labels, sample_bar_recognized_datasets = _binary_attr_bar_payload(
        ui(data, "scenario_recognized"),
        b_mentioned_attr,
        b_total_attr,
        ui(data, "scenario_recognized"),
        ui(data, "scenario_not_recognized"),
        bar_thickness=32,
    )
    sample_bar_cited_labels, sample_bar_cited_datasets = _binary_attr_bar_payload(
        ui(data, "scenario_cited"),
        b_cited_attr,
        b_total_attr,
        ui(data, "scenario_cited"),
        ui(data, "scenario_not_cited"),
        bar_thickness=18,
    )
    perf = data.get("platform_performance", {})
    platforms = perf.get("platforms", []) or []
    auth = data.get("authority_radar", {})
    source = data.get("source_quality", {})
    # Drop channels that don't apply to consumer/eyewear brands: dev docs (hardcoded dead bar)
    # and B2B software review platforms (G2 / Capterra). Trustpilot-style review signal still
    # shows up via the credibility radar's 专业度 axis.
    _SRC_CHANNEL_HIDE = {
        "开发者文档", "B2B 评测 (G2 / Capterra)",
        "Developer docs", "B2B reviews (G2 / Capterra)",
    }
    source_channels = [c for c in (source.get("channels", []) or []) if c.get("name") not in _SRC_CHANNEL_HIDE]
    # Per-channel bar colour derived from each channel's own status (NOT a fixed positional
    # array — that broke once channels were filtered out): muted only when not independently tested.
    src_colors = ["rgba(83,58,253,0.28)" if c.get("evidence_status") == "not_independently_tested" else "#533afd" for c in source_channels]
    comp = data.get("competitor_gap", {})
    comp_rows = comp.get("rows", []) or []
    dr_rank = comp.get("dr_ranking", []) or []

    # Platform visibility comparison is rendered as logo-led HTML bars in the body
    # (see build_platform_compare); only the recommendation-resistance bubble matrix
    # remains a Chart.js chart here.
    matrix_datasets = []
    for p in platforms:
        name = p.get("display_name") or p.get("id")
        color = platform_chart_color(str(p.get("id", "")), str(name))
        if color == "#533afd":
            bubble_fill = "rgba(83,58,253,0.65)"
        elif color == "#1a9e80":
            bubble_fill = "rgba(26,158,128,0.58)"
        else:
            bubble_fill = "rgba(14,165,233,0.58)"
        # Opportunity / resistance quadrant: x = unbranded visibility (higher = better),
        # y = competitor-takeover rate (higher = more resistance), bubble size = sample count.
        inv = p.get("competitor_inverse_score")
        try:
            takeover_rate = round(100 - float(inv), 1)
        except (TypeError, ValueError):
            takeover_rate = None
        try:
            sample_n = int(p.get("unbranded_total") or 0)
        except (TypeError, ValueError):
            sample_n = 0
        bubble_r = max(10, min(26, sample_n / 2 + 8))
        matrix_datasets.append({
            "label": name,
            "data": [{"x": p.get("unbranded_visibility_rate"), "y": takeover_rate, "r": bubble_r, "n": sample_n}],
            "backgroundColor": bubble_fill,
            "borderColor": color,
            "borderWidth": 1.5,
        })

    comp_datasets = []
    comp_color_by_name = {}
    for i, row in enumerate(comp_rows):
        color = COMP_COLORS[i % len(COMP_COLORS)]
        comp_color_by_name[row.get("name")] = color
        y_is_proxy = bool(row.get("y_is_proxy"))
        comp_datasets.append({
            "label": row.get("name"),
            "data": [{"x": row.get("x_visibility"), "y": row.get("y_source_share") or 0}],
            # Real-measured points: filled. Proxy-y points (competitors): hollow + dashed ring.
            "backgroundColor": "transparent" if y_is_proxy else hex_to_rgba(color, 0.85),
            "borderColor": color,
            "borderWidth": 2,
            "borderDash": [4, 3] if y_is_proxy else [],
            "pointStyle": "circle",
            "pointRadius": 7,
            "pointHoverRadius": 10,
        })
    dr_colors = [comp_color_by_name.get(x[0], COLORS["muted"]) for x in dr_rank]
    dr_values = [x[1] for x in dr_rank if x[1]]
    dr_max = max(dr_values) if dr_values else 100
    # DR is now 0-100 scale; round up to nearest 10
    tick_unit = 10
    dr_axis_max = min(100, ((int(dr_max) // tick_unit) + 1) * tick_unit)
    comp_y_values = [float(row.get("y_source_share") or 0) for row in comp_rows]
    comp_y_max_raw = max(comp_y_values) if comp_y_values else 40
    comp_bubble_y_max = min(100, max(40, ((int(comp_y_max_raw) // 10) + 1) * 10))

    return f"""<script>
(function(){{
const INK = '#0d253d', MUTED = '#5a7184', GRID = '#edf2f7', LINE = '#e3e8ee';
const FONT_BASE = "'Inter','Noto Sans SC',sans-serif";
const FONT_MONO = "'IBM Plex Mono',monospace";
if (window.Chart && Chart.defaults) {{
  Chart.defaults.font.family = FONT_BASE;
  Chart.defaults.color = MUTED;
  Chart.defaults.font.size = 12;
}}
const dashboard = {js({k: data.get(k) for k in ('brand_name', 'target_domain', 'delivery_language')})};
const baseOptions = {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}}}}};
const radarOptions = {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{display:false}}}}, scales:{{r:{{beginAtZero:true,max:100,ticks:{{stepSize:25,backdropColor:'transparent',color:'#a99bd5'}},grid:{{color:LINE}},angleLines:{{color:LINE}},pointLabels:{{color:INK,font:{{size:11}}}}}}}}}};
const platformBubbleOptions = {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}, tooltip:{{callbacks:{{label:function(ctx){{var d=ctx.raw||{{}};return {js(tooltip_plat_tpl)}.replace('{{name}}',ctx.dataset.label).replace('{{x}}',d.x).replace('{{y}}',d.y).replace('{{n}}',d.n||0);}}}}}}}}, scales:{{x:{{min:0,max:100,title:{{display:true,text:{js(plat_bubble_x)},color:INK,font:{{size:12,weight:'600'}}}},grid:{{color:GRID}}}}, y:{{min:0,max:100,title:{{display:true,text:{js(plat_bubble_y)},color:INK,font:{{size:12,weight:'600'}}}},grid:{{color:GRID}}}}}}}};
const matrixQuadrant = {{
  id:'matrixQuadrant',
  beforeDraw:function(chart){{
    var a=chart.chartArea; if(!a) return;
    var xs=chart.scales.x, ys=chart.scales.y;
    var xMid=xs.getPixelForValue(50), yMid=ys.getPixelForValue(50);
    var c=chart.ctx; c.save();
    // ideal zone = high visibility + low takeover (bottom-right)
    c.fillStyle='rgba(14,165,233,0.06)';
    c.fillRect(xMid, yMid, a.right-xMid, a.bottom-yMid);
    c.strokeStyle='#cdd7e2'; c.lineWidth=1; c.setLineDash([5,5]);
    c.beginPath(); c.moveTo(xMid,a.top); c.lineTo(xMid,a.bottom); c.stroke();
    c.beginPath(); c.moveTo(a.left,yMid); c.lineTo(a.right,yMid); c.stroke();
    c.setLineDash([]); c.font="11px 'Inter','Noto Sans SC',sans-serif";
    c.fillStyle='#5a7184';
    c.textAlign='right'; c.fillText({js(matrix_ideal)}, a.right-8, a.bottom-8);
    c.textAlign='left'; c.fillText({js(matrix_risk)}, a.left+8, a.top+14);
    c.restore();
  }}
}};
const competitorScatterOptions = {{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}, tooltip:{{callbacks:{{label:function(ctx){{var proxy=ctx.dataset.borderDash&&ctx.dataset.borderDash.length;var tag=proxy?{js(tooltip_comp_proxy)}:'';return {js(tooltip_comp_tpl)}.replace('{{name}}',ctx.dataset.label).replace('{{x}}',ctx.parsed.x).replace('{{y}}',ctx.parsed.y).replace('{{tag}}',tag);}}}}}}}}, scales:{{x:{{min:0,max:100,title:{{display:true,text:{js(bubble_x)},color:INK,font:{{size:12,weight:'600'}}}},grid:{{color:GRID}}}}, y:{{min:0,max:{comp_bubble_y_max},title:{{display:true,text:{js(bubble_y)},color:INK,font:{{size:12,weight:'600'}}}},grid:{{color:GRID}}}}}}}};
const sampleBarYLabelWidth = {112 if not latin else 132};
const sampleBarOptions = {{
  indexAxis:'y', responsive:true, maintainAspectRatio:false,
  layout:{{padding:{{left:2,right:4,top:2,bottom:2}}}},
  scales:{{
    x:{{stacked:true, min:0, max:100, ticks:{{callback:function(v){{return v+'%';}},color:MUTED,font:{{size:10}}}}, grid:{{color:GRID}}}},
    y:{{
      stacked:true,
      grid:{{display:false}},
      afterFit:function(scale){{ scale.width = sampleBarYLabelWidth; }},
      ticks:{{
        color:INK,
        font:{{size:window.innerWidth<640?10:11,weight:'600'}},
        autoSkip:false,
        maxRotation:0,
        minRotation:0,
        crossAlign:'near',
        padding:4
      }}
    }}
  }},
  plugins:{{
    legend:{{display:false}},
    tooltip:{{callbacks:{{
      title:function(){{return '';}},
      label:function(ctx){{
      var d=ctx.dataset, i=ctx.dataIndex;
      var lbl=(d.segLabels&&d.segLabels[i])?d.segLabels[i]:d.label;
      return {js(tooltip_seg_tpl)}.replace('{{label}}',lbl).replace('{{count}}',d.counts[i]).replace('{{total}}',d.totals[i]).replace('{{pct}}',ctx.parsed.x);
    }}}}}}
  }}
}};
function mountSampleBar(id, labels, datasets, fontWeight) {{
  var el = document.getElementById(id);
  if (!el) return;
  var yTicks = Object.assign({{}}, sampleBarOptions.scales.y.ticks, {{
    font: Object.assign({{}}, sampleBarOptions.scales.y.ticks.font, {{weight: fontWeight || '600'}})
  }});
  var opts = Object.assign({{}}, sampleBarOptions, {{
    scales: Object.assign({{}}, sampleBarOptions.scales, {{
      y: Object.assign({{}}, sampleBarOptions.scales.y, {{ticks: yTicks}})
    }})
  }});
  new Chart(el, {{ type:'bar', data:{{labels:labels, datasets:datasets}}, options:opts }});
}}
mountSampleBar('sampleBarRecognized', {js(sample_bar_recognized_labels)}, {js(sample_bar_recognized_datasets)}, '700');
mountSampleBar('sampleBarBranded', {js(sample_bar_branded_labels)}, {js(sample_bar_branded_datasets)}, '500');
mountSampleBar('sampleBarCited', {js(sample_bar_cited_labels)}, {js(sample_bar_cited_datasets)}, '500');
mountSampleBar('sampleBarUnbranded', {js(sample_bar_unbranded_labels)}, {js(sample_bar_unbranded_datasets)}, '700');
new Chart(document.getElementById('platMatrix'), {{
  type:'bubble',
  data:{{datasets:{js(matrix_datasets)}}},
  options:platformBubbleOptions,
  plugins:[matrixQuadrant]
}});
new Chart(document.getElementById('authRadar'), {{
  type:'radar',
  data:{{labels:{js(auth.get('axes', []))}, datasets:[{{label:{js(radar_industry)}, data:{js(auth.get('industry_baseline_scores', []))}, borderColor:'#0ea5e9', backgroundColor:'rgba(14,165,233,0.14)', borderWidth:2}}, {{label:{js(brand_current)}, data:{js(auth.get('target_scores', []))}, borderColor:'#533afd', backgroundColor:'rgba(83,58,253,0.18)', borderWidth:2}}]}},
  options:radarOptions
}});
new Chart(document.getElementById('srcBar'), {{
  type:'bar',
  data:{{labels:{js([x.get('name') for x in source_channels])}, datasets:[{{label:{js(brand_current)}, data:{js([x.get('target_score') for x in source_channels])}, backgroundColor:{js(src_colors)}, borderRadius:4, barPercentage:0.48, categoryPercentage:0.62, maxBarThickness:18}}, {{label:{js(industry_mean)}, data:{js([x.get('industry_score') for x in source_channels])}, backgroundColor:'#8a9bb0', borderRadius:4, barPercentage:0.48, categoryPercentage:0.62, maxBarThickness:18}}]}},
  options:{{responsive:true, maintainAspectRatio:false, plugins:{{legend:{{position:'bottom'}}}}, scales:{{y:{{beginAtZero:true,max:100,grid:{{color:GRID}}}}, x:{{grid:{{display:false}}}}}}}}
}});
new Chart(document.getElementById('compBubble'), {{
  type:'scatter',
  data:{{datasets:{js(comp_datasets)}}},
  options:competitorScatterOptions
}});
new Chart(document.getElementById('drBar'), {{
  type:'bar',
  data:{{labels:{js([x[0] for x in dr_rank])}, datasets:[{{label:{js(dr_label)}, data:{js([x[1] for x in dr_rank])}, backgroundColor:{js(dr_colors)}, borderRadius:3, barPercentage:0.46, categoryPercentage:0.7, maxBarThickness:16}}]}},
  options:{{responsive:true, maintainAspectRatio:false, indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:{{x:{{beginAtZero:true,max:{dr_axis_max},grid:{{color:GRID}}}}, y:{{grid:{{display:false}}}}}}}}
}});
}})();

(function(){{
  var CLOUD = {js((data.get("sentiment") or {}).get("word_cloud") or {})};
  var ROOT = document.getElementById('sentiWordCloud');
  if (!ROOT) return;
  var COLORS_POS = ['#0ea5e9','#0284c7','#0369a1','#14b8a6','#0d9488','#533afd','#6366f1','#7c3aed'];
  var COLORS_NEU = ['#64748b','#475569','#94a3b8','#78869a','#5b6b7c','#8a9bb0','#6b7c8f','#7d8fa3'];
  var COLORS_NEG = ['#dc2626','#ef4444','#f97316','#ea580c','#b91c1c','#c2410c','#e11d48','#9f1239'];
  var state = {{ polarity: 'positive', enhanced: {{}} }};
  var tipCountTpl = {js(ui(data, "senti_cloud_tooltip_count"))};

  function termsFor(polarity) {{
    var rows = (CLOUD && CLOUD[polarity]) || [];
    return rows.filter(function(r){{ return r && r.text; }}).map(function(r){{
      return {{
        text: String(r.text),
        count: Number(r.count || r.weight || 1) || 1,
        weight: Number(r.weight || r.count || 1) || 1
      }};
    }});
  }}

  function paletteFor(polarity) {{
    if (polarity === 'negative') return COLORS_NEG;
    if (polarity === 'neutral') return COLORS_NEU;
    return COLORS_POS;
  }}

  function showPane(polarity) {{
    state.polarity = polarity;
    ROOT.querySelectorAll('.senti-cloud-pane').forEach(function(pane){{
      var on = pane.getAttribute('data-polarity') === polarity;
      pane.classList.toggle('is-active', on);
      if (on) pane.removeAttribute('hidden');
      else pane.setAttribute('hidden', 'hidden');
    }});
    document.querySelectorAll('.senti-cloud-tab').forEach(function(b){{
      var on = (b.getAttribute('data-polarity') || '') === polarity;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    }});
    enhancePane(polarity);
  }}

  function enhancePane(polarity) {{
    if (!(window.d3 && d3.layout && typeof d3.layout.cloud === 'function')) return;
    if (state.enhanced[polarity]) return;
    var pane = ROOT.querySelector('.senti-cloud-pane[data-polarity="' + polarity + '"]');
    if (!pane) return;
    var host = pane.querySelector('[data-cloud-host]');
    if (!host) return;
    var terms = termsFor(polarity);
    if (!terms.length) return;
    var width = Math.max(host.clientWidth || ROOT.clientWidth || 640, 320);
    var height = Math.max(280, 320);
    var maxW = Math.max.apply(null, terms.map(function(t){{ return t.weight; }})) || 1;
    var palette = paletteFor(polarity);
    var layout = d3.layout.cloud()
      .size([width, height])
      .words(terms.map(function(t){{
        return {{ text: t.text, count: t.count, size: 14 + Math.round((t.weight / maxW) * 34) }};
      }}))
      .padding(4)
      .rotate(function(){{ return 0; }})
      .font("'Noto Sans SC','Inter',sans-serif")
      .fontSize(function(d){{ return d.size; }})
      .on('end', function(words){{
        host.innerHTML = '';
        var svg = d3.select(host).append('svg')
          .attr('width', width)
          .attr('height', height)
          .attr('viewBox', '0 0 ' + width + ' ' + height)
          .attr('role', 'img');
        var g = svg.append('g').attr('transform', 'translate(' + (width/2) + ',' + (height/2) + ')');
        g.selectAll('text').data(words).enter().append('text')
          .style('font-family', "'Noto Sans SC','Inter',sans-serif")
          .style('font-weight', '600')
          .style('font-size', function(d){{ return d.size + 'px'; }})
          .style('fill', function(d, i){{ return palette[i % palette.length]; }})
          .attr('text-anchor', 'middle')
          .attr('transform', function(d){{ return 'translate(' + [d.x, d.y] + ')rotate(' + d.rotate + ')'; }})
          .text(function(d){{ return d.text; }})
          .append('title')
          .text(function(d){{ return tipCountTpl.replace('{{count}}', String(d.count || 1)); }});
        state.enhanced[polarity] = true;
      }});
    layout.start();
  }}

  document.querySelectorAll('.senti-cloud-tab').forEach(function(btn){{
    btn.addEventListener('click', function(){{
      showPane(btn.getAttribute('data-polarity') || 'positive');
    }});
  }});

  var defaultPolarity = 'positive';
  var bestCount = -1;
  ['neutral', 'positive', 'negative'].forEach(function(p){{
    var n = termsFor(p).length;
    if (n > bestCount) {{
      bestCount = n;
      defaultPolarity = p;
    }}
  }});
  showPane(bestCount > 0 ? defaultPolarity : 'positive');
  window.addEventListener('resize', function(){{
    if (ROOT._cloudResizeTimer) clearTimeout(ROOT._cloudResizeTimer);
    ROOT._cloudResizeTimer = setTimeout(function(){{
      state.enhanced = {{}};
      showPane(state.polarity);
    }}, 180);
  }});
}})();
</script>"""


def render_html(raw: dict[str, Any], *, delivery_language: str = "", report_title: str = "") -> str:
    data = prepare_render_data(raw, delivery_language or str(raw.get("delivery_language") or "zh-Hans"))
    template = read_text(str(TEMPLATE_PATH))
    brand = data.get("brand_name") or ""
    title = report_title or f"{brand} {ui(data, 'report_title_suffix')}"
    body = build_body(data)
    html_lang = locale_bcp47(str(data.get("delivery_language") or delivery_language or "zh-Hans"))
    html_dir = "rtl" if html_lang.lower().split("-")[0] in {"ar", "fa", "he", "ur"} else "ltr"
    insight_label = ui(data, "insight_label").replace("\\", "\\\\").replace('"', '\\"')
    return (
        template.replace("{{TITLE}}", e(title))
        .replace("{{BODY_CONTENT}}", body)
        .replace("{{INSIGHT_LABEL}}", insight_label)
        .replace('lang="zh-CN"', f'lang="{html_lang}" dir="{html_dir}"')
    )


def render(args: argparse.Namespace) -> None:
    raw = load_json(args.dashboard_data_file)
    output = render_html(
        raw,
        delivery_language=args.delivery_language,
        report_title=args.report_title,
    )
    out_path = Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"[masked-dashboard-html] wrote {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Magup masked sales dashboard HTML from dashboard JSON.")
    parser.add_argument("--dashboard-data-file", required=True)
    parser.add_argument("--template-file", default="skills/renders/render-magup-masked-sales-html/template.html")
    parser.add_argument("--brand-name", default="")
    parser.add_argument("--target-domain", default="")
    parser.add_argument("--delivery-language", default="en")
    parser.add_argument("--report-title", default="")
    parser.add_argument("--output-file", required=True)
    args = parser.parse_args()
    render(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
