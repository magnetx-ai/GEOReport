"""Magup masked-sales dashboard i18n helpers (ADR 007 Phase A).

v2 schema: shared metrics + per-locale copy packs.
Renderers flatten v2 to a legacy-compatible view dict via ``flatten_v2_for_render``.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_V2 = "magup-masked-sales-dashboard-v2-i18n"

LOCALE_ALIASES = {
    "zh": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-hans": "zh-Hans",
    "chinese": "zh-Hans",
    "en": "en",
    "english": "en",
    "ar": "ar",
    "arabic": "ar",
    "pt": "pt-PT",
    "pt-pt": "pt-PT",
    "portuguese": "pt-PT",
    "pt-br": "pt-BR",
    "brazilian-portuguese": "pt-BR",
    "fr": "fr",
    "french": "fr",
    "de": "de",
    "german": "de",
    "es": "es",
    "spanish": "es",
    "ja": "ja",
    "japanese": "ja",
    "jp": "ja",
}

BCP47 = {
    "zh-Hans": "zh-CN",
    "en": "en",
    "ar": "ar",
    "pt-PT": "pt-PT",
    "pt-BR": "pt-BR",
    "fr": "fr",
    "ja": "ja",
}

# Keys whose string values belong in locale packs (not shared evidence).
LOCALE_STRING_PATHS = (
    "cover",
    "narrative_copy",
    "ui_copy",
    "chart_labels",
    "recommendations",
    "channel_gap_cards",
    "root_cause_stack",
    "boundary",
    "raw_summary",
    "qa_section",
    "unbranded_ranking",
)

SHARED_TOP_LEVEL_KEYS = (
    "schema_version",
    "generated_at",
    "brand_name",
    "target_domain",
    "delivery_language",
    "executive_kpis",
    "top_distribution",
    "platform_performance",
    "authority_radar",
    "source_quality",
    "competitor_gap",
    # Builder emits `sentiment` / `competitor_ranking`; keep legacy aliases too.
    "sentiment",
    "sentiment_analysis",
    "competitor_ranking",
    "unbranded_ranking",
    "prompt_explorer",
    "citation_source_ranking",
)


# GEO-ML-REVIEW:#13a normalize_locale — locale 字符串归一
def normalize_locale(value: str | None, default: str = "en") -> str:
    raw = str(value or "").strip()
    if not raw:
        return default
    key = raw.lower().replace("_", "-")
    return LOCALE_ALIASES.get(key, raw)


def locale_bcp47(locale: str) -> str:
    normalized = normalize_locale(locale)
    return BCP47.get(normalized, normalized)


def is_english_locale(locale: str) -> bool:
    return normalize_locale(locale).lower().startswith("en")


def is_cjk_locale(locale: str) -> bool:
    """True for Chinese delivery locales (zh-Hans / zh-*)."""
    return normalize_locale(locale).lower().startswith("zh")


# Chinese structural channel / axis labels → delivery-locale labels.
# Applied at render time so narrative leftovers and chart chrome stay consistent.
CHANNEL_LABEL_MAPS: dict[str, dict[str, str]] = {
    "en": {
        "官网": "Official site",
        "开发者文档": "Developer docs",
        "YouTube 视频": "YouTube videos",
        "Reddit / 论坛": "Reddit / forums",
        "媒体 / PR": "Media / PR",
        "B2B 评测 (G2 / Capterra)": "B2B reviews (G2 / Capterra)",
        "百科 / 知识库": "Encyclopedia / knowledge base",
        "百科权威": "Encyclopedia authority",
        "百科": "Encyclopedia",
        "媒体覆盖": "Media coverage",
        "媒体": "Media",
        "官方信源": "Official sources",
        "社区活跃 (Reddit / 论坛)": "Community activity (Reddit / forums)",
        "社区活跃": "Community activity",
        "专业度 (评测 / 口碑)": "Professional credibility (reviews)",
        "专业度": "Professional credibility",
        "有品牌问题官网引用率 (%)": "Branded-query official-site citation rate (%)",
        "无品牌 AI 可见度 (%)": "Unbranded AI visibility (%)",
        "信源引用占比 (%)": "Source citation share (%)",
    },
    "pt-BR": {
        "官网": "Site oficial",
        "开发者文档": "Documentação para desenvolvedores",
        "YouTube 视频": "Vídeos no YouTube",
        "Reddit / 论坛": "Reddit / fóruns",
        "媒体 / PR": "Mídia / PR",
        "B2B 评测 (G2 / Capterra)": "Avaliações B2B (G2 / Capterra)",
        "百科 / 知识库": "Enciclopédia / base de conhecimento",
        "百科权威": "Autoridade em enciclopédias",
        "百科": "Enciclopédia",
        "媒体覆盖": "Cobertura de mídia",
        "媒体": "Mídia",
        "官方信源": "Fontes oficiais",
        "社区活跃 (Reddit / 论坛)": "Atividade na comunidade (Reddit / fóruns)",
        "社区活跃": "Atividade na comunidade",
        "专业度 (评测 / 口碑)": "Credibilidade profissional (avaliações)",
        "专业度": "Credibilidade profissional",
        "有品牌问题官网引用率 (%)": "Taxa de citação do site oficial em consultas com marca (%)",
        "无品牌 AI 可见度 (%)": "Visibilidade de IA sem marca (%)",
        "信源引用占比 (%)": "Participação de citações de fontes (%)",
    },
    "pt-PT": {
        "官网": "Site oficial",
        "开发者文档": "Documentação para programadores",
        "YouTube 视频": "Vídeos no YouTube",
        "Reddit / 论坛": "Reddit / fóruns",
        "媒体 / PR": "Media / PR",
        "B2B 评测 (G2 / Capterra)": "Avaliações B2B (G2 / Capterra)",
        "百科 / 知识库": "Enciclopédia / base de conhecimento",
        "百科权威": "Autoridade em enciclopédias",
        "百科": "Enciclopédia",
        "媒体覆盖": "Cobertura mediática",
        "媒体": "Media",
        "官方信源": "Fontes oficiais",
        "社区活跃 (Reddit / 论坛)": "Atividade na comunidade (Reddit / fóruns)",
        "社区活跃": "Atividade na comunidade",
        "专业度 (评测 / 口碑)": "Credibilidade profissional (avaliações)",
        "专业度": "Credibilidade profissional",
        "有品牌问题官网引用率 (%)": "Taxa de citação do site oficial em consultas com marca (%)",
        "无品牌 AI 可见度 (%)": "Visibilidade de IA sem marca (%)",
        "信源引用占比 (%)": "Participação de citações de fontes (%)",
    },
}


def channel_label_map_for_locale(locale: str) -> dict[str, str]:
    code = normalize_locale(locale)
    if code in CHANNEL_LABEL_MAPS:
        return dict(CHANNEL_LABEL_MAPS[code])
    if not is_cjk_locale(code):
        return dict(CHANNEL_LABEL_MAPS["en"])
    return {}


def apply_channel_labels_to_text(text: str, locale: str) -> str:
    """Replace known Chinese channel/axis labels inside free text."""
    if not text or is_cjk_locale(locale):
        return text
    mapping = channel_label_map_for_locale(locale)
    if not mapping:
        return text
    out = str(text)
    for zh, localized in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
        if zh in out:
            out = out.replace(zh, localized)
    return out


# Display labels for authority radar (scores stay in shared; labels follow delivery language).
AUTHORITY_RADAR_AXES: dict[str, list[str]] = {
    "zh-Hans": ["官方信源", "百科权威", "媒体覆盖", "社区活跃 (Reddit / 论坛)", "专业度 (评测 / 口碑)"],
    "zh-Hant": ["官方信源", "百科權威", "媒體覆蓋", "社區活躍 (Reddit / 論壇)", "專業度 (評測 / 口碑)"],
    "en": [
        "Official source",
        "Encyclopedic authority",
        "Media coverage",
        "Community (Reddit / forums)",
        "Professional depth",
    ],
    "pt-BR": [
        "Fonte oficial",
        "Autoridade enciclopédica",
        "Cobertura de mídia",
        "Comunidade (Reddit / fóruns)",
        "Profundidade profissional",
    ],
    "pt-PT": [
        "Fonte oficial",
        "Autoridade enciclopédica",
        "Cobertura mediática",
        "Comunidade (Reddit / fóruns)",
        "Profundidade profissional",
    ],
    "ja": [
        "公式ソース",
        "百科権威",
        "メディア露出",
        "コミュニティ（Reddit / フォーラム）",
        "専門性（レビュー / 評判）",
    ],
}

AUTHORITY_RADAR_CAVEAT: dict[str, str] = {
    "zh-Hans": (
        "官方信源 = 官网域名权威分与 AI 引用率加权（6:4，均为实测）；"
        "百科/媒体/社区/专业度为方向性代理估算，非全市场基准。"
    ),
    "en": (
        "Official source = weighted official-domain authority and AI citation rate (measured); "
        "encyclopedia / media / community / professional axes are directional proxies, not full-market benchmarks."
    ),
    "pt-BR": (
        "Fonte oficial = autoridade do domínio oficial e taxa de citação por IA (6:4, medido); "
        "eixos de enciclopédia / mídia / comunidade / profundidade são proxies direcionais."
    ),
    "pt-PT": (
        "Fonte oficial = autoridade do domínio oficial e taxa de citação por IA (6:4, medido); "
        "eixos de enciclopédia / media / comunidade / profundidade são proxies direcionais."
    ),
    "ja": (
        "公式ソース = 公式ドメイン権威とAI引用率の加重（6:4、実測）；"
        "百科 / メディア / コミュニティ / 専門性は方向性の代理指標であり、全市場ベンチマークではない。"
    ),
}


def authority_radar_axes_for_locale(locale: str) -> list[str]:
    code = normalize_locale(locale)
    if code in AUTHORITY_RADAR_AXES:
        return list(AUTHORITY_RADAR_AXES[code])
    if code.startswith("zh"):
        return list(AUTHORITY_RADAR_AXES["zh-Hans"])
    if code.startswith("pt"):
        return list(AUTHORITY_RADAR_AXES["pt-BR"])
    if code.startswith("ja"):
        return list(AUTHORITY_RADAR_AXES["ja"])
    return list(AUTHORITY_RADAR_AXES["en"])


def authority_radar_caveat_for_locale(locale: str) -> str:
    code = normalize_locale(locale)
    if code in AUTHORITY_RADAR_CAVEAT:
        return AUTHORITY_RADAR_CAVEAT[code]
    if code.startswith("zh"):
        return AUTHORITY_RADAR_CAVEAT["zh-Hans"]
    if code.startswith("pt"):
        return AUTHORITY_RADAR_CAVEAT["pt-BR"]
    return AUTHORITY_RADAR_CAVEAT["en"]


# GEO-ML-REVIEW:#15 localize_authority_radar — 雷达轴 / caveat 本地化
def localize_authority_radar(data: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    """Rewrite authority radar axes/caveat for delivery language; keep numeric scores."""
    loc = normalize_locale(locale or data.get("delivery_language") or "en")
    auth = dict(data.get("authority_radar") or {})
    if not auth:
        return data
    axes = list(auth.get("axes") or [])
    # Preserve score alignment: only replace labels when axis count matches canonical (5),
    # or when empty (fill canonical). Mismatched custom lengths keep original labels.
    canonical = authority_radar_axes_for_locale(loc)
    if not axes or len(axes) == len(canonical):
        auth["axes"] = canonical
    caveat = str(auth.get("caveat") or "")
    # Replace caveat whenever missing or language-mismatched vs delivery locale.
    needs_caveat = not caveat.strip()
    if not needs_caveat:
        if is_cjk_locale(loc) and not _has_cjk(caveat):
            needs_caveat = True
        elif (not is_cjk_locale(loc)) and _has_cjk(caveat):
            needs_caveat = True
    if needs_caveat:
        auth["caveat"] = authority_radar_caveat_for_locale(loc)
    data["authority_radar"] = auth
    return data


# GEO-ML-REVIEW:#17 apply_channel_label_locale — 渠道结构标签本地化
def apply_channel_label_locale(data: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    """Localize structural Chinese channel/axis labels for non-zh delivery."""
    loc = normalize_locale(locale or data.get("delivery_language") or "en")
    if is_cjk_locale(loc):
        return data
    mapping = channel_label_map_for_locale(loc)
    if not mapping:
        return data

    def map_name(value: Any) -> Any:
        if not isinstance(value, str) or not value:
            return value
        name = value
        for zh, localized in sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True):
            if zh in name:
                return name.replace(zh, localized)
        return name

    out = data

    sq = dict(out.get("source_quality") or {})
    channels = []
    for ch in sq.get("channels") or []:
        row = dict(ch)
        row["name"] = map_name(row.get("name"))
        channels.append(row)
    if channels:
        sq["channels"] = channels
        out["source_quality"] = sq

    auth = dict(out.get("authority_radar") or {})
    if auth.get("axes"):
        auth["axes"] = [map_name(a) for a in auth.get("axes") or []]
        out["authority_radar"] = auth
    if isinstance(auth.get("caveat"), str) and _has_cjk(auth["caveat"]):
        auth["caveat"] = apply_channel_labels_to_text(auth["caveat"], loc)
        out["authority_radar"] = auth

    cards = []
    for card in out.get("channel_gap_cards") or []:
        row = dict(card)
        row["channel"] = map_name(row.get("channel"))
        if isinstance(row.get("description"), str):
            row["description"] = apply_channel_labels_to_text(row["description"], loc)
        if isinstance(row.get("headline"), str):
            row["headline"] = apply_channel_labels_to_text(row["headline"], loc)
        cards.append(row)
    if cards:
        out["channel_gap_cards"] = cards

    comp = dict(out.get("competitor_gap") or {})
    axes_obj = dict(comp.get("bubble_axes") or {})
    changed_axes = False
    for key in ("x", "y", "y_definition"):
        if key in axes_obj and isinstance(axes_obj[key], str):
            mapped = apply_channel_labels_to_text(axes_obj[key], loc)
            if mapped != axes_obj[key]:
                axes_obj[key] = mapped
                changed_axes = True
    if changed_axes:
        comp["bubble_axes"] = axes_obj
        out["competitor_gap"] = comp
    if isinstance(comp.get("bubble_data_source"), str):
        comp["bubble_data_source"] = apply_channel_labels_to_text(comp["bubble_data_source"], loc)
        out["competitor_gap"] = comp

    nc = dict(out.get("narrative_copy") or {})
    nc_changed = False
    for key, val in list(nc.items()):
        if isinstance(val, str) and _has_cjk(val):
            mapped = apply_channel_labels_to_text(val, loc)
            if mapped != val:
                nc[key] = mapped
                nc_changed = True
    if nc_changed:
        out["narrative_copy"] = nc

    recs = []
    recs_changed = False
    for rec in out.get("recommendations") or []:
        row = dict(rec)
        for key in ("action", "why", "expected_metric_change"):
            if isinstance(row.get(key), str) and _has_cjk(row[key]):
                mapped = apply_channel_labels_to_text(row[key], loc)
                if mapped != row[key]:
                    row[key] = mapped
                    recs_changed = True
        recs.append(row)
    if recs_changed:
        out["recommendations"] = recs

    stack = dict(out.get("root_cause_stack") or {})
    layers = []
    stack_changed = False
    for layer in stack.get("layers") or []:
        row = dict(layer)
        for key in ("name", "layer", "evidence"):
            if isinstance(row.get(key), str) and _has_cjk(row[key]):
                mapped = apply_channel_labels_to_text(row[key], loc)
                if mapped != row[key]:
                    row[key] = mapped
                    stack_changed = True
        layers.append(row)
    if stack_changed:
        stack["layers"] = layers
        out["root_cause_stack"] = stack

    return out


# GEO-ML-REVIEW:#13 get_ui_strings — 静态 chrome 词典（缺包时非中文回落 en）
def get_ui_strings(locale: str) -> dict[str, str]:
    catalog, _fallback = resolve_ui_strings(locale)
    return catalog


def resolve_ui_strings(locale: str) -> tuple[dict[str, str], str | None]:
    """Return (ui_copy, chrome_fallback_locale_or_None)."""
    code = normalize_locale(locale)
    if code in _UI_STRINGS:
        return dict(_UI_STRINGS[code]), None
    # Non-Chinese locales without a dedicated catalog fall back to English chrome
    # (Arabic previously fell through to zh-Hans, so RTL reports stayed Chinese).
    if is_cjk_locale(code):
        return dict(_UI_STRINGS["zh-Hans"]), "zh-Hans" if code != "zh-Hans" else None
    return dict(_UI_STRINGS["en"]), "en"


def t(view: dict[str, Any], key: str, **fmt: Any) -> str:
    """Resolve UI string for render view (flat or flattened v2)."""
    ui = view.get("ui_copy") or {}
    if key in ui:
        text = str(ui[key])
    else:
        lang = normalize_locale(str(view.get("delivery_language") or "en"))
        text = str(get_ui_strings(lang).get(key, key))
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, ValueError):
            return text
    return text


def pending_label(view: dict[str, Any]) -> str:
    return t(view, "status_pending")


# GEO-ML-REVIEW:#32a extract_locale_pack — 从 flat 抽出 locales.{code} 文案包
def extract_locale_pack(flat: dict[str, Any]) -> dict[str, Any]:
    pack: dict[str, Any] = {}
    for key in LOCALE_STRING_PATHS:
        if key in flat and flat[key] is not None:
            pack[key] = copy.deepcopy(flat[key])
    if "ui_copy" not in pack:
        pack["ui_copy"] = get_ui_strings(str(flat.get("delivery_language") or "en"))
    if "chart_labels" not in pack:
        pack["chart_labels"] = _default_chart_labels(str(flat.get("delivery_language") or "en"))
    if "narrative_copy" not in pack and flat.get("narrative_copy"):
        pack["narrative_copy"] = copy.deepcopy(flat["narrative_copy"])
    return pack


def extract_shared(flat: dict[str, Any]) -> dict[str, Any]:
    shared: dict[str, Any] = {}
    for key in SHARED_TOP_LEVEL_KEYS:
        if key in flat:
            shared[key] = copy.deepcopy(flat[key])
    # Preserve nested evidence used by renderer but language-agnostic
    for key in (
        "sentiment",
        "sentiment_analysis",
        "prompt_explorer",
        "citation_source_ranking",
        "competitor_ranking",
        "unbranded_ranking",
    ):
        if key in flat and key not in shared:
            shared[key] = copy.deepcopy(flat[key])

    # Normalize aliases so renderers can always read the builder keys.
    sentiment = shared.get("sentiment") or shared.get("sentiment_analysis")
    if sentiment is not None:
        shared["sentiment"] = copy.deepcopy(sentiment)
        shared["sentiment_analysis"] = copy.deepcopy(sentiment)
    ranking = shared.get("competitor_ranking") or shared.get("unbranded_ranking")
    if ranking is not None:
        shared["competitor_ranking"] = copy.deepcopy(ranking)
        shared["unbranded_ranking"] = copy.deepcopy(ranking)

    shared["brand_name"] = flat.get("brand_name", "")
    shared["target_domain"] = flat.get("target_domain", "")
    shared["generated_at"] = flat.get("generated_at", "")
    return shared


def ensure_v2_shared_metrics(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure language-agnostic metric blocks survive in v2.shared (incl. older packs)."""
    if data.get("schema_version") != SCHEMA_V2:
        return data
    out = data
    shared = out.setdefault("shared", {})
    sentiment = shared.get("sentiment") or shared.get("sentiment_analysis")
    if _sentiment_total(sentiment) <= 0:
        # Pull raw_summary / prompt_explorer from any locale pack for rebuild.
        probe = copy.deepcopy(shared)
        for pack in (out.get("locales") or {}).values():
            if not isinstance(pack, dict):
                continue
            for key in ("raw_summary", "prompt_explorer", "qa_section"):
                if key not in probe and pack.get(key) is not None:
                    probe[key] = copy.deepcopy(pack[key])
        repaired = _rebuild_sentiment_from_view(probe)
        if repaired:
            sentiment = repaired
    if sentiment is not None:
        shared["sentiment"] = copy.deepcopy(sentiment)
        shared["sentiment_analysis"] = copy.deepcopy(sentiment)

    ranking = shared.get("competitor_ranking") or shared.get("unbranded_ranking")
    if ranking is None:
        for pack in (out.get("locales") or {}).values():
            if isinstance(pack, dict) and pack.get("unbranded_ranking") is not None:
                ranking = pack.get("unbranded_ranking")
                break
    if ranking is not None:
        shared["competitor_ranking"] = copy.deepcopy(ranking)
        shared["unbranded_ranking"] = copy.deepcopy(ranking)

    cite_rank = shared.get("citation_source_ranking")
    if cite_rank is None:
        for pack in (out.get("locales") or {}).values():
            if isinstance(pack, dict) and pack.get("citation_source_ranking") is not None:
                cite_rank = pack.get("citation_source_ranking")
                break
    if cite_rank is not None:
        shared["citation_source_ranking"] = copy.deepcopy(cite_rank)
    return out


def wrap_as_v2(
    flat: dict[str, Any],
    locale: str,
    *,
    source_locale: str | None = None,
) -> dict[str, Any]:
    loc = normalize_locale(locale)
    src = normalize_locale(source_locale or loc)
    pack = extract_locale_pack(flat)
    pack.setdefault("ui_copy", get_ui_strings(loc))
    return ensure_v2_shared_metrics(
        {
            "schema_version": SCHEMA_V2,
            "default_locale": loc,
            "requested_locales": [loc],
            "available_locales": [loc],
            "source_locale": src,
            "shared": extract_shared(flat),
            "locales": {loc: pack},
        }
    )


def _sentiment_total(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    try:
        return int(value.get("total") or 0)
    except (TypeError, ValueError):
        return 0


def _rebuild_sentiment_from_view(view: dict[str, Any]) -> dict[str, Any] | None:
    """Rebuild sentiment block for older v2 packs that dropped `sentiment` from shared."""
    summary = ((view.get("raw_summary") or {}).get("aeo_summary") or {})
    try:
        pos = int(summary.get("positive_count") or 0)
        neu = int(summary.get("neutral_count") or 0)
        neg = int(summary.get("negative_count") or 0)
    except (TypeError, ValueError):
        pos = neu = neg = 0

    by_platform: dict[str, dict[str, int]] = {}
    order: list[str] = []
    explorer = view.get("prompt_explorer") or view.get("qa_section") or {}
    for group in explorer.get("groups") or []:
        for ans in group.get("answers") or []:
            pid = str(ans.get("platform") or "Unknown").strip() or "Unknown"
            if pid not in by_platform:
                order.append(pid)
                by_platform[pid] = {"positive": 0, "neutral": 0, "negative": 0}
            sent = str(ans.get("brand_sentiment") or "neutral").lower()
            if sent not in ("positive", "negative"):
                sent = "neutral"
            by_platform[pid][sent] += 1

    if not order and (pos + neu + neg) <= 0:
        return None
    if (pos + neu + neg) <= 0 and by_platform:
        pos = sum(v["positive"] for v in by_platform.values())
        neu = sum(v["neutral"] for v in by_platform.values())
        neg = sum(v["negative"] for v in by_platform.values())
    total = pos + neu + neg
    if total <= 0:
        return None

    def _pct(n: int) -> float:
        return round(n / total * 100, 1) if total else 0.0

    return {
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "total": total,
        "positive_pct": _pct(pos),
        "neutral_pct": _pct(neu),
        "negative_pct": _pct(neg),
        "by_platform": [
            {"platform": p, **by_platform[p], "total": sum(by_platform[p].values())}
            for p in order
        ],
    }


def _normalize_sentiment_and_ranking(view: dict[str, Any]) -> dict[str, Any]:
    sentiment = view.get("sentiment") or view.get("sentiment_analysis")
    if _sentiment_total(sentiment) <= 0:
        repaired = _rebuild_sentiment_from_view(view)
        if repaired:
            sentiment = repaired
    if sentiment is not None:
        view["sentiment"] = copy.deepcopy(sentiment)
        view["sentiment_analysis"] = copy.deepcopy(sentiment)
    ranking = view.get("competitor_ranking") or view.get("unbranded_ranking")
    if ranking is not None:
        view["competitor_ranking"] = copy.deepcopy(ranking)
        view["unbranded_ranking"] = copy.deepcopy(ranking)
    return view


# GEO-ML-REVIEW:#32b flatten_v2_for_render — v2 shared+locales → 渲染用 flat
def flatten_v2_for_render(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != SCHEMA_V2:
        return _normalize_sentiment_and_ranking(copy.deepcopy(data))
    # Prefer explicit delivery_language so CLI/render target wins over stale default_locale.
    locale = normalize_locale(
        str(data.get("delivery_language") or data.get("default_locale") or "en")
    )
    locales = data.get("locales") if isinstance(data.get("locales"), dict) else {}
    pack = locales.get(locale) if isinstance(locales.get(locale), dict) else {}
    if not pack:
        # Fall back to default_locale pack when target pack is missing (caller may fail-closed).
        fallback_loc = normalize_locale(str(data.get("default_locale") or "en"))
        pack = locales.get(fallback_loc) if isinstance(locales.get(fallback_loc), dict) else {}
    shared = copy.deepcopy(data.get("shared") or {})
    view: dict[str, Any] = {**shared}
    view["delivery_language"] = locale
    view["default_locale"] = locale
    # Catalog wins: stale/wrong-language pack chrome must not override delivery locale.
    catalog, chrome_fallback = resolve_ui_strings(locale)
    view["ui_copy"] = {**(pack.get("ui_copy") or {}), **catalog}
    if chrome_fallback:
        view["chrome_fallback"] = chrome_fallback
    view["narrative_copy"] = copy.deepcopy(pack.get("narrative_copy") or {})
    view["chart_labels"] = {
        **(pack.get("chart_labels") or {}),
        **_default_chart_labels(locale),
    }
    for key in LOCALE_STRING_PATHS:
        if key in ("ui_copy", "chart_labels", "narrative_copy"):
            continue
        if key in pack:
            view[key] = copy.deepcopy(pack[key])
    # Legacy v1 used top-level cover
    if "cover" in pack:
        view["cover"] = copy.deepcopy(pack["cover"])
    return _normalize_sentiment_and_ranking(view)


# GEO-ML-REVIEW:#32c merge_v2_locales — 合并目标语 pack 进 v2
def merge_v2_locales(existing: dict[str, Any], locale: str, pack: dict[str, Any]) -> dict[str, Any]:
    loc = normalize_locale(locale)
    out = copy.deepcopy(existing)
    out.setdefault("locales", {})
    out["locales"][loc] = pack
    avail = set(out.get("available_locales") or [])
    avail.add(loc)
    out["available_locales"] = sorted(avail)
    out["default_locale"] = loc
    if loc not in (out.get("requested_locales") or []):
        out["requested_locales"] = [loc]
    return out


def _default_chart_labels(locale: str) -> dict[str, Any]:
    code = normalize_locale(locale)
    if code.lower().startswith("ja"):
        return {
            "funnel_tiers": ["可視", "要改善 / 競合", "不在"],
            "funnel_branded": "ブランド指名クエリ",
            "funnel_unbranded": "非ブランドクエリ",
            "radar_industry": "カテゴリ横断ベースライン",
            "radar_target_suffix": "現状",
            "bubble_x": "非ブランドAI可視性 (%)",
            "bubble_y": "ソース引用シェア (%)",
            "dr_label": "ドメイン権威スコア",
            "matrix_ideal": "理想ゾーン · 可視かつ競合少",
            "matrix_risk": "リスクゾーン · 不在かつ競合多",
            "platform_bubble_x": "非ブランド可視性（右ほど良い）",
            "platform_bubble_y": "競合占有率（低いほど良い）",
        }
    en = is_english_locale(code) or not str(code).lower().startswith("zh")
    if en:
        return {
            "funnel_tiers": ["Visible", "Needs improvement / competitor", "Absent"],
            "funnel_branded": "Branded queries",
            "funnel_unbranded": "Non-branded queries",
            "radar_industry": "Cross-category baseline",
            "radar_target_suffix": "current",
            "bubble_x": "Unbranded AI visibility (%)",
            "bubble_y": "Source citation share (%)",
            "dr_label": "Domain authority score",
            "matrix_ideal": "Ideal zone · visible, low competitor",
            "matrix_risk": "Risk zone · absent, high competitor",
            "platform_bubble_x": "Unbranded visibility (higher is better)",
            "platform_bubble_y": "Competitor share (lower is better)",
        }
    return {
        "funnel_tiers": ["我方可见", "需改进 / 被竞品占位", "完全缺席"],
        "funnel_branded": "品牌词提问",
        "funnel_unbranded": "不带品牌提问",
        "radar_industry": "跨类目基准",
        "radar_target_suffix": "当前",
        "bubble_x": "无品牌 AI 可见度 (%)",
        "bubble_y": "信源引用占比 (%)",
        "dr_label": "域名权威分",
        "matrix_ideal": "理想区 · 可见且少竞品",
        "matrix_risk": "高危区 · 缺席且多竞品",
        "platform_bubble_x": "无品牌可见度（越右越好）",
        "platform_bubble_y": "竞品占位率（越低越好）",
    }


def apply_english_locale(flat: dict[str, Any]) -> dict[str, Any]:
    """Post-process a zh-Hans dashboard dict into English chrome / missing copy.

    Important: do **not** replace existing Chinese narrative / recommendation /
    root-cause prose with short English templates. Those fields must be
    translated from the source conclusions (same facts, different language).
    Templates are only used when a key is missing or empty.
    """
    data = copy.deepcopy(flat)
    data["delivery_language"] = "en"
    data["ui_copy"] = get_ui_strings("en")
    data["chart_labels"] = _default_chart_labels("en")

    brand = str(data.get("brand_name") or "")
    domain = str(data.get("target_domain") or "")
    cover = dict(data.get("cover") or {})
    kpis = data.get("executive_kpis") or {}
    unbr = kpis.get("unbranded_visibility") or {}
    branded = kpis.get("branded_recognition") or {}
    takeover = kpis.get("competitor_takeover_when_target_absent") or {}
    dr_target = (kpis.get("domain_rating") or {}).get("target", "—")

    u_m, u_t = int(unbr.get("mentioned") or 0), int(unbr.get("total") or 0)
    b_m, b_t = int(branded.get("mentioned") or 0), int(branded.get("total") or 0)
    tk = int(takeover.get("count") or 0)
    branded_rate = round(b_m / b_t * 100) if b_t else 0

    if not cover.get("eyebrow") or _has_cjk(str(cover.get("eyebrow"))):
        cover["eyebrow"] = "Diagnostic report · sales edition"
    if not cover.get("headline") or _has_cjk(str(cover.get("headline"))):
        cover["headline"] = (
            f"{brand} AI recommendation visibility — branded recall {branded_rate}% on named queries; "
            f"category-query presence {u_m}/{u_t} with {tk} competitor takeovers when absent."
        )
    locked = bool(cover.get("business_definition_locked"))
    if not locked and (not cover.get("business_definition") or _has_cjk(str(cover.get("business_definition")))):
        cover["business_definition"] = f"GEO / AEO visibility and citation performance for {domain}"
    if not cover.get("audience") or _has_cjk(str(cover.get("audience"))):
        cover["audience"] = "Sales enablement, marketing stakeholders, and executive briefings"
    data["cover"] = cover

    # Fill English narrative templates only when keys are missing/empty.
    # Never overwrite existing Chinese conclusions — that produced lossy one-liners
    # (e.g. 400-char diagnosis → "systematic absence…") and wrong metrics.
    # Keys must match generate_magup_dashboard_narrative.REQUIRED_KEYS (and legacy aliases).
    section_06_insight = (
        f"Competitors score higher on external sources because of denser user-generated citations on "
        f"YouTube, Reddit, and industry media. {brand}'s owned content is fine, but third-party citation "
        f"density is lower on unbranded recommendations."
    )
    section_07_dr_note = (
        f"{brand} domain authority is {dr_target}; competitors cluster "
        f"in a similar range. DR measures backlink volume, not topical relevance — niche media citations "
        f"often weigh more for AI recommendations."
    )
    section_09_insight = (
        f"{brand} has mature site and brand assets, but most are built for humans and search engines, not AI "
        f"recommendation logic. Re-encode existing assets for machine-readable citation."
    )
    section_10_desc = (
        f"Three stacked gaps displace {brand} in AI recommendations: unclear boundaries → no citable pages "
        f"on non-branded queries → competitors with stronger signals win the slot."
    )
    section_11_insight = (
        "P0 always starts with official-site structure and citable on-site content (Schema, Meta, llms.txt, "
        "category entry pages). Off-site and social amplify that base — they should not come first. "
        "Bind every initiative to re-testable AI metrics (unbranded visibility, branded official-site citation rate)."
    )
    root_expression = (
        f"{brand}'s official site may be readable for humans, but incomplete machine-readable boundaries "
        f"(Schema / entity markup / citable sections) force models to infer positioning from free text."
    )
    root_supply = (
        f"Organic keywords, organic traffic, and domain authority remain thin for {brand}, so category "
        f"questions lack citable official pages AI can quote on unbranded recommendations."
    )
    root_distribution = (
        f"{brand} unbranded presence is {u_m}/{u_t}; competitors take over recommendation slots "
        f"{tk} times when the brand is absent. External amplification cannot fix a missing official entry point."
    )
    en_narrative = {
        "section_01_desc": (
            f"When buyers ask category questions before choosing a vendor, {brand} appears in {u_m}/{u_t} AI answers; "
            f"competitors fill the gap {tk} times when {brand} is absent."
        ),
        "main_insight": (
            f"The issue is not brand awareness — it is <b>systematic absence from AI recommendation slots</b> "
            f"on unbranded queries ({u_m}/{u_t} presence, {tk} competitor takeovers)."
        ),
        "section_06_insight": section_06_insight,
        "section_05_insight": section_06_insight,  # legacy
        "section_07_dr_note": section_07_dr_note,
        "section_06_dr_note": section_07_dr_note,  # legacy
        "section_09_insight": section_09_insight,
        "section_07_insight": section_09_insight,  # legacy
        "section_10_desc": section_10_desc,
        "section_08_desc": section_10_desc,  # legacy
        "section_11_insight": section_11_insight,
        "root_cause_expression": root_expression,
        "root_cause_supply": root_supply,
        "root_cause_distribution": root_distribution,
    }
    nc = dict(data.get("narrative_copy") or {})
    for key, en_text in en_narrative.items():
        if not str(nc.get(key) or "").strip():
            nc[key] = en_text
    data["narrative_copy"] = nc

    data = localize_authority_radar(data, "en")

    top = dict(data.get("top_distribution") or {})
    funnel = dict(top.get("funnel") or {})
    if funnel:
        funnel["tiers"] = data["chart_labels"]["funnel_tiers"]
        for scenario in funnel.get("scenarios") or []:
            name = str(scenario.get("name") or "")
            if "品牌" in name or _has_cjk(name) and "brand" not in name.lower():
                if (
                    "品类" in name
                    or "无品牌" in name
                    or "不带品牌" in name
                    or "category" in name.lower()
                    or "non-brand" in name.lower()
                    or "unbranded" in name.lower()
                ):
                    scenario["name"] = data["chart_labels"]["funnel_unbranded"]
                else:
                    scenario["name"] = data["chart_labels"]["funnel_branded"]
            for seg in scenario.get("segments") or []:
                label = str(seg.get("label") or "")
                seg_map = {
                    "完整可见": "Fully visible",
                    "部分可见": "Partially visible",
                    "品牌缺席": "Brand absent",
                    "我方出现": "Brand present",
                    "竞品占位": "Competitor takeover",
                    "全部缺席": "All absent",
                }
                if label in seg_map:
                    seg["label"] = seg_map[label]
                elif _has_cjk(label):
                    seg["label"] = "Other"
        top["funnel"] = funnel
        data["top_distribution"] = top
    donut = dict(top.get("donut") or {})
    if donut.get("labels") and any(_has_cjk(str(x)) for x in donut.get("labels") or []):
        donut["labels"] = [
            "Branded · fully visible",
            "Branded · partial",
            "Unbranded · absent + competitor",
            "Unbranded · all absent",
        ]
        top["donut"] = donut
        data["top_distribution"] = top

    sq = dict(data.get("source_quality") or {})
    channels = []
    name_map = channel_label_map_for_locale("en")
    for ch in sq.get("channels") or []:
        row = dict(ch)
        name = str(row.get("name") or "")
        mapped = False
        for zh, en in sorted(name_map.items(), key=lambda kv: len(kv[0]), reverse=True):
            if zh in name:
                row["name"] = name.replace(zh, en)
                mapped = True
                break
        if not mapped and _has_cjk(name):
            row["name"] = re.sub(r"[\u4e00-\u9fff]+", "", name).strip(" ·/-") or "Channel"
        channels.append(row)
    if channels:
        sq["channels"] = channels
        data["source_quality"] = sq

    comp = dict(data.get("competitor_gap") or {})
    axes_obj = dict(comp.get("bubble_axes") or {})
    if _has_cjk(str(axes_obj.get("x") or "")):
        axes_obj["x"] = "Unbranded AI visibility (%)"
    if _has_cjk(str(axes_obj.get("y") or "")):
        axes_obj["y"] = "Source citation share (%)"
    if axes_obj:
        comp["bubble_axes"] = axes_obj
    if _has_cjk(str(comp.get("bubble_data_source") or "")):
        comp["bubble_data_source"] = (
            "X-axis (unbranded AI visibility) is measured AEO co-occurrence for target and competitors; "
            "Y-axis source share is measured for the target and directional for competitors."
        )
    data["competitor_gap"] = comp

    data["root_cause_stack"] = _translate_root_cause_en(data.get("root_cause_stack") or {}, brand, u_m, u_t, tk)
    data["boundary"] = _translate_boundary_en(data.get("boundary") or {})
    data["recommendations"] = _translate_recommendations_en(data.get("recommendations") or [])
    data["channel_gap_cards"] = _translate_channel_cards_en(data.get("channel_gap_cards") or [])

    qa = data.get("qa_section") or data.get("prompt_explorer")
    if isinstance(qa, dict) and qa.get("note") and _has_cjk(str(qa["note"])):
        qa = dict(qa)
        qa["note"] = (
            "Expand any row to see real AI answer excerpts and classification rationale. "
            "Prompt wording may differ by platform for the same scenario."
        )
        if "qa_section" in data:
            data["qa_section"] = qa
        else:
            data["prompt_explorer"] = qa

    return apply_channel_label_locale(data, "en")


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


# Narrative fields rendered into HTML conclusions / root-cause body copy.
# Keep in sync with generate_magup_dashboard_narrative.REQUIRED_KEYS (+ legacy aliases).
_NARRATIVE_CJK_KEYS = (
    "section_01_desc",
    "main_insight",
    "section_06_insight",
    "section_05_insight",  # legacy
    "section_07_dr_note",
    "section_06_dr_note",  # legacy
    "section_09_insight",
    "section_07_insight",  # legacy
    "section_10_desc",
    "section_08_desc",  # legacy
    "section_11_insight",
    "root_cause_expression",
    "root_cause_supply",
    "root_cause_distribution",
)


def _display_has_residual_cjk(data: dict[str, Any]) -> bool:
    """True when non-Chinese delivery still contains user-visible Chinese leftovers.

    Covers narrative leftovers plus structural chrome baked into zh-Hans source data
    (radar axes, funnel tiers/segments, channel names, QA note, recs, cards, evidence,
    word-cloud labels). Answer bodies / Actual prompts are intentionally excluded.
    """
    samples: list[Any] = [
        (data.get("cover") or {}).get("headline"),
        (data.get("cover") or {}).get("audience"),
        (data.get("authority_radar") or {}).get("caveat"),
        (data.get("boundary") or {}).get("legal_boundary"),
    ]
    nc = data.get("narrative_copy") or {}
    for key in _NARRATIVE_CJK_KEYS:
        samples.append(nc.get(key))
    for layer in (data.get("root_cause_stack") or {}).get("layers") or []:
        if isinstance(layer, dict):
            samples.extend([layer.get("name"), layer.get("layer"), layer.get("evidence")])
    for card in data.get("channel_gap_cards") or []:
        if isinstance(card, dict):
            samples.extend(
                [card.get("channel"), card.get("headline"), card.get("description"), card.get("status")]
            )
    for rec in data.get("recommendations") or []:
        if isinstance(rec, dict):
            samples.extend(
                [rec.get("action"), rec.get("why"), rec.get("expected_metric_change"), rec.get("effort_band")]
            )

    auth = data.get("authority_radar") or {}
    samples.extend(auth.get("axes") or [])

    funnel = ((data.get("top_distribution") or {}).get("funnel") or {})
    samples.extend(funnel.get("tiers") or [])
    for scenario in funnel.get("scenarios") or []:
        samples.append(scenario.get("name"))
        for seg in scenario.get("segments") or []:
            samples.append(seg.get("label"))

    for ch in (data.get("source_quality") or {}).get("channels") or []:
        if isinstance(ch, dict):
            samples.append(ch.get("name"))

    qa = data.get("qa_section") or data.get("prompt_explorer") or {}
    if isinstance(qa, dict):
        samples.append(qa.get("note"))
        # Classification basis is user-visible; Actual prompt / answer_excerpt stay source language.
        for group in qa.get("groups") or []:
            if not isinstance(group, dict):
                continue
            for answer in group.get("answers") or []:
                if isinstance(answer, dict):
                    samples.append(answer.get("evidence"))

    for item in (data.get("boundary") or {}).get("proxy_estimates") or []:
        samples.append(item)

    # Sentiment word-cloud labels are delivery chrome when they were wrongly translated.
    sentiment = data.get("sentiment") or data.get("sentiment_analysis") or {}
    cloud = sentiment.get("word_cloud") if isinstance(sentiment, dict) else {}
    if isinstance(cloud, dict):
        for polarity in ("positive", "neutral", "negative"):
            for term in cloud.get(polarity) or []:
                if isinstance(term, dict):
                    samples.append(term.get("text"))
                else:
                    samples.append(term)

    return any(_has_cjk(str(x or "")) for x in samples)


def _strip_cjk_keep_latin(text: str, *, fallback: str) -> str:
    """Drop CJK ideographs + CJK/fullwidth punctuation; keep Latin/numbers.

    Warning: the remnant is **not** a translation. Callers must not ship it as
    user-facing prose (SECTION 11 why/metric, root-cause evidence, etc.).
    """
    cleaned = re.sub(r"[\u4e00-\u9fff]+", " ", str(text or ""))
    cleaned = re.sub(r"[\u3000-\u303F\uFF00-\uFFEF「」『』【】]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·/-，。；：、")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·/-.,;:()[]{}|")
    return cleaned or fallback


_CJK_PUNCT_RE = re.compile(r"[\u3000-\u303F\uFF00-\uFFEF「」『』【】]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")


def _has_cjk_punctuation(text: str) -> bool:
    return bool(_CJK_PUNCT_RE.search(str(text or "")))


def looks_like_cjk_strip_garbage(text: str) -> bool:
    """True when text looks like CJK-stripped punctuation soup, not real prose.

    Classic failure: Chinese why → delete Han chars → leave ``AI Brand, 。：HTML / 、H1。``.
    Real Chinese prose (contains Han) is never treated as strip-garbage.
    Short clean Latin labels (e.g. actions) are also not garbage.
    """
    sample = str(text or "").strip()
    if not sample:
        return True
    # Genuine CJK copy uses ideographs; leftover punct-only soup does not.
    if _has_cjk(sample):
        return False
    if _has_cjk_punctuation(sample):
        return True
    if "( )" in sample or "（ ）" in sample or re.search(r"\(\s*\)", sample):
        return True

    letters = sum(1 for ch in sample if ch.isalpha())
    punct = sum(1 for ch in sample if not ch.isalnum() and not ch.isspace())
    words = _LATIN_WORD_RE.findall(sample)

    # Short clean Latin titles/actions are valid ("Ship Schema markup").
    if len(sample) <= 64 and letters >= 8 and punct <= max(3, len(words)) and words:
        return False

    if letters < 12:
        return True
    if letters and punct / max(letters, 1) > 0.45:
        return True
    if len(words) < 4:
        return True
    # High density of tiny technical tokens + almost no function words → not prose.
    tiny = sum(1 for w in words if len(w) <= 4)
    if len(words) >= 4 and tiny / len(words) >= 0.75 and not re.search(
        r"\b(the|and|for|with|from|that|this|when|because|improve|build|missing|needs)\b",
        sample,
        re.I,
    ):
        return True
    return False


def is_usable_latin_prose(text: str, *, min_chars: int = 24, min_words: int = 4) -> bool:
    """Whether a string is acceptable Latin-script user-facing prose."""
    sample = str(text or "").strip()
    if len(sample) < min_chars:
        return False
    if _has_cjk(sample) or looks_like_cjk_strip_garbage(sample):
        return False
    return len(_LATIN_WORD_RE.findall(sample)) >= min_words


_DEFAULT_REC_WHY_EN = (
    "Improve AI-readable brand signals and third-party evidence for unbranded recommendation scenarios."
)
_DEFAULT_REC_METRIC_EN = "Higher unbranded visibility and official-site citation rate on re-test"


def sanitize_recommendation_prose(
    data_or_items: dict[str, Any] | list[Any],
    locale: str | None = None,
) -> dict[str, Any] | list[Any]:
    """Ensure recommendation why/metric/action are real prose for delivery language.

    Never treat CJK-strip remnants as a translation. For English delivery, replace
    unusable fields with stable defaults; for other non-zh locales, blank unusable
    fields so residual/LLM paths can regenerate (do not ship punctuation soup).
    """
    loc = normalize_locale(locale or "en")
    use_en_defaults = is_english_locale(loc)

    def _fix_items(items: list[Any]) -> list[Any]:
        out: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                out.append(item)
                continue
            row = dict(item)
            action = str(row.get("action") or "")
            why = str(row.get("why") or "")
            metric = str(row.get("expected_metric_change") or "")

            if is_cjk_locale(loc):
                # Chinese delivery: drop Latin-only / strip-garbage leftovers.
                if why and not _has_cjk(why) and (
                    looks_like_cjk_strip_garbage(why) or is_usable_latin_prose(why)
                ):
                    row["why"] = ""
                if metric and not _has_cjk(metric) and (
                    looks_like_cjk_strip_garbage(metric)
                    or is_usable_latin_prose(metric, min_chars=12, min_words=3)
                ):
                    row["expected_metric_change"] = ""
            else:
                # Non-Chinese: never ship CJK or strip-garbage as why/metric/action.
                if _has_cjk(action) or _has_cjk_punctuation(action):
                    row["action"] = "Recommended action" if use_en_defaults else ""
                elif looks_like_cjk_strip_garbage(action) and len(action) > 64:
                    row["action"] = "Recommended action" if use_en_defaults else ""
                if _has_cjk(why) or looks_like_cjk_strip_garbage(why) or not why.strip():
                    row["why"] = _DEFAULT_REC_WHY_EN if use_en_defaults else ""
                elif use_en_defaults and not is_usable_latin_prose(why):
                    row["why"] = _DEFAULT_REC_WHY_EN
                if _has_cjk(metric) or looks_like_cjk_strip_garbage(metric) or not metric.strip():
                    row["expected_metric_change"] = (
                        _DEFAULT_REC_METRIC_EN if use_en_defaults else ""
                    )
                elif use_en_defaults and not is_usable_latin_prose(
                    metric, min_chars=12, min_words=3
                ):
                    row["expected_metric_change"] = _DEFAULT_REC_METRIC_EN

            code = normalize_effort_band_code(row.get("effort_code") or row.get("effort_band"))
            row["effort_code"] = code
            row["effort_band"] = localize_effort_band(code, loc)
            out.append(row)
        return out

    if isinstance(data_or_items, list):
        return _fix_items(data_or_items)

    data = data_or_items
    if not isinstance(data, dict):
        return data
    recs = data.get("recommendations")
    if not isinstance(recs, list):
        return data
    out = dict(data)
    out["recommendations"] = _fix_items(recs)
    return out


def _scrub_prompt_explorer_evidence_en(explorer: dict[str, Any] | None) -> dict[str, Any]:
    """Deterministic EN fallback for classification evidence — no LLM, no Chinese leftovers."""
    if not isinstance(explorer, dict):
        return {}
    out = copy.deepcopy(explorer)
    note = str(out.get("note") or "")
    if _has_cjk(note):
        out["note"] = (
            "Expand any row to see real AI answer excerpts and classification rationale. "
            "Prompt wording may differ by platform for the same scenario."
        )
    for group in out.get("groups") or []:
        if not isinstance(group, dict):
            continue
        for answer in group.get("answers") or []:
            if not isinstance(answer, dict):
                continue
            evidence = str(answer.get("evidence") or "")
            if not _has_cjk(evidence):
                continue
            mentioned = bool(answer.get("mentioned"))
            # Prefer a short Latin remnant if present; otherwise use a stable EN note.
            remnant = _strip_cjk_keep_latin(evidence, fallback="")
            # Remnant is not a translation — only keep if it is already usable Latin prose.
            if remnant and is_usable_latin_prose(remnant, min_chars=12, min_words=4):
                answer["evidence"] = remnant
            elif mentioned:
                answer["evidence"] = (
                    "Brand mention flagged from the answer text; "
                    "see the answer excerpt above for supporting detail."
                )
            else:
                answer["evidence"] = (
                    "Brand name not found in the answer body "
                    "(classification note localized for delivery language)."
                )
    return out


def _scrub_word_cloud_cjk(data: dict[str, Any]) -> dict[str, Any]:
    """Drop word-cloud phrases that still contain CJK (answer-language rule already applied upstream)."""
    out = data
    sentiment = out.get("sentiment")
    if not isinstance(sentiment, dict):
        return out
    cloud = sentiment.get("word_cloud")
    if not isinstance(cloud, dict):
        return out
    next_cloud = dict(cloud)
    changed = False
    for polarity in ("positive", "neutral", "negative"):
        rows = cloud.get(polarity)
        if not isinstance(rows, list):
            continue
        kept = []
        for term in rows:
            if isinstance(term, dict):
                text = str(term.get("text") or "")
                if _has_cjk(text):
                    changed = True
                    continue
                kept.append(term)
            else:
                if _has_cjk(str(term)):
                    changed = True
                    continue
                kept.append(term)
        next_cloud[polarity] = kept
    if changed:
        sentiment = dict(sentiment)
        sentiment["word_cloud"] = next_cloud
        out = dict(out)
        out["sentiment"] = sentiment
    return out


def ensure_non_cjk_delivery(data: dict[str, Any], locale: str | None = None) -> dict[str, Any]:
    """Hard scrub user-visible Chinese leftovers for non-Chinese delivery locales.

    Deterministic (no LLM). Prefer apply_english_locale + this scrub over shipping CJK.
    """
    loc = normalize_locale(locale or data.get("delivery_language") or "en")
    if is_cjk_locale(loc):
        return data
    out = copy.deepcopy(data)
    out["delivery_language"] = loc
    if loc.lower().startswith("en"):
        out = apply_english_locale(out)
    # Recommendations / cards / root cause already remapped inside apply_english_locale for en;
    # still force-clear any residual CJK fields for en and other non-zh locales.
    out["recommendations"] = _translate_recommendations_en(out.get("recommendations") or [])
    out["channel_gap_cards"] = _translate_channel_cards_en(out.get("channel_gap_cards") or [])
    # Root-cause evidence: never keep Chinese under non-zh delivery.
    brand = str(out.get("brand_name") or "")
    kpis = out.get("executive_kpis") or {}
    unbr = kpis.get("unbranded_visibility") or {}
    takeover = kpis.get("competitor_takeover_when_target_absent") or {}
    u_m, u_t = int(unbr.get("mentioned") or 0), int(unbr.get("total") or 0)
    tk = int(takeover.get("count") or 0)
    out["root_cause_stack"] = _translate_root_cause_en(
        out.get("root_cause_stack") or {}, brand, u_m, u_t, tk
    )
    # Narrative: fill EN templates for any remaining CJK keys.
    if loc.lower().startswith("en"):
        nc = dict(out.get("narrative_copy") or {})
        # Re-run apply_english empty-only fill is insufficient when keys hold CJK;
        # replace CJK narrative with templates from a fresh apply pass on empty nc.
        stub = copy.deepcopy(out)
        stub["narrative_copy"] = {
            k: "" for k in set(_NARRATIVE_CJK_KEYS) | set((out.get("narrative_copy") or {}).keys())
        }
        filled = apply_english_locale(stub)
        filled_nc = filled.get("narrative_copy") or {}
        for key in _NARRATIVE_CJK_KEYS:
            if _has_cjk(str(nc.get(key) or "")):
                nc[key] = filled_nc.get(key) or nc.get(key)
        out["narrative_copy"] = nc
    explorer = out.get("prompt_explorer") or out.get("qa_section")
    if isinstance(explorer, dict):
        scrubbed = _scrub_prompt_explorer_evidence_en(explorer)
        out["prompt_explorer"] = scrubbed
        if "qa_section" in out:
            out["qa_section"] = scrubbed
    out = _scrub_word_cloud_cjk(out)
    out["ui_copy"] = {**(out.get("ui_copy") or {}), **get_ui_strings(loc)}
    out = apply_channel_label_locale(out, loc)
    out = localize_authority_radar(out, loc)
    return out


def warn_residual_cjk(data: dict[str, Any], locale: str | None = None) -> list[str]:
    """Return human-readable leftover buckets; never raise. Callers may still ship."""
    loc = normalize_locale(locale or data.get("delivery_language") or "en")
    if is_cjk_locale(loc) or not _display_has_residual_cjk(data):
        return []
    hits: list[str] = []
    for rec in data.get("recommendations") or []:
        if isinstance(rec, dict) and any(
            _has_cjk(str(rec.get(k) or "")) for k in ("why", "expected_metric_change", "action")
        ):
            hits.append("recommendations")
            break
    for card in data.get("channel_gap_cards") or []:
        if isinstance(card, dict) and _has_cjk(str(card.get("description") or "")):
            hits.append("channel_gap_cards")
            break
    qa = data.get("prompt_explorer") or data.get("qa_section") or {}
    if isinstance(qa, dict):
        for group in qa.get("groups") or []:
            for answer in (group.get("answers") or []) if isinstance(group, dict) else []:
                if isinstance(answer, dict) and _has_cjk(str(answer.get("evidence") or "")):
                    hits.append("prompt_explorer.evidence")
                    break
            if "prompt_explorer.evidence" in hits:
                break
    cloud = ((data.get("sentiment") or {}).get("word_cloud") or {})
    if isinstance(cloud, dict):
        for polarity in ("positive", "neutral", "negative"):
            for term in cloud.get(polarity) or []:
                text = term.get("text") if isinstance(term, dict) else term
                if _has_cjk(str(text or "")):
                    hits.append("sentiment.word_cloud")
                    break
            if "sentiment.word_cloud" in hits:
                break
    if not hits:
        hits.append("narrative_or_chrome")
    return hits


def assert_no_residual_cjk(data: dict[str, Any], locale: str | None = None) -> None:
    """Soft locale guard (compat name). Scrub leftovers elsewhere; never refuse to ship.

    Older call sites treated this as fail-closed. That aborted otherwise-usable reports
    after expensive collection. Prefer ensure_non_cjk_delivery + warn_residual_cjk.
    """
    leftovers = warn_residual_cjk(data, locale)
    if leftovers:
        loc = normalize_locale(locale or data.get("delivery_language") or "en")
        print(
            f"[locale-guard] delivery_language={loc} residual CJK after scrub in: "
            f"{', '.join(leftovers)} — shipping anyway; fix via chat revision / re-render.",
            flush=True,
        )


def _translate_root_cause_en(
    stack: dict[str, Any],
    brand: str,
    unbranded_mentioned: int,
    unbranded_total: int,
    takeover: int,
) -> dict[str, Any]:
    layers_in = list((stack or {}).get("layers") or [])
    defaults = [
        {
            "layer": "UPSTREAM",
            "name": "Expression gap",
            "evidence": "Machine-readable signals (Schema / semantic HTML / meta) are incomplete, so models must infer brand entities from free text.",
        },
        {
            "layer": "MIDSTREAM",
            "name": "Supply gap",
            "evidence": "Organic keywords, organic traffic, and domain authority remain thin, so category semantic coverage stays limited.",
        },
        {
            "layer": "DOWNSTREAM",
            "name": "Distribution gap",
            "evidence": (
                f"{brand} unbranded presence is {unbranded_mentioned}/{unbranded_total}; "
                f"competitors take over recommendation slots {takeover} times when the brand is absent."
            ),
        },
    ]
    layers = []
    for idx, default in enumerate(defaults):
        src = dict(layers_in[idx]) if idx < len(layers_in) else {}
        layer = dict(default)
        src_evidence = str(src.get("evidence") or "")
        # Keep client-specific evidence only when already in Latin script.
        if src_evidence and not _has_cjk(src_evidence):
            layer["evidence"] = src_evidence
            if src.get("name") and not _has_cjk(str(src.get("name"))):
                layer["name"] = src["name"]
            if src.get("layer") and not _has_cjk(str(src.get("layer"))):
                layer["layer"] = src["layer"]
        elif src_evidence and _has_cjk(src_evidence):
            # Never CJK-strip evidence into punctuation soup — keep English default layer copy.
            pass
        layers.append(layer)
    return {"layers": layers}


def _translate_boundary_en(boundary: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible EN helper — prefer ``localize_boundary``."""
    return localize_boundary(boundary, "en")


# Fixed conclusory boundary phrases (built in zh-Hans). Platform tokens like
# "ChatGPT 30" stay untouched. These are processed "data notes", not raw prompts.
_BOUNDARY_PHRASE_LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "官网抓取证据": "Official-site crawl evidence",
        "搜索流量/外链画像": "Search traffic / backlink profile",
        "搜索流量画像": "Search traffic profile",
        "AEO 提及与引用分类": "AEO mention and citation classification",
        "百科/媒体/社区/专业度（方向性，须为该客户独立调研的 channel_signals，禁止跨客户抄 stub）": (
            "Encyclopedia / media / community / professionalism "
            "(directional; must be client-specific researched channel_signals — no cross-client stub copy)"
        ),
        "竞品气泡 Y 可读性上调（基于提及×域名同现 + DR 地板）": (
            "Competitor bubble Y readability uplift (mention × domain co-occurrence + DR floor)"
        ),
        "竞品气泡 Y 可读性上调（基于提及x域名同现 + DR 地板）": (
            "Competitor bubble Y readability uplift (mention × domain co-occurrence + DR floor)"
        ),
        "跨类目基准雷达（固定对照，非客户实测）": (
            "Cross-category benchmark radar (fixed control, not client-measured)"
        ),
        "跨客户复制的 channel_signals stub": "Cross-client copied channel_signals stub",
        "把未测渠道写成 0 分实绩": "Treating untested channels as measured zero scores",
    },
    "pt-BR": {
        "官网抓取证据": "Evidência de crawl do site oficial",
        "搜索流量/外链画像": "Perfil de tráfego de busca / backlinks",
        "搜索流量画像": "Perfil de tráfego de busca",
        "AEO 提及与引用分类": "Classificação de menções e citações AEO",
        "百科/媒体/社区/专业度（方向性，须为该客户独立调研的 channel_signals，禁止跨客户抄 stub）": (
            "Enciclopédia / mídia / comunidade / profissionalismo "
            "(direcional; channel_signals pesquisados por cliente — sem copiar stub de outro cliente)"
        ),
        "竞品气泡 Y 可读性上调（基于提及×域名同现 + DR 地板）": (
            "Ajuste de legibilidade Y das bolhas de concorrentes "
            "(coocorrência menção × domínio + piso de DR)"
        ),
        "竞品气泡 Y 可读性上调（基于提及x域名同现 + DR 地板）": (
            "Ajuste de legibilidade Y das bolhas de concorrentes "
            "(coocorrência menção × domínio + piso de DR)"
        ),
        "跨类目基准雷达（固定对照，非客户实测）": (
            "Radar de referência cross-categoria (controle fixo, não medido no cliente)"
        ),
        "跨客户复制的 channel_signals stub": "Stub de channel_signals copiado de outro cliente",
        "把未测渠道写成 0 分实绩": "Tratar canais não testados como zero medido",
    },
    "pt-PT": {
        "官网抓取证据": "Evidência de crawl do site oficial",
        "搜索流量/外链画像": "Perfil de tráfego de pesquisa / backlinks",
        "搜索流量画像": "Perfil de tráfego de pesquisa",
        "AEO 提及与引用分类": "Classificação de menções e citações AEO",
        "百科/媒体/社区/专业度（方向性，须为该客户独立调研的 channel_signals，禁止跨客户抄 stub）": (
            "Enciclopédia / media / comunidade / profissionalismo "
            "(direcional; channel_signals investigados por cliente — sem copiar stub de outro cliente)"
        ),
        "竞品气泡 Y 可读性上调（基于提及×域名同现 + DR 地板）": (
            "Ajuste de legibilidade Y das bolhas de concorrentes "
            "(coocorrência menção × domínio + piso de DR)"
        ),
        "竞品气泡 Y 可读性上调（基于提及x域名同现 + DR 地板）": (
            "Ajuste de legibilidade Y das bolhas de concorrentes "
            "(coocorrência menção × domínio + piso de DR)"
        ),
        "跨类目基准雷达（固定对照，非客户实测）": (
            "Radar de referência cross-categoria (controlo fixo, não medido no cliente)"
        ),
        "跨客户复制的 channel_signals stub": "Stub de channel_signals copiado de outro cliente",
        "把未测渠道写成 0 分实绩": "Tratar canais não testados como zero medido",
    },
    "fr": {
        "官网抓取证据": "Preuve de crawl du site officiel",
        "搜索流量/外链画像": "Profil trafic de recherche / backlinks",
        "搜索流量画像": "Profil de trafic de recherche",
        "AEO 提及与引用分类": "Classification des mentions et citations AEO",
        "百科/媒体/社区/专业度（方向性，须为该客户独立调研的 channel_signals，禁止跨客户抄 stub）": (
            "Encyclopédie / médias / communauté / professionnalisme "
            "(indicatif ; channel_signals recherchés pour ce client — pas de stub copié)"
        ),
        "竞品气泡 Y 可读性上调（基于提及×域名同现 + DR 地板）": (
            "Relevé de lisibilité Y des bulles concurrentes "
            "(co-occurrence mention × domaine + plancher DR)"
        ),
        "竞品气泡 Y 可读性上调（基于提及x域名同现 + DR 地板）": (
            "Relevé de lisibilité Y des bulles concurrentes "
            "(co-occurrence mention × domaine + plancher DR)"
        ),
        "跨类目基准雷达（固定对照，非客户实测）": (
            "Radar de référence inter-catégories (témoin fixe, non mesuré client)"
        ),
        "跨客户复制的 channel_signals stub": "Stub channel_signals copié d'un autre client",
        "把未测渠道写成 0 分实绩": "Traiter des canaux non testés comme un zéro mesuré",
    },
    "ar": {
        "官网抓取证据": "أدلة زحف الموقع الرسمي",
        "搜索流量/外链画像": "ملف حركة البحث / الروابط الخلفية",
        "搜索流量画像": "ملف حركة البحث",
        "AEO 提及与引用分类": "تصنيف إشارات واستشهادات AEO",
        "百科/媒体/社区/专业度（方向性，须为该客户独立调研的 channel_signals，禁止跨客户抄 stub）": (
            "موسوعة / إعلام / مجتمع / احترافية "
            "(اتجاهي؛ channel_signals مبحوثة لهذا العميل — دون نسخ stub)"
        ),
        "竞品气泡 Y 可读性上调（基于提及×域名同现 + DR 地板）": (
            "رفع قابلية قراءة محور Y لفقاعات المنافسين "
            "(تزامن ذكر × نطاق + أرضية DR)"
        ),
        "竞品气泡 Y 可读性上调（基于提及x域名同现 + DR 地板）": (
            "رفع قابلية قراءة محور Y لفقاعات المنافسين "
            "(تزامن ذكر × نطاق + أرضية DR)"
        ),
        "跨类目基准雷达（固定对照，非客户实测）": (
            "رادار مرجعي عبر الفئات (شاهد ثابت، غير مقاس للعميل)"
        ),
        "跨客户复制的 channel_signals stub": "stub channel_signals منسوخ من عميل آخر",
        "把未测渠道写成 0 分实绩": "اعتبار القنوات غير المختبرة صفراً مقيساً",
    },
}


# GEO-ML-REVIEW:#16 localize_boundary — 底部数据说明列表（结论句，非 prompt/词云）
def localize_boundary(boundary: dict[str, Any] | None, locale: str) -> dict[str, Any]:
    """Localize conclusory boundary notes for delivery language.

    Contract: raw prompts / answer word-clouds stay original; processed notes must match locale.
    """
    loc = normalize_locale(locale)
    b = dict(boundary or {})
    if is_cjk_locale(loc):
        return b

    mapping = dict(_BOUNDARY_PHRASE_LOCALES.get(loc) or _BOUNDARY_PHRASE_LOCALES["en"])
    # Longest keys first so compound phrases win over short tokens.
    ordered = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)

    def _canon(text: str) -> str:
        out = str(text or "")
        out = out.replace("（", "(").replace("）", ")").replace("，", ",").replace("、", ",")
        out = out.replace("×", "x")
        return re.sub(r"\s+", " ", out).strip()

    canon_map = {_canon(zh): localized for zh, localized in mapping.items()}

    def _loose_pattern(zh: str) -> str:
        # Match builder phrases despite half/full-width punctuation or ×/x drift.
        parts: list[str] = []
        for ch in zh:
            if ch in "（(":
                parts.append("[(（]")
            elif ch in "）)":
                parts.append("[)）]")
            elif ch in "，,、":
                parts.append("[,，、]")
            elif ch in "×x":
                parts.append("[×x]")
            elif ch.isspace():
                parts.append(r"\s*")
            else:
                parts.append(re.escape(ch))
        return "".join(parts)

    def map_item(item: Any) -> str:
        text = str(item or "")
        if not text:
            return text
        if text in mapping:
            return mapping[text]
        canon = _canon(text)
        if canon in canon_map:
            return canon_map[canon]
        out = text
        for zh, localized in ordered:
            if zh in out:
                out = out.replace(zh, localized)
                continue
            if not _has_cjk(out):
                break
            try:
                out = re.sub(_loose_pattern(zh), localized, out)
            except re.error:
                pass
        if _has_cjk(out):
            cleaned = re.sub(r"[\u4e00-\u9fff]+", " ", out)
            cleaned = re.sub(r"\s+", " ", cleaned).strip(" ·/-,;:")
            return cleaned or out
        return out

    for field in ("tested_evidence", "not_independently_tested", "proxy_estimates", "forbidden"):
        rows = b.get(field)
        if isinstance(rows, list) and any(_has_cjk(str(x)) for x in rows):
            b[field] = [map_item(x) for x in rows]

    legal = str(b.get("legal_boundary") or "")
    if (not legal) or _has_cjk(legal) or "This report" in legal or "诊断报告" in legal:
        b["legal_boundary"] = get_ui_strings(loc).get(
            "boundary_legal",
            get_ui_strings("en").get("boundary_legal", legal),
        )
    return b


# Effort band is coarse chrome (low/medium/high), not free-form prose.
# Historical builders emit locale-flavoured display strings; language switch must
# re-localize via code — never treat English labels as language-neutral tokens.
EFFORT_BAND_CODES = ("low", "medium", "high")

_EFFORT_BAND_LABELS: dict[str, dict[str, str]] = {
    "zh-Hans": {
        "low": "低 · 模板/信息架构一次性改动",
        "medium": "中 · 内容 + 工程",
        "high": "高 · 长周期内容 / 社区",
    },
    "en": {
        "low": "Low · one-time template change",
        "medium": "Medium · content + engineering",
        "high": "High · long-cycle content / community",
    },
    "pt-PT": {
        "low": "Baixo · alteração pontual de template",
        "medium": "Médio · conteúdo + engenharia",
        "high": "Alto · conteúdo/comunidade de longo ciclo",
    },
    "pt-BR": {
        "low": "Baixo · alteração pontual de template",
        "medium": "Médio · conteúdo + engenharia",
        "high": "Alto · conteúdo/comunidade de longo ciclo",
    },
    "fr": {
        "low": "Faible · changement de template ponctuel",
        "medium": "Moyen · contenu + ingénierie",
        "high": "Élevé · contenu/communauté long cycle",
    },
    "ar": {
        "low": "منخفض · تعديل قالب لمرة واحدة",
        "medium": "متوسط · محتوى + هندسة",
        "high": "مرتفع · محتوى/مجتمع طويل الأمد",
    },
    "ja": {
        "low": "低 · テンプレートの一回限り改修",
        "medium": "中 · コンテンツ + エンジニアリング",
        "high": "高 · 長期コンテンツ / コミュニティ",
    },
}


def normalize_effort_band_code(value: Any) -> str:
    """Map display strings / codes → low|medium|high (default medium)."""
    raw = str(value or "").strip()
    if not raw:
        return "medium"
    low = raw.lower().strip()
    if low in EFFORT_BAND_CODES:
        return low
    # Leading Chinese band markers (builders: 低/中/高 · …).
    head = raw[:2]
    if raw.startswith("低") or "低" in head:
        return "low"
    if raw.startswith("高") or "高" in head:
        return "high"
    if raw.startswith("中") or "中" in head:
        return "medium"
    # English / Romance prefixes used by prior one-way EN map and LLM stubs.
    if low.startswith("low") or low.startswith("faible") or low.startswith("baixo") or "منخفض" in raw:
        return "low"
    if low.startswith("high") or low.startswith("élev") or low.startswith("elev") or low.startswith("alto") or "مرتفع" in raw:
        return "high"
    if (
        low.startswith("medium")
        or low.startswith("med ")
        or low.startswith("moyen")
        or low.startswith("médio")
        or low.startswith("medio")
        or "متوسط" in raw
    ):
        return "medium"
    # Phrase fingerprints from the historical EN collapse map.
    if any(tok in low for tok in ("one-time", "template change", "waf", "audit")):
        return "low"
    if any(tok in low for tok in ("long-cycle", "long cycle", "community")):
        return "high"
    if any(tok in low for tok in ("content + engineering", "content +", "engineering")):
        return "medium"
    return "medium"


def localize_effort_band(value: Any, locale: str | None = None) -> str:
    """Deterministic effort-band display for delivery language."""
    loc = normalize_locale(locale or "en")
    code = normalize_effort_band_code(value)
    family = loc if loc in _EFFORT_BAND_LABELS else (
        "zh-Hans" if is_cjk_locale(loc) else (
            "pt-PT" if loc.lower().startswith("pt") else (
                "fr" if loc.lower().startswith("fr") else (
                    "ar" if loc.lower().startswith("ar") else (
                        "ja" if loc.lower().startswith("ja") else "en"
                    )
                )
            )
        )
    )
    labels = _EFFORT_BAND_LABELS.get(family) or _EFFORT_BAND_LABELS["en"]
    return labels.get(code) or labels["medium"]


def localize_recommendations_effort(
    data_or_items: dict[str, Any] | list[Any],
    locale: str | None = None,
) -> dict[str, Any] | list[Any]:
    """Rewrite recommendation effort_band (+effort_code) for delivery language.

    Effort band is chrome with a closed vocabulary — same contract as channel
    metric headlines. Must run on every locale path (fresh, relocalize, render).
    """
    loc = normalize_locale(locale or "en")

    def _fix_items(items: list[Any]) -> list[Any]:
        out: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                out.append(item)
                continue
            row = dict(item)
            code = normalize_effort_band_code(row.get("effort_code") or row.get("effort_band"))
            row["effort_code"] = code
            row["effort_band"] = localize_effort_band(code, loc)
            out.append(row)
        return out

    if isinstance(data_or_items, list):
        return _fix_items(data_or_items)

    data = data_or_items
    if not isinstance(data, dict):
        return data
    out = data
    recs = out.get("recommendations")
    if isinstance(recs, list):
        out = dict(out)
        out["recommendations"] = _fix_items(recs)
    return out


def _translate_recommendations_en(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Chinese recommendation *slots* to English — never CJK-strip why/metric into soup."""
    out = []
    for item in items:
        row = dict(item)
        action = str(row.get("action") or "")
        mapping = {
            "官网机器可读性与页面结构补强": "Strengthen on-site machine readability and page structure",
            "官网可引用内容与信息架构建设": "Build citable on-site content and information architecture",
            "恢复官网可抓取并完成机器可读性审计": "Restore crawl access and audit on-site machine readability",
            "无品牌品类入口页建设（官网）": "Build unbranded category landing pages on the official site",
            "官网持续优化与实测缺口复测": "Keep optimizing the official site and re-test measured gaps",
            "官网结构化标记补全": "Complete on-site structured markup",
            "站点机器可读性补全": "Complete on-site machine-readable markup",
            "Wikipedia 条目完善 + 权威媒体品牌命名一致性": "Improve Wikipedia entry and consistent brand naming in media",
            "Wikipedia / 权威实体页建设": "Build Wikipedia / authoritative entity pages",
            "无品牌品类入口页建设": "Build unbranded category landing pages",
            "权威行业媒体与第三方评测定向引用建设": "Earn citations in industry media and third-party reviews",
            "YouTube 官方频道与用户评价内容建设": "Build YouTube and user-review citation footprint",
            "YouTube 官方频道内容与用户评价引用建设": "Build YouTube and user-review citation footprint",
            "外链多样性审计 + 社区讨论引用建设": "Backlink diversity audit and community citation building",
        }
        mapped = False
        for zh, en in mapping.items():
            if zh in action:
                row["action"] = en
                mapped = True
                break
        # Never ship CJK-strip remnants as action prose.
        if (not mapped) and (_has_cjk(str(row.get("action") or "")) or looks_like_cjk_strip_garbage(str(row.get("action") or ""))):
            row["action"] = "Recommended action"
        out.append(row)
    # Shared prose contract (defaults / garbage rejection / effort chrome).
    return sanitize_recommendation_prose(out, "en")  # type: ignore[return-value]


def format_channel_metric_headline(metric: dict[str, Any] | None, locale: str = "en") -> str:
    """Build SECTION 09 Off-site / channel headline from language-agnostic measured metric.

    Numbers come from collection (shared evidence). Locale only changes units/labels —
    never invent qualitative scores in place of measured counts.
    """
    if not isinstance(metric, dict):
        return ""
    loc = normalize_locale(locale)
    kind = str(metric.get("kind") or "").strip()
    family = "zh" if is_cjk_locale(loc) else (
        "pt" if loc.lower().startswith("pt") else (
            "fr" if loc.lower().startswith("fr") else (
                "ar" if loc.lower().startswith("ar") else (
                    "ja" if loc.lower().startswith("ja") else "en"
                )
            )
        )
    )

    static_maps = {
        "zh": {
            "pending_retest": "待复测",
            "not_tested": "未检测",
            "no_hits": "未发现检索结果",
            "no_entry": "无条目",
            "entry_found": "有条目",
            "missing": "缺失",
            "present": "可见",
            "empty": "空",
            "all_false": "全 false",
            "absent": "无",
            "partial_present": "部分可见",
            "too_short": "偏短",
            "unable": "无法判定",
        },
        "en": {
            "pending_retest": "Pending re-test",
            "not_tested": "Not tested",
            "no_hits": "No search hits",
            "no_entry": "No entry",
            "entry_found": "Entry found",
            "missing": "Missing",
            "present": "Present",
            "empty": "Empty",
            "all_false": "All false",
            "absent": "Absent",
            "partial_present": "Partially present",
            "too_short": "Too short",
            "unable": "Unable to determine",
        },
        "pt": {
            "pending_retest": "Reavaliação pendente",
            "not_tested": "Não testado",
            "no_hits": "Sem resultados de busca",
            "no_entry": "Sem entrada",
            "entry_found": "Entrada encontrada",
            "missing": "Ausente",
            "present": "Presente",
            "empty": "Vazio",
            "all_false": "Tudo false",
            "absent": "Ausente",
            "partial_present": "Parcialmente presente",
            "too_short": "Muito curto",
            "unable": "Não foi possível determinar",
        },
        "fr": {
            "pending_retest": "Nouveau test en attente",
            "not_tested": "Non testé",
            "no_hits": "Aucun résultat de recherche",
            "no_entry": "Aucune entrée",
            "entry_found": "Entrée trouvée",
            "missing": "Manquant",
            "present": "Présent",
            "empty": "Vide",
            "all_false": "Tout à false",
            "absent": "Absent",
            "partial_present": "Partiellement présent",
            "too_short": "Trop court",
            "unable": "Impossible à déterminer",
        },
        "ar": {
            "pending_retest": "بانتظار إعادة الاختبار",
            "not_tested": "غير مختبر",
            "no_hits": "لا نتائج بحث",
            "no_entry": "لا توجد صفحة",
            "entry_found": "تم العثور على صفحة",
            "missing": "مفقود",
            "present": "موجود",
            "empty": "فارغ",
            "all_false": "الكل false",
            "absent": "غير موجود",
            "partial_present": "موجود جزئياً",
            "too_short": "قصير جداً",
            "unable": "تعذر التحديد",
        },
        "ja": {
            "pending_retest": "次回再測定",
            "not_tested": "未検出",
            "no_hits": "検索結果なし",
            "no_entry": "エントリなし",
            "entry_found": "エントリあり",
            "missing": "欠落",
            "present": "あり",
            "empty": "空",
            "all_false": "すべて false",
            "absent": "なし",
            "partial_present": "一部あり",
            "too_short": "短すぎる",
            "unable": "判定不能",
        },
    }
    static = static_maps.get(family) or static_maps["en"]

    if kind == "static":
        key = str(metric.get("static_key") or "")
        fallback = {"zh": "待复核", "pt": "Revisar", "fr": "À revoir", "ar": "يحتاج مراجعة", "ja": "要確認"}.get(
            family, "Needs review"
        )
        return static.get(key, key or fallback)

    try:
        n = int(metric.get("value") or 0)
    except (TypeError, ValueError):
        n = 0

    if kind == "backlinks_count":
        return {
            "zh": f"{n} 条外链",
            "en": f"{n} backlinks",
            "pt": f"{n} backlinks",
            "fr": f"{n} backlinks",
            "ar": f"{n} روابط خلفية",
            "ja": f"バックリンク {n}件",
        }.get(family, f"{n} backlinks")

    if kind == "domain_rating":
        return {
            "zh": f"域名权威分 {n}",
            "en": f"Domain rating {n}",
            "pt": f"Domain rating {n}",
            "fr": f"Domain rating {n}",
            "ar": f"تقييم النطاق {n}",
            "ja": f"ドメイン評価 {n}",
        }.get(family, f"Domain rating {n}")

    if kind == "search_hits":
        plus = "+" if metric.get("plus", True) else ""
        official = bool(metric.get("official_channel"))
        unit = str(metric.get("unit") or "")
        if family == "zh":
            if unit == "youtube" or unit == "results_ge":
                base = f"{n}{plus} 个检索结果"
            else:
                base = f"{n}{plus} 条检索结果"
            if official:
                base += "（含疑似官方频道）"
            return base
        if family == "pt":
            base = f"{n}{plus} resultados de busca"
            if official:
                base += " (incl. canal oficial provável)"
            return base
        if family == "fr":
            base = f"{n}{plus} résultats de recherche"
            if official:
                base += " (canal officiel probable inclus)"
            return base
        if family == "ar":
            base = f"{n}{plus} نتيجة بحث"
            if official:
                base += " (يشمل قناة رسمية محتملة)"
            return base
        if family == "ja":
            base = f"検索結果 {n}{plus}件"
            if official:
                base += "（公式チャンネル含む可能性あり）"
            return base
        base = f"{n}{plus} search hits"
        if official:
            base += " (incl. likely official channel)"
        return base

    return ""


def infer_channel_card_metric(card: dict[str, Any]) -> dict[str, Any] | None:
    """Recover measured metric from card.metric or by parsing an existing headline."""
    raw = card.get("metric")
    if isinstance(raw, dict) and raw.get("kind"):
        return dict(raw)

    headline = str(card.get("headline") or "").strip()
    channel = str(card.get("channel") or "")
    if not headline:
        return None

    static_keys = {
        "待复测": "pending_retest",
        "Pending re-test": "pending_retest",
        "未检测": "not_tested",
        "Not tested": "not_tested",
        "未发现检索结果": "no_hits",
        "No search hits": "no_hits",
        "无条目": "no_entry",
        "No entry": "no_entry",
        "有条目": "entry_found",
        "Entry found": "entry_found",
        "缺失": "missing",
        "Missing": "missing",
        "可见": "present",
        "Present": "present",
        "空": "empty",
        "Empty": "empty",
        "全 false": "all_false",
        "All false": "all_false",
        "无": "absent",
        "Absent": "absent",
        "部分可见": "partial_present",
        "Partially present": "partial_present",
        "偏短": "too_short",
        "Too short": "too_short",
        "无法判定": "unable",
        "Unable to determine": "unable",
    }
    if headline in static_keys:
        return {"kind": "static", "static_key": static_keys[headline]}

    m = re.match(r"^(?:DR\s*)?(\d+(?:\.\d+)?)(\+)?\s*", headline, re.I)
    if not m:
        return None
    try:
        value = int(float(m.group(1)))
    except ValueError:
        return None
    plus = bool(m.group(2))
    lower = headline.lower()
    if "外链" in headline or "backlink" in lower:
        return {"kind": "backlinks_count", "value": value}
    if "域名权威" in headline or "domain rating" in lower or headline.upper().startswith("DR"):
        return {"kind": "domain_rating", "value": value}
    if "检索" in headline or "search hit" in lower or "YouTube" in channel or "Reddit" in channel:
        unit = "youtube" if ("YouTube" in channel or "个检索" in headline) else "reddit"
        return {
            "kind": "search_hits",
            "value": value,
            "plus": plus or True,
            "official_channel": ("官方" in headline) or ("official channel" in lower),
            "unit": unit,
        }
    return None


def resolve_channel_card_headline(card: dict[str, Any], locale: str) -> str:
    """Prefer metric→format; fall back to localizing an existing measured headline string."""
    metric = infer_channel_card_metric(card)
    if metric:
        formatted = format_channel_metric_headline(metric, locale)
        if formatted:
            return formatted
    return localize_measured_channel_headline(
        str(card.get("headline") or ""),
        channel=str(card.get("channel") or ""),
        locale=locale,
    )


def localize_measured_channel_headline(
    headline: str,
    *,
    channel: str = "",
    locale: str = "en",
) -> str:
    """Localize SECTION 09 card headlines while preserving measured numbers.

    Prefer :func:`resolve_channel_card_headline` / ``card.metric`` when available.
    Examples (zh → en):
      - ``37 条外链`` → ``37 backlinks``
      - ``68+ 个检索结果（含疑似官方频道）`` → ``68+ search hits (incl. likely official channel)``
      - ``63+ 条检索结果`` → ``63+ search hits``
      - ``无条目`` → ``No entry``
    """
    text = str(headline or "").strip()
    if not text:
        return text
    loc = normalize_locale(locale)
    if is_cjk_locale(loc) or not _has_cjk(text):
        return text

    static = {
        "待复测": "Pending re-test",
        "未检测": "Not tested",
        "缺失": "Missing",
        "可见": "Present",
        "无条目": "No entry",
        "有条目": "Entry found",
        "空": "Empty",
        "全 false": "All false",
        "无": "Absent",
        "部分可见": "Partially present",
        "偏短": "Too short",
        "未发现检索结果": "No search hits",
        "无法判定": "Unable to determine",
    }
    if text in static:
        return static[text]

    ch = str(channel or "")
    # Keep leading measured token: 37 / 68+ / 12.5 / DR 8
    m = re.match(r"^((?:DR\s*)?\d+(?:\.\d+)?\+?)\s*", text, re.I)
    prefix = m.group(1) if m else ""

    if "外链" in text or ("backlink" in text.lower() and _has_cjk(text)):
        return f"{prefix} backlinks".strip() if prefix else "Backlinks"
    if "检索结果" in text or "搜索结果" in text:
        suffix = " (incl. likely official channel)" if ("官方" in text or "频道" in text) else ""
        return f"{prefix} search hits{suffix}".strip() if prefix else f"Search hits{suffix}".strip()
    if "域名权威" in text or (prefix.upper().startswith("DR") and "权威" in text):
        return f"Domain rating {prefix.replace('DR', '').strip()}".strip() if prefix else "Domain rating"
    if "YouTube" in ch and ("视频" in text or "检索" in text):
        suffix = " (incl. likely official channel)" if ("官方" in text or "频道" in text) else ""
        return f"{prefix} search hits{suffix}".strip() if prefix else f"Search hits{suffix}".strip()
    if "Reddit" in ch and ("检索" in text or "讨论" in text or "条" in text):
        return f"{prefix} search hits".strip() if prefix else "Search hits"

    # Fallback: keep digits/units, drop remaining CJK.
    return _strip_cjk_keep_latin(text, fallback="Needs review")


def localize_channel_card_name(channel: str, locale: str = "en") -> str:
    """Normalize SECTION 09 channel titles for delivery language."""
    ch = str(channel or "").strip()
    if not ch:
        return ch
    loc = normalize_locale(locale)
    if is_cjk_locale(loc):
        # Prefer Chinese titles when source already has them; otherwise keep.
        return ch
    family = (
        "pt" if loc.lower().startswith("pt") else (
            "fr" if loc.lower().startswith("fr") else (
                "ar" if loc.lower().startswith("ar") else (
                    "ja" if loc.lower().startswith("ja") else "en"
                )
            )
        )
    )
    names = {
        "en": {
            "schema": "Schema / JSON-LD",
            "semantic": "Semantic HTML",
            "meta": "Meta Description",
            "youtube": "YouTube · video sources",
            "reddit": "Reddit · community sources",
            "wikipedia": "Wikipedia · Encyclopedia",
            "backlinks": "Backlinks summary",
            "llms": "llms.txt",
        },
        "pt": {
            "schema": "Schema / JSON-LD",
            "semantic": "HTML semântico",
            "meta": "Meta Description",
            "youtube": "YouTube · fontes de vídeo",
            "reddit": "Reddit · fontes da comunidade",
            "wikipedia": "Wikipedia · Enciclopédia",
            "backlinks": "Resumo de backlinks",
            "llms": "llms.txt",
        },
        "fr": {
            "schema": "Schema / JSON-LD",
            "semantic": "HTML sémantique",
            "meta": "Meta Description",
            "youtube": "YouTube · sources vidéo",
            "reddit": "Reddit · sources communautaires",
            "wikipedia": "Wikipedia · Encyclopédie",
            "backlinks": "Résumé des backlinks",
            "llms": "llms.txt",
        },
        "ar": {
            "schema": "Schema / JSON-LD",
            "semantic": "HTML دلالي",
            "meta": "Meta Description",
            "youtube": "YouTube · مصادر فيديو",
            "reddit": "Reddit · مصادر مجتمعية",
            "wikipedia": "Wikipedia · موسوعة",
            "backlinks": "ملخص الروابط الخلفية",
            "llms": "llms.txt",
        },
        "ja": {
            "schema": "Schema / JSON-LD",
            "semantic": "セマンティックHTML",
            "meta": "Meta Description",
            "youtube": "YouTube · 動画ソース",
            "reddit": "Reddit · コミュニティソース",
            "wikipedia": "Wikipedia · 百科事典",
            "backlinks": "バックリンク概要",
            "llms": "llms.txt",
        },
    }
    table = names.get(family) or names["en"]
    if "Schema" in ch or "结构化" in ch or "JSON-LD" in ch:
        return table["schema"]
    if "语义" in ch or "Semantic" in ch or "semânt" in ch.lower() or "sémant" in ch.lower():
        return table["semantic"]
    if "Meta" in ch:
        return table["meta"]
    if "YouTube" in ch:
        return table["youtube"]
    if "Reddit" in ch:
        return table["reddit"]
    if "Wikipedia" in ch or "百科" in ch or "Enciclop" in ch or "Encyclop" in ch or "موسوعة" in ch:
        return table["wikipedia"]
    if "外链" in ch or "Backlink" in ch or "backlink" in ch.lower():
        return table["backlinks"]
    if "llms" in ch.lower():
        return table["llms"]
    if _has_cjk(ch) and family != "zh":
        return _strip_cjk_keep_latin(ch, fallback=table.get("backlinks", "Channel"))
    return ch


def _translate_channel_cards_en(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for card in cards:
        row = dict(card)
        row["channel"] = localize_channel_card_name(str(row.get("channel") or ""), "en")
        metric = infer_channel_card_metric(row)
        if metric:
            row["metric"] = metric
            row["headline"] = format_channel_metric_headline(metric, "en")
        else:
            headline = str(row.get("headline") or "")
            if _has_cjk(headline) or headline in {
                "待复测", "未检测", "缺失", "可见", "无条目", "有条目", "空", "全 false", "无", "部分可见", "偏短", "未发现检索结果", "无法判定",
            }:
                row["headline"] = localize_measured_channel_headline(
                    headline, channel=str(row.get("channel") or ""), locale="en"
                )
        # Description feeds `{desc}` into EN chrome templates — never leave Chinese
        # or CJK-strip punctuation soup.
        desc = str(row.get("description") or "")
        if _has_cjk(desc) or looks_like_cjk_strip_garbage(desc):
            row["description"] = ""
        status = str(row.get("status") or "")
        if _has_cjk(status):
            status_map = {
                "已检测": "detected",
                "部分覆盖": "partial",
                "严重缺口": "critical_gap",
                "代理证据": "proxy",
            }
            row["status"] = status_map.get(status, "measured")
        out.append(row)
    return out


def load_dashboard_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_dashboard_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# Static UI catalog (renderer keys)
try:
    from magup_geo_report.magup_report.locale_catalogs.ja_ui_strings import JA_UI_STRINGS
except ImportError:
    from .locale_catalogs.ja_ui_strings import JA_UI_STRINGS

_UI_STRINGS: dict[str, dict[str, str]] = {
    "zh-Hans": {
        "report_title_suffix": "AI 模型表现诊断报告",
        "report_sub": "基于 {platform_phrase} 的 {total_samples} 条回答样本，结合官网结构化信号、搜索流量画像与竞品基准，评估 {brand_name} 在生成式搜索与答案引擎中的提及、引用与推荐占位表现。",
        "report_audience": "本报告供品牌增长、市场与业务负责人快速决策。",
        "meta_subject": "诊断对象",
        "meta_business": "业务定义",
        "meta_platforms": "采样平台",
        "meta_date": "报告日期",
        "meta_report_code": "报告编号",
        "section_01_no": "SECTION 02 · 核心数据",
        "section_01_title": "四项核心指标：当前态势总览",
        "kpi_unbranded": "无品牌自然展现",
        "kpi_unbranded_note": "买家用不带品牌提问时，AI 推荐列表里出现{brand_name}的次数。",
        "kpi_branded": "品牌词被识别",
        "kpi_branded_note": "用户报上品牌后，多数回答能识别品牌，说明底层资产可用，但需要被前置。",
        "kpi_competitor": "竞品占位回答数",
        "kpi_competitor_note": "目标缺席且至少出现一个竞品的回答数；每条回答最多计 1 次（缺席场景接管率 {rate}%）。",
        "kpi_dr": "域名权威分",
        "kpi_dr_note": "竞品得分 {comp_min}–{comp_max}。得分越高，AI 越倾向将其列为推荐来源。",
        "status_pending": "待复测",
        "status_tested": "已实测",
        "status_detected": "已检测",
        "status_partial": "部分覆盖",
        "status_critical_gap": "严重缺口",
        "status_not_deployed": "未部署",
        "insight_label": "诊断结论",
        "platform_brand_visibility": "品牌可见度",
        "platform_unbranded_visibility": "无品牌可见度",
        "platform_official_cite": "官网引用率",
        "platform_competitor_mentions": "竞品出现次数",
        "platform_samples_mentioned": "样本提及",
        "platform_unbranded_samples": "无品牌样本",
        "platform_cited_official": "引用官网",
        "platform_low_competitor": "低竞品占位",
        "platform_footer": "本平台口径来自本轮 AI 回答样本；无品牌可见度为获客前链路核心指标。",
        "platform_pending": "下一轮复测",
        "platform_pending_sub": "待测",
        "platform_untested_note": "说明：{name} 本轮未独立测试，保留为下一轮复测对象；不可将待测项解释为 0 表现。",
        "platform_competitive_strength": "竞品未占位率 {pct}",
        "meta_per_platform_prompts": "每个平台 {count} 问",
        "meta_per_platform_prompts_partial": "计划每平台 {planned} 问（实际采样未完全对齐）",
        "compare_unbranded": "无品牌可见",
        "compare_branded": "品牌可见",
        "compare_competitor_inverse": "竞品未占位率",
        "compare_pending": "待测，下一轮补测",
        "cover_platforms_and_more": "{joined} 等 {count} 个平台",
        "cover_platforms_count_only": "{count} 个主流 AI 平台",
        "funnel_seg_complete": "完整可见",
        "funnel_seg_partial": "部分可见",
        "funnel_seg_brand_absent": "品牌缺席",
        "funnel_seg_mine": "我方出现",
        "funnel_seg_comp": "竞品占位",
        "funnel_seg_all_blank": "全部缺席",
        "vs_label": "vs",
        "status_proxy": "代理证据",
        "status_mixed": "混合证据",
        "status_not_tested": "本轮未测",
        "status_not_independent": "未独立测试",
        "status_unavailable": "不可用",
        "status_failed": "采集失败",
        "status_blocked": "抓取被拦截",
        # Section 02 content keys (rendered as SECTION 01 — order: TOP distribution → core metrics)
        "section_02_no": "SECTION 01 · TOP 排名分布",
        "section_02_title": "{brand_name} 在 {total_samples} 条 AI 回答样本中的位置分布",
        "section_02_desc": "按品牌是否出现、是否引用官网、是否被竞品接管对样本分类后可见：主要缺口不在品牌认知准确度，而在前链路（无品牌场景）能否进入推荐列表。",
        "section_02_card_title": "样本分布全景",
        "section_02_card_note": "分两类场景对照：品牌词提问（共 {branded_total} 条）与不带品牌提问（共 {unbranded_total} 条）并排；每行按该场景 100% 归一化，悬停查看占比。",
        "legend_visible": "我方可见",
        "legend_improve": "需改进 / 被竞品占位",
        "legend_absent": "完全缺席",
        "scenario_card_title": "分场景明细",
        "scenario_card_note": "两组统计口径不同：品牌词提问组是同一批属性（可重叠、不可相加）；不带品牌提问组是互斥分解（三项相加 = {unbranded_total}）。",
        "scenario_group_branded": "品牌词提问 · {total} 条",
        "scenario_group_unbranded": "不带品牌提问 · {total} 条",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · 获客前链路",
        "scenario_visibility_mix": "可见度分层",
        "scenario_children_note": "品牌词提问中的可见度与官网引用",
        "scenario_unbranded_gap_note": "竞品占位 {comp_pct}% + 完全缺席 {blank_pct}% = {absent_pct}% 未进入推荐。这是获客前链路的主缺口。",
        "scenario_recognized": "被识别",
        "scenario_not_recognized": "未被识别",
        "scenario_cited": "官网被引用",
        "scenario_not_cited": "官网未被引用",
        "scenario_mine": "我方出现",
        "scenario_comp_takeover": "缺席 · 竞品接管",
        "scenario_all_blank": "缺席 · 全部空白",
        "scenario_read_note": "读法：不带品牌提问是获客前链路，缺席（竞品接管 {comp} + 全部空白 {blank} = {absent}）时，竞品会先被 AI 推荐给潜在客户；品牌词提问里官网被引用 {cited}/{branded_total} 偏低，说明 AI 认得品牌、却很少回链官网。",
        # Section 03
        "section_03_no": "SECTION 03 · 舆情分析",
        "section_03_title": "AI 回答中对{brand_name}的情绪倾向",
        "section_03_desc": "对每条 AI 回答做情绪分类（正面 / 中性 / 负面），统计{brand_name}被谈及时的口碑倾向。负面占比越低越安全；中性占比高代表「被提及但未被推荐」。",
        "senti_overall_title": "整体情绪占比",
        "senti_overall_note": "基于对全部 {total} 条回答逐条情绪分类后的占比。",
        "senti_platform_title": "各平台情绪分布",
        "senti_platform_note": "同口径拆到每个已测平台，看不同 AI 对品牌的情绪是否一致。",
        "senti_positive": "正面",
        "senti_neutral": "中性",
        "senti_negative": "负面",
        "senti_stat_line": "{label} · {count} 条",
        "senti_plat_counts": "正 {pos} · 中 {neu} · 负 {neg}",
        "senti_insight_with_data": "在 {total} 条 AI 回答中，正面情绪 {pos} 条（{pos_pct}），负面仅 {neg} 条（{neg_pct}）——说明 AI 谈到{brand_name}时几乎没有口碑风险。真正的机会在于 {neu_pct} 的中性占比：这部分回答只是「提到」品牌却没有给出推荐倾向，把中性转化为正面背书，是把 AI 可见度变成 AI 推荐的关键一跳。",
        "senti_insight_no_data": "本轮未取得可分类的情绪样本。",
        "senti_cloud_title": "舆情词云",
        "senti_cloud_badge": "LLM 短语抽取",
        "senti_cloud_note": "从提及{brand_name}的正/中/负回答中抽取评价短语；字号越大表示在越多回答中出现。",
        "senti_cloud_tab_positive": "正面关键词",
        "senti_cloud_tab_neutral": "中性关键词",
        "senti_cloud_tab_negative": "负面关键词",
        "senti_cloud_tooltip_count": "出现 {count} 次",
        "senti_cloud_empty_generic": "当前极性暂无可用关键词。",
        "senti_cloud_empty_missing": "本轮尚未生成舆情词云产物（可复跑 AEO 关键词抽取步骤）。",
        "senti_cloud_empty_no_answers": "提及样本不足，暂无法抽取关键词。",
        "senti_cloud_empty_no_phrases": "已有情绪样本，但未能抽出可展示的具体短语。",
        # Section 04
        "section_04_no": "SECTION 04 · 平台表现",
        "section_04_title": "主流 AI 模型上的可见性差异",
        "section_04_desc": "已测平台使用同一组提示词；未测平台保留待复测标记，不转换为 0 表现。",
        "plat_compare_title": "平台可见性对比",
        "plat_compare_note": "三项可见性指标（0–100%，越高越好）逐平台对比；官网引用率见上方平台卡片，作为诊断信号不在此处评分。",
        "plat_matrix_title": "平台推荐阻力矩阵",
        "plat_matrix_note": "横轴 = 无品牌可见度（越右越好）；纵轴 = 竞品占位率（越低越好）；圆越大 = 该平台样本量越多。右下蓝色区为理想区（可见且少竞品），左上为高危区。",
        # Section 05
        "section_05_no": "SECTION 05 · 信源权威性",
        "section_05_title": "AI 可调用的信源类型与覆盖范围",
        "section_05_desc": "浅蓝 = 跨类目基准，紫色 = 当前状态；代理估算已显式标注。",
        "auth_radar_title": "品牌可信度雷达",
        "auth_radar_note": "五个维度均衡量「该渠道里关于品牌的权威内容足迹」：官方信源 = 官网域名权威分与 AI 引用率加权（6:4，实测）；百科 / 媒体 / 社区 / 专业度为方向性估算。",
        "auth_dim_title": "各维度解读",
        "auth_dim_note": "评分反映 AI 在各渠道能找到多少可信内容，0–100 相对值",
        "auth_focus_note": "重点关注：百科、媒体、社区三个维度——这是 AI 判断「这个品牌是否被外部认可」的主要依据。",
        "legend_radar_industry": "跨类目基准",
        "legend_radar_current": "{brand_name}当前",
        # Section 06
        "section_06_no": "SECTION 06 · 渠道存在感",
        "section_06_title": "AI 在哪些渠道能找到关于我们的内容",
        "section_06_desc": "与上方雷达同口径（0-100）：官网 / 百科 / 媒体直接对应雷达对应轴，YouTube 与 Reddit 是雷达「社区」轴拆开看（社区 = 两者均值）。分数越高越好。",
        "src_bar_title": "各渠道得分对比",
        "src_bar_note": "紫色柱 = {brand_name}当前得分；灰色柱 = 同类品牌参考水平（方向性）。",
        "legend_peer_ref": "同类参考",
        # Section 07
        "section_07_no": "SECTION 07 · 竞品差距",
        "section_07_title": "平台推荐阻力与竞品占位压力",
        "section_07_desc": "横轴 = 无品牌查询下的 AI 可见度（%，实测）；纵轴 = AI 回答里把该品牌作为信源引用的占比（%）。空心点 = 竞品引用占比无实测数据、按域名权威分代理估算。",
        "comp_bubble_title": "竞品在 AI 回答中的可见性对比",
        "comp_bubble_note": "横轴 = 无品牌问题中 AI 提及该品牌的频率（实测）；纵轴 = AI 引用该品牌作为信源的占比。空心点为代理估算。",
        "dr_bar_title": "域名权威分对比",
        "dr_bar_note": "域名权威分反映有多少外部网站引用过这个域名，分数越高 AI 越倾向将其视为可信来源。满分 100。",
        "search_dr_row": "域名权威分 {dr} · Organic {organic} · Keywords {keywords}",
        # Section 08
        "section_08_no": "SECTION 08 · 竞品排名",
        "section_08_title": "同赛道里，AI 最常提到谁",
        "section_08_desc": "把{brand_name}与所有竞品放进同一张排行榜：统计每个品牌在 {denom} 条不带品牌提问的 AI 回答中被提及的真实次数。排名越靠前，越能在用户尚未决定品牌时抢占 AI 推荐位。",
        "rank_card_title": "无品牌提问提及排行",
        "rank_card_note": "紫色高亮为{brand_name}；长条 = 被 AI 提及的相对频次；右侧为绝对次数与占不带品牌提问比例。",
        "rank_card_badge": "{denom} 条不带品牌提问",
        "rank_you_tag": "本品牌",
        "rank_focus_tag": "关注",
        "rank_count_line": "{mentions} 次 · {rate}",
        "rank_phrase": "第 {rank}",
        "rank_not_listed": "未上榜",
        "rank_headline_ranked": "在同赛道 {total_brands} 个品牌中，{brand_name}在不带品牌提问下的提及频次排名 <b>{rank_phrase}</b>。",
        "rank_headline_unranked": "在同赛道 {total_brands} 个品牌中，{brand_name}在不带品牌提问下尚未进入提及排名。",
        "focus_comp_kicker": "Focus competitors",
        "focus_comp_title": "本报告关注竞品",
        "focus_comp_note": "来自报告配置的关注名单（比自动发现更精确）。下方展示本轮无品牌场景中的实测提及；未出现不代表不是竞品，只说明本轮样本未点名。",
        "focus_comp_mentions": "无品牌提及 {count} 次",
        "focus_comp_rank": "排名 #{rank}",
        "focus_comp_absent": "本轮未点名",
        # Section 09
        "section_09_no": "SECTION 09 · 渠道逐项诊断",
        "section_09_title": "渠道缺口与优先修复项",
        "section_09_desc": "先看官网可读性，再看外链/社媒足迹。蓝标 = 已实测且正常；黄标 = 有数据但需改进；红标 = 明确缺口；灰标 = 本轮未单独测试。",
        "channel_group_official_kicker": "01 · 站内",
        "channel_group_official_title": "官网",
        "channel_group_official_note": "站点是否被机器读懂：结构化标记、语义边界、标题层级、一句话定义、抓取声明，以及正文/内页可引用密度。",
        "channel_group_offsite_kicker": "02 · 站外",
        "channel_group_offsite_title": "外链 / 社媒",
        "channel_group_offsite_note": "站外被看见的足迹：外链聚合、视频/社区检索量、百科条目。社媒计数来自关键字检索，未必等于真实品牌相关内容。",
        # Section 10
        "section_10_no": "SECTION 10 · 问题归因",
        "section_10_title": "{brand_name} 未被主动推荐的归因",
        # Section 11
        "section_11_no": "SECTION 11 · 改进建议",
        "section_11_title": "改进路径与执行优先级",
        "section_11_desc": "官网建设永远是第一优先级：先补机器可读结构与可引用内容，再扩外链/社媒。按改动难度和预期效果排序，供团队排期。",
        "recs_col_priority": "优先级",
        "recs_col_action": "动作",
        "recs_col_why": "选择依据",
        "recs_col_metric": "预期变化指标",
        "recs_col_effort": "修复成本档",
        "recs_site_markup_hint": "JSON-LD Schema · semantic HTML · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "品类专题页 · 对比/选购文 · 清晰 H2 分区 · 可引用事实段落",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        # Section 12
        "section_12_no": "SECTION 12 · 引用信源排行",
        "section_12_title": "AI 回答实际引用了哪些网站与文章",
        "section_12_desc": "只统计回答中的引用信源（不含检索列表）。按域名出现次数排序，展示前 30 个；官网未进入前 30 时在末尾单独列出。展开后查看具体文章及次数。",
        "cite_rank_tab_branded": "品牌词提问",
        "cite_rank_tab_unbranded": "不带品牌提问",
        "cite_rank_tab_meta": "{answers} 条回答 · {citations} 次引用",
        "cite_rank_empty": "本档提问的回答中未采集到引用信源",
        "cite_rank_count": "{count} 次",
        "cite_rank_official": "官网",
        "cite_rank_urls_n": "{count} 篇文章",
        "cite_rank_truncated": "仅展示前 {n} 个域名（共 {total} 个）",
        "cite_rank_unlisted": "未上榜",
        "section_13_no": "SECTION 12 · 提示词与回答原文",
        "section_13_title": "提示词与原始回答明细",
        "qa_group_branded": "品牌提示词",
        "qa_group_unbranded": "无品牌提示词",
        "qa_group_default": "提问",
        "qa_dot_mentioned": "已提及",
        "qa_dot_not_mentioned": "未提及",
        "qa_badge_mentioned": "已提及品牌",
        "qa_badge_not_mentioned": "未提及",
        "qa_badge_cite_official": "引用官网",
        "qa_badge_cite_missing": "未引用官网",
        "qa_badge_partial_visible": "部分可见",
        "qa_badge_fully_visible": "完整可见",
        "qa_dots_legend": "圆点 = 各平台是否提及品牌（蓝=已提及，灰=未提及）",
        "qa_comp_mentioned": "同答提及竞品：{names}",
        "qa_queried_as": "实际问法：{text}",
        "qa_no_excerpt": "（该平台回答原文未写入报告，多为采集失败或早期报告缺回答字段）",
        "qa_evidence": "分类依据：",
        "qa_evidence_corrected": "回答正文未出现品牌名，已纠正为未提及",
        "qa_evidence_corrected_original": "回答正文未出现品牌名，已纠正为未提及。原依据：{evidence}",
        "qa_sources": "信源",
        "qa_source_cited": "正文出现",
        "qa_source_listed": "列表信源",
        "qa_no_sources": "本条未采集到信源列表",
        "qa_expand_answer": "展开回答全文",
        "qa_collapse_answer": "收起回答",
        "qa_open_modal": "查看详情",
        "qa_modal_close": "关闭",
        "qa_modal_question": "提示词",
        "qa_modal_actual_prompt": "该平台实际问法",
        "qa_modal_status": "状态标签",
        "qa_modal_ranking": "回答内品牌 / 竞品出现顺序",
        "qa_modal_competitors": "回答提及竞品",
        "qa_no_platform": "该提示词暂无平台回答",
        "qa_no_competitors": "本条未识别到竞品提及",
        "qa_no_rank": "暂无可用排名信息",
        "qa_rank_absent": "缺席",
        "qa_section_note": "点击任意提示词，在弹窗中按平台切换查看完整回答（Markdown 渲染）、信源、分类依据与提及顺序。",
        # Boundary
        "boundary_title": "数据说明",
        "boundary_tested": "本轮已测试：",
        "boundary_not_tested": "本轮未单独测试",
        "boundary_not_tested_note": "（不代表零分，下轮可补测）",
        "boundary_proxy": "参考估算值",
        "boundary_proxy_note": "（非精确测量，供方向性参考）",
        "boundary_scope": "以上数据和结论基于本轮测试的问题范围，不代表所有可能的搜索场景。",
        "boundary_legal": "本材料仅用于现状判断与下一轮复测口径定义，不构成实施承诺、报价或合同条款。",
        # Misc
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "目标品牌",
        "rivals_fallback": "竞品",
        "industry_mean": "同赛道行业均值(方向性)",
        "chart_tooltip_seg": "{label}: {pct}%（{count}/{total}）",
        "chart_tooltip_plat_bubble": "{name}: unbranded visibility {x}%, competitor share {y}%, n={n}",
        "chart_tooltip_comp_scatter": "{name}: visibility {x}%, source share {y}%{tag}",
        "chart_tooltip_comp_proxy": " (est.)",
        # Narrative fallbacks (when narrative_copy missing)
        "fallback_section_01_desc": "在品牌点名问题中，AI 对{brand_name}的识别为 {branded_mentioned}/{branded_total}（{branded_rate}%）；在用户尚未决定品牌的问题中，{brand_name}出现在 {unbranded_mentioned}/{unbranded_total} 的场景里，另有 {takeover} 次由竞品占据推荐位置。",
        "fallback_main_insight": "本轮数据显示，{brand_name}在品牌点名问题中的识别率为 <b>{branded_rate}%</b>，但在无品牌决策场景中缺席 {unbranded_absent}/{unbranded_total} 次，其中 {takeover} 次由 {rivals} 占据推荐位置。应优先补足影响无品牌发现与推荐的证据供给，并在下一轮使用相同问题集复测。",
        "fallback_section_05_insight": "为什么竞品在这张图上的外部信源得分更高：不只是品牌体量——而是因为竞品在 YouTube、Reddit 和行业媒体上积累了大量真实用户生成的可引用内容，这正是 AI 判断品牌可信度时优先参考的信号类型。{brand_name}的官方内容质量没有问题，但在这些外部渠道的可被引用密度偏低，导致 AI 在无品牌推荐时更倾向于选择有更多第三方背书的对手。灰色柱表示本轮未单独测试，不等于零分；但官网结构补全（Schema、Meta、llms.txt）是成本最低的起点，再逐步在外部渠道建立被引用记录，才能从根本上扭转这个差距。",
        "fallback_section_06_dr_note": "{brand_name}域名权威分 {dr}，竞品在 {comp_min}–{comp_max} 之间，差距本身有限。但域名权威分衡量的是外链总量，不反映内容相关性——竞品在行业媒体、用户社区中的专题引用密度更高，这类定向引用对 AI 推荐权重的影响比泛域名权威分直接得多。盲目追域名权威分总分不是出路；{brand_name}需要的是在品类语义节点上被权威来源点名引用，这才是 AI 愿意主动推荐的信号。",
        "fallback_section_07_insight": "{brand_name}有成熟的品牌资产——完整官网、广泛品牌认知——但这些资产大多是为搜索引擎和人类读者设计的，对 AI 的推荐逻辑几乎没有直接输入。竞品的官网结构化程度更高、外部媒体和社区引用更密集，AI 在无品牌推荐时自然优先选择那里。{brand_name}不需要重建——需要的是把现有资产重新编码成 AI 可调用的格式。这个工作的改动成本低，但每推迟一天，竞品在 AI 语料里的先发优势就再积累一天。灰色标记渠道本轮未单独测试，不代表出了问题，下一轮可以单独验证。",
        "fallback_section_08_desc": "三个层次的缺口叠加，导致{brand_name}在 AI 推荐链路中系统性失位：AI 无法干净地识别品牌产品边界 → AI 在无品牌内容里找不到可引用的{brand_name}页面 → AI 给出推荐时优先选择信号更完整的竞品。三个层次互相放大，不是简单的加法关系。",
        "fallback_section_09_insight": "官网是 AI 认识{brand_name}的第一可信源，每个品牌都应持续优化——不是一次性改完就停。P0 先做两件事：①机器可读结构（Schema、语义标签、H1/H2、Meta、llms.txt）；②可引用内容与品类入口页（对比/选购/场景说明）。这些改动直接决定 AI 能否稳定识别并引用官网。外链与社媒是放大站内建设的下一层，不应先于官网开工。每个项目都要绑定可复测的 AI 指标——不能只交付内容，必须验证回答是否真的改变了。",
        "fallback_root_expression": "{brand}官网往往内容完整，但结构与文章仍按人类阅读设计：缺清晰实体标记、标题层级或可引用专题段落时，AI 只能从散落正文拼接【提供什么、适合谁】——效率低于结构完善的竞品页，直接体现在无品牌推荐被跳过的频率上。<br/><br/>证据：{evidence}。",
        "fallback_root_supply": "{brand}缺少专门回答用户尚未选定品牌时提问的那类内容——缺少回答品类对比、产品选择、竞品差异类问题的可引用页面。这些页面是 AI 做无品牌推荐时的直接引用来源；竞品在这些语义节点上的内容覆盖比{brand}密集得多，AI 的推荐自然更多流向那里。<br/><br/>证据：{evidence}。",
        "fallback_root_distribution": "这是获客的第一道门：用户还没选定品牌，正在用 AI 寻求推荐。在本轮无品牌场景里，{brand}有超过一半时间没有出现在 AI 的答案里，其中多次被竞品直接占走推荐位。AI 作为产品发现渠道的用户渗透率仍在快速增长；这个入口每缺席一次，都是一次真实的潜在客户被引向对手的记录。<br/><br/>证据：{evidence}。",
        # Channel description expansions
        "ch_desc_backlinks": "{desc} 外部网站的引用数量和质量，是 AI 判断一个品牌是否值得推荐的重要参考之一。建议下一轮重点看引用来源是否包含媒体、评测站和行业目录。",
        "ch_desc_youtube_tested": "{desc} AI 在回答产品类问题时会参考视频内容（评测、教程、开箱）来描述品牌特点；可见的品牌视频越多，AI 的描述越具体。",
        "ch_desc_youtube_untested": "本轮未单独测试 YouTube 的影响。AI 在回答产品类问题时，会参考视频内容（尤其是评测、使用教程、开箱）来描述品牌特点。搜索结果中的品牌视频越多，AI 对品牌的描述越具体；反之则不会主动提及。建议下一轮单独验证。",
        "ch_desc_reddit_tested": "{desc} AI 判断用户反馈时会参考 Reddit、论坛等社区讨论——既看好评也看差评；这类内容决定 AI 是否在推荐时加注意事项，或转向竞品替代。",
        "ch_desc_reddit_untested": "本轮未单独测试社区口碑的影响。AI 在判断一个品牌的用户反馈时，Reddit、论坛等社区讨论是重要参考——不只看好评，也看差评和真实使用问题。这类内容决定 AI 是否会在推荐时加注意事项，或直接推荐竞品替代。",
        "ch_desc_wikipedia": "{desc} Wikipedia 是 AI 判断一个品牌基本信息的常用来源之一。没有词条不代表 AI 完全不认识这个品牌，但在品牌名字模糊或存在同名产品时，缺少独立词条会增加 AI 描述出错的概率。",
        "ch_desc_schema": "{desc} Schema 标记是让网页机器可读的标准方式——相当于给官网加一层专门给 AI 看的说明，写清楚品牌名称、产品分类、适用人群。缺失时，AI 只能从正文文字里猜，容易出错或描述模糊。改动成本低，优先补齐。",
        "ch_desc_semantic": "{desc} 如果页面没有清晰的标题层级和内容分区，AI 在理解这个页面内容时会比较困难，容易混用竞品页面的描述来填补。这属于站内可以直接优化的部分。",
        "ch_desc_meta": "{desc} Meta description 通常是 AI 生成品牌简介时最直接借用的来源。如果留空，AI 会自己从正文拼一段，结果往往不够准确或不够有利。写一句清晰的品牌定位描述，改动成本极低。",
        "ch_desc_llms": "{desc} llms.txt 是一个新兴的约定格式，让品牌可以主动告诉 AI 爬虫哪些页面最重要、品牌是谁、核心产品是什么。目前不是强制标准，但可以和 Schema、Meta 一起，作为三件套快速改善官网的机器可读性。",
    },
    "en": {
        "report_title_suffix": "AI Model Performance Diagnostic Report",
        "report_sub": "Based on {total_samples} answer samples across {platform_phrase}, combined with official-site structural signals, search-traffic profiles, and competitor benchmarks, this report evaluates {brand_name}'s mention, citation, and recommendation presence in generative search and answer engines.",
        "report_audience": "For brand, marketing, and business decision makers.",
        "meta_subject": "Subject",
        "meta_business": "Business scope",
        "meta_platforms": "Sampled platforms",
        "meta_date": "Report date",
        "meta_report_code": "Report code",
        "section_01_no": "SECTION 02 · CORE METRICS",
        "section_01_title": "Four numbers that frame the situation",
        "kpi_unbranded": "Unbranded presence",
        "kpi_unbranded_note": "Times {brand_name} appeared when buyers ask without naming a brand.",
        "kpi_branded": "Branded recognition",
        "kpi_branded_note": "When users name the brand, most answers recognize it — underlying assets exist but must be surfaced earlier.",
        "kpi_competitor": "Answers occupied by competitors",
        "kpi_competitor_note": "Answers where {brand_name} is absent and at least one competitor appears; each answer counts once ({rate}% of absent scenarios).",
        "kpi_dr": "Domain authority score",
        "kpi_dr_note": "Competitors score {comp_min}–{comp_max}. Higher scores correlate with AI citation preference.",
        "status_pending": "Pending",
        "status_tested": "Measured",
        "status_detected": "Detected",
        "status_partial": "Partial coverage",
        "status_critical_gap": "Critical gap",
        "status_not_deployed": "Not deployed",
        "insight_label": "Insight",
        "platform_brand_visibility": "Brand visibility",
        "platform_unbranded_visibility": "Unbranded visibility",
        "platform_official_cite": "Official site citation rate",
        "platform_competitor_mentions": "Competitor mentions",
        "platform_samples_mentioned": "samples mentioned",
        "platform_unbranded_samples": "unbranded samples",
        "platform_cited_official": "official-site citations",
        "platform_low_competitor": "Low competitor share",
        "platform_footer": "Platform metrics come from this run's AI answer samples; unbranded visibility is the key pre-conversion metric.",
        "platform_pending": "Next run",
        "platform_pending_sub": "Pending",
        "platform_untested_note": "Note: {name} was not independently tested this run; do not interpret pending items as zero performance.",
        "platform_competitive_strength": "Low competitor share {pct}",
        "meta_per_platform_prompts": "{count} prompts per platform",
        "meta_per_platform_prompts_partial": "Planned {planned} prompts per platform (actual coverage incomplete)",
        "compare_unbranded": "Unbranded visibility",
        "compare_branded": "Brand visibility",
        "compare_competitor_inverse": "Low competitor share",
        "compare_pending": "Pending — next run",
        "cover_platforms_and_more": "{joined} and {count} platforms",
        "cover_platforms_count_only": "{count} major AI platforms",
        "funnel_seg_complete": "Fully visible",
        "funnel_seg_partial": "Partially visible",
        "funnel_seg_brand_absent": "Brand absent",
        "funnel_seg_mine": "Target present",
        "funnel_seg_comp": "Competitor present",
        "funnel_seg_all_blank": "All absent",
        "vs_label": "vs",
        "status_proxy": "Proxy evidence",
        "status_mixed": "Mixed evidence",
        "status_not_tested": "Not tested this run",
        "status_not_independent": "Not independently tested",
        "status_unavailable": "Unavailable",
        "status_failed": "Collection failed",
        "status_blocked": "Crawl blocked",
        # Section 02
        # Section 02 content keys (rendered as SECTION 01 — order: TOP distribution → core metrics)
        "section_02_no": "SECTION 01 · TOP DISTRIBUTION",
        "section_02_title": "Where {brand_name} appears across {total_samples} AI answer samples",
        "section_02_desc": "After classifying samples by brand presence, official-site citation, and competitor takeover, the main gap is not brand-recognition accuracy, but whether the brand can enter recommendation lists in the front-of-funnel (unbranded scenarios).",
        "section_02_card_title": "Sample distribution overview",
        "section_02_card_note": "Two scenario groups side by side: branded queries ({branded_total}) and non-branded queries ({unbranded_total}); each row is normalized to 100% — hover for percentages.",
        "legend_visible": "Visible",
        "legend_improve": "Needs improvement / competitor",
        "legend_absent": "Absent",
        "scenario_card_title": "Scenario breakdown",
        "scenario_card_note": "Different statistical bases: branded rows are overlapping attributes; non-branded rows are a MECE partition (three segments sum to {unbranded_total}).",
        "scenario_group_branded": "User named the brand · branded queries {total}",
        "scenario_group_unbranded": "User did not name the brand · non-branded queries {total}",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · Pre-conversion",
        "scenario_visibility_mix": "Visibility mix",
        "scenario_children_note": "Visibility and official-site citation in branded queries",
        "scenario_unbranded_gap_note": "Competitor {comp_pct}% + fully absent {blank_pct}% = {absent_pct}% not recommended. This is the pre-conversion gap.",
        "scenario_recognized": "Recognized",
        "scenario_not_recognized": "Not recognized",
        "scenario_cited": "Official site cited",
        "scenario_not_cited": "Official site not cited",
        "scenario_mine": "Target present",
        "scenario_comp_takeover": "Absent · competitor takeover",
        "scenario_all_blank": "Absent · all blank",
        "scenario_read_note": "Non-branded queries are the pre-conversion funnel. When absent (competitor {comp} + blank {blank} = {absent}), competitors get recommended first. Low official-site citation {cited}/{branded_total} on branded queries means AI knows the brand but rarely links back.",
        # Section 03
        "section_03_no": "SECTION 03 · SENTIMENT",
        "section_03_title": "How AI talks about {brand_name} — positive or negative",
        "section_03_desc": "Each AI answer is classified (positive / neutral / negative) when {brand_name} is mentioned. Lower negative share is safer; high neutral share means mentioned but not endorsed.",
        "senti_overall_title": "Overall sentiment mix",
        "senti_overall_note": "Share of all {total} answers after per-answer sentiment classification.",
        "senti_platform_title": "Sentiment by platform",
        "senti_platform_note": "Same methodology split per tested platform to compare consistency.",
        "senti_positive": "Positive",
        "senti_neutral": "Neutral",
        "senti_negative": "Negative",
        "senti_stat_line": "{label} · {count} answers",
        "senti_plat_counts": "pos {pos} · neu {neu} · neg {neg}",
        "senti_insight_with_data": "Across {total} AI answers, {pos} positive ({pos_pct}) and only {neg} negative ({neg_pct}) — little reputational risk when AI discusses {brand_name}. The opportunity is {neu_pct} neutral: mentioned without endorsement. Converting neutral to positive backing is the jump from visibility to recommendation.",
        "senti_insight_no_data": "No classifiable sentiment samples this run.",
        "senti_cloud_title": "Sentiment word cloud",
        "senti_cloud_badge": "LLM phrase extract",
        "senti_cloud_note": "Phrases extracted from positive/neutral/negative answers that mention {brand_name}; larger type means more answers.",
        "senti_cloud_tab_positive": "Positive keywords",
        "senti_cloud_tab_neutral": "Neutral keywords",
        "senti_cloud_tab_negative": "Negative keywords",
        "senti_cloud_tooltip_count": "Seen in {count} answers",
        "senti_cloud_empty_generic": "No keywords for this polarity yet.",
        "senti_cloud_empty_missing": "Sentiment keyword artifact was not produced this run.",
        "senti_cloud_empty_no_answers": "Too few mentioned answers to extract keywords.",
        "senti_cloud_empty_no_phrases": "Sentiment samples exist, but no displayable phrases were extracted.",
        # Section 04
        "section_04_no": "SECTION 04 · PLATFORM PERFORMANCE",
        "section_04_title": "Visibility differences across major AI models",
        "section_04_desc": "Tested platforms share the same prompt set; untested platforms stay marked pending — not scored as zero.",
        "plat_compare_title": "Platform visibility comparison",
        "plat_compare_note": "Three visibility metrics (0–100%, higher is better) per platform; official-site citation rate is on platform cards above.",
        "plat_matrix_title": "Recommendation resistance matrix",
        "plat_matrix_note": "X = unbranded visibility (right is better); Y = competitor share (lower is better); bubble size = sample count. Bottom-right blue = ideal; top-left = high risk.",
        # Section 05
        "section_05_no": "SECTION 05 · SOURCE AUTHORITY",
        "section_05_title": "What source types AI can cite about us",
        "section_05_desc": "Light blue = cross-category baseline; purple = current state; proxy estimates are labeled.",
        "auth_radar_title": "Brand credibility radar",
        "auth_radar_note": "Five dimensions measure authoritative content footprint: official source = DR + AI citation (6:4, measured); encyclopedia / media / community / depth are directional.",
        "auth_dim_title": "Dimension interpretation",
        "auth_dim_note": "Scores reflect how much credible content AI can find per channel (0–100 relative).",
        "auth_focus_note": "Focus: encyclopedia, media, and community — primary signals for external validation.",
        "legend_radar_industry": "Cross-category baseline",
        "legend_radar_current": "{brand_name} current",
        # Section 06
        "section_06_no": "SECTION 06 · CHANNEL PRESENCE",
        "section_06_title": "Where AI can find content about us",
        "section_06_desc": "Same 0–100 scale as radar: site / encyclopedia / media map to radar axes; YouTube and Reddit split the community axis (community = their mean). Higher is better.",
        "src_bar_title": "Channel score comparison",
        "src_bar_note": "Purple = {brand_name} current; gray = peer reference level (directional).",
        "legend_peer_ref": "Peer reference",
        # Section 07
        "section_07_no": "SECTION 07 · COMPETITOR GAP",
        "section_07_title": "Recommendation resistance and competitor pressure",
        "section_07_desc": "X = unbranded AI visibility (% measured); Y = share of answers citing the brand as a source (%). Hollow points = proxy from domain authority when citation share is unavailable.",
        "comp_bubble_title": "Competitor presence in AI answers",
        "comp_bubble_note": "X = mention frequency on unbranded queries (measured); Y = citation-as-source share. Hollow = proxy estimate.",
        "dr_bar_title": "Domain authority comparison",
        "dr_bar_note": "Domain authority reflects how many external sites link to the domain; higher scores correlate with AI trust. Max 100.",
        "search_dr_row": "DR {dr} · Organic {organic} · Keywords {keywords}",
        # Section 08
        "section_08_no": "SECTION 08 · COMPETITOR RANKING",
        "section_08_title": "Who AI mentions most in the category",
        "section_08_desc": "Rank {brand_name} against competitors by real mention counts in {denom} category (unbranded) AI answers. Higher rank = better pre-decision recommendation slot.",
        "rank_card_title": "Category mention leaderboard",
        "rank_card_note": "Purple highlight = {brand_name}; bar length = relative mention frequency; right = absolute count and share of non-branded queries.",
        "rank_card_badge": "{denom} non-branded queries",
        "rank_you_tag": "This brand",
        "rank_focus_tag": "Focus",
        "rank_count_line": "{mentions} mentions · {rate}",
        "rank_phrase": "rank #{rank}",
        "rank_not_listed": "not ranked",
        "rank_headline_ranked": "Among {total_brands} brands in the category, {brand_name} ranks <b>{rank_phrase}</b> by mention frequency on unbranded AI queries.",
        "rank_headline_unranked": "Among {total_brands} brands in the category, {brand_name} has not entered the mention ranking on unbranded AI queries yet.",
        "focus_comp_kicker": "Focus competitors",
        "focus_comp_title": "Watched competitors for this report",
        "focus_comp_note": "From report setup (more precise than auto-discovery). Mentions below are measured in this run's unbranded sample; absence means not named in-sample, not “not a competitor”.",
        "focus_comp_mentions": "{count} unbranded mentions",
        "focus_comp_rank": "rank #{rank}",
        "focus_comp_absent": "not named this run",
        # Section 09
        "section_09_no": "SECTION 09 · CHANNEL DIAGNOSTICS",
        "section_09_title": "Where the gaps are and what to fix fast",
        "section_09_desc": "Official site first, then off-site / social footprint. Blue = measured OK; yellow = needs improvement; red = clear gap; gray = not independently tested this run.",
        "channel_group_official_kicker": "01 · On-site",
        "channel_group_official_title": "Official site",
        "channel_group_official_note": "Machine-readability of the site: structured markup, semantic boundaries, heading hierarchy, one-line definition, crawl hints, and citable body/inner-page density.",
        "channel_group_offsite_kicker": "02 · Off-site",
        "channel_group_offsite_title": "Backlinks / social",
        "channel_group_offsite_note": "Off-site footprint: backlink totals, video/community search volume, encyclopedia presence. Social counts come from keyword search and may not equal verified brand-related content.",
        # Section 10
        "section_10_no": "SECTION 10 · ROOT CAUSES",
        "section_10_title": "Why AI does not actively recommend {brand_name} yet",
        # Section 11
        "section_11_no": "SECTION 11 · RECOMMENDATIONS",
        "section_11_title": "Where to start and how",
        "section_11_desc": "Official-site work is always first: machine-readable structure and citable pages before off-site/social. Sorted by effort and expected impact.",
        "recs_col_priority": "Priority",
        "recs_col_action": "Action",
        "recs_col_why": "Why this",
        "recs_col_metric": "Expected metric change",
        "recs_col_effort": "Effort band",
        "recs_site_markup_hint": "JSON-LD Schema · semantic HTML · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "Category pages · comparison/buying guides · clear H2 sections · citable fact blocks",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        # Section 12
        "section_12_no": "SECTION 12 · CITED SOURCES",
        "section_12_title": "Which sites and articles AI actually cited",
        "section_12_desc": "Counts citations that appear in the answer (not search listings). Ranked by domain frequency; shows the top 30. If the official site is outside the top 30, it is listed at the end. Expand a row to see article URLs and counts.",
        "cite_rank_tab_branded": "Branded queries",
        "cite_rank_tab_unbranded": "Non-branded queries",
        "cite_rank_tab_meta": "{answers} answers · {citations} citations",
        "cite_rank_empty": "No applied citations were captured for this query set",
        "cite_rank_count": "{count}×",
        "cite_rank_official": "Official site",
        "cite_rank_urls_n": "{count} articles",
        "cite_rank_truncated": "Showing top {n} of {total} domains",
        "cite_rank_unlisted": "Unranked",
        "section_13_no": "SECTION 12 · PROMPTS & ANSWERS",
        "section_13_title": "Open any row to inspect what AI actually answered",
        "qa_group_branded": "Branded prompt",
        "qa_group_unbranded": "Unbranded prompt",
        "qa_group_default": "Query",
        "qa_dot_mentioned": "Mentioned",
        "qa_dot_not_mentioned": "Not mentioned",
        "qa_badge_mentioned": "Brand mentioned",
        "qa_badge_not_mentioned": "Not mentioned",
        "qa_badge_cite_official": "Official site cited",
        "qa_badge_cite_missing": "Official site not cited",
        "qa_badge_partial_visible": "Partially visible",
        "qa_badge_fully_visible": "Fully visible",
        "qa_dots_legend": "Dots = whether each platform mentioned the brand (blue = yes, gray = no)",
        "qa_comp_mentioned": "Competitors in same answer: {names}",
        "qa_queried_as": "Actual prompt: {text}",
        "qa_no_excerpt": "(Full answer not stored — often collection failure or legacy report without answer body.)",
        "qa_evidence": "Classification basis:",
        "qa_evidence_corrected": "Brand name not found in the answer body; corrected to not mentioned",
        "qa_evidence_corrected_original": "Brand name not found in the answer body; corrected to not mentioned. Original basis: {evidence}",
        "qa_sources": "Sources",
        "qa_source_cited": "Seen in answer",
        "qa_source_listed": "Listed source",
        "qa_no_sources": "No sources captured for this answer",
        "qa_expand_answer": "Expand full answer",
        "qa_collapse_answer": "Collapse answer",
        "qa_open_modal": "View details",
        "qa_modal_close": "Close",
        "qa_modal_question": "Prompt",
        "qa_modal_actual_prompt": "Actual platform prompt",
        "qa_modal_status": "Status tags",
        "qa_modal_ranking": "Brand / competitor order in answer",
        "qa_modal_competitors": "Competitors mentioned",
        "qa_no_platform": "No platform answers for this prompt",
        "qa_no_competitors": "No competitor mentions detected",
        "qa_no_rank": "No ranking signals available",
        "qa_rank_absent": "Absent",
        "qa_section_note": "Click any prompt to open a modal with platform tabs, Markdown-rendered answers, sources, classification notes, and mention order.",
        # Boundary
        "boundary_title": "Data notes",
        "boundary_tested": "Tested this run:",
        "boundary_not_tested": "Not independently tested this run",
        "boundary_not_tested_note": "(not a zero score — can be tested next run)",
        "boundary_proxy": "Proxy estimates",
        "boundary_proxy_note": "(directional, not precise measurement)",
        "boundary_scope": "Findings reflect this run's prompt scope, not every possible search scenario.",
        "boundary_legal": "For status assessment and next-run measurement only — not an implementation commitment, quote, or contract term.",
        # Misc
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "Target brand",
        "rivals_fallback": "competitors",
        "industry_mean": "Industry mean (directional)",
        "chart_tooltip_seg": "{label}: {pct}% ({count}/{total})",
        "chart_tooltip_plat_bubble": "{name}: unbranded visibility {x}%, competitor share {y}%, n={n}",
        "chart_tooltip_comp_scatter": "{name}: visibility {x}%, source share {y}%{tag}",
        "chart_tooltip_comp_proxy": " (est.)",
        # Narrative fallbacks
        "fallback_section_01_desc": "AI recognizes {brand_name} in {branded_mentioned}/{branded_total} named-brand answers ({branded_rate}%). On pre-decision category questions, {brand_name} appears in {unbranded_mentioned}/{unbranded_total} cases; competitors fill the slot {takeover} times.",
        "fallback_main_insight": "This run shows <b>{branded_rate}% named-brand recognition</b> for {brand_name}, but absence from {unbranded_absent}/{unbranded_total} unbranded decision scenarios, including {takeover} recommendation slots occupied by {rivals}. Prioritize evidence that improves unbranded discovery, then retest with the same prompt set.",
        "fallback_section_05_insight": "Competitors score higher on external sources because they have denser user-generated citations on YouTube, Reddit, and industry media — signals AI trusts for unbranded recommendations. {brand_name}'s owned content is fine, but third-party citation density is lower. Gray bars are untested, not zero; start with Schema, Meta, and llms.txt, then build external citations.",
        "fallback_section_06_dr_note": "{brand_name} DR is {dr}; competitors range {comp_min}–{comp_max} — a modest gap. DR measures backlink volume, not topical relevance. Competitors have denser niche citations in media and communities, which weigh more for AI recommendations than raw DR. Chase topical authority citations, not DR alone.",
        "fallback_section_07_insight": "{brand_name} has mature assets — site and brand awareness — but most are built for humans and search engines, not AI recommendation logic. Competitors are more structured and cited externally, so AI prefers them on unbranded queries. Re-encode existing assets for AI; delay compounds competitor corpus advantage. Gray channels were not independently tested.",
        "fallback_section_08_desc": "Three stacked gaps displace {brand_name} in AI recommendations: unclear product boundaries → no citable pages on non-branded queries → competitors with stronger signals win the slot. The layers amplify each other.",
        "fallback_section_09_insight": "The official site is AI's first trusted source for {brand_name} — keep improving it, not one-and-done. P0 covers two tracks: (1) machine-readable structure (Schema, semantic tags, H1/H2, Meta, llms.txt); (2) citable content and category entry pages. Off-site/social amplify on-site work and should not come first. Bind every initiative to re-testable AI metrics.",
        "fallback_root_expression": "{brand} site content may look complete for humans, but weak structure or thin citable sections force AI to stitch positioning from scattered paragraphs — less efficient than well-structured competitors, and visible in skipped unbranded recommendations.<br/><br/>Evidence: {evidence}.",
        "fallback_root_supply": "{brand} lacks pages that answer pre-decision category questions — comparisons, selection, and competitor differentiation AI can cite. Competitors cover these semantic nodes more densely.<br/><br/>Evidence: {evidence}.",
        "fallback_root_distribution": "This is the first acquisition gate: buyers ask AI before choosing a vendor. In unbranded scenarios {brand} is often absent and competitors take the recommendation slot. Each absence routes a prospect to rivals.<br/><br/>Evidence: {evidence}.",
        # Channel description expansions
        "ch_desc_backlinks": "{desc} Backlink volume and quality help AI judge whether to recommend a brand. Next run: check media, review sites, and industry directories.",
        "ch_desc_youtube_tested": "{desc} AI uses video (reviews, tutorials, unboxing) to describe products; more visible brand video yields more specific AI copy.",
        "ch_desc_youtube_untested": "YouTube was not independently tested this run. AI uses video content for product answers; verify brand video footprint next run.",
        "ch_desc_reddit_tested": "{desc} AI weighs Reddit and forums for user feedback — praise and complaints — affecting whether it adds caveats or recommends alternatives.",
        "ch_desc_reddit_untested": "Community sentiment was not independently tested. Reddit and forums shape how AI frames user feedback and recommendations.",
        "ch_desc_wikipedia": "{desc} Wikipedia is a common disambiguation source. No article increases confusion risk when brand names collide.",
        "ch_desc_schema": "{desc} Schema makes pages machine-readable for AI — brand, category, audience. Without it, AI guesses from body text. Low cost, high priority.",
        "ch_desc_semantic": "{desc} Without clear headings and sections, AI struggles to parse the page and may borrow competitor phrasing. Fixable on-site.",
        "ch_desc_meta": "{desc} Meta description is often the first source for AI brand summaries. Empty meta forces improvised, weaker copy.",
        "ch_desc_llms": "{desc} llms.txt is an emerging convention to tell crawlers which pages matter. Combine with Schema and Meta for faster machine readability.",
    },
    "pt-BR": {
        "report_title_suffix": "Relatório de Diagnóstico de Desempenho em Modelos de IA",
        "report_sub": "Com base em {total_samples} amostras de respostas em {platform_phrase}, combinadas com sinais estruturais do site oficial, perfis de tráfego de busca e benchmarks de concorrentes, este relatório avalia a menção, citação e presença de recomendação de {brand_name} em busca generativa e motores de resposta.",
        "report_audience": "Para decisores de marca, marketing e negócios.",
        "meta_subject": "Objeto",
        "meta_business": "Escopo de negócio",
        "meta_platforms": "Plataformas amostradas",
        "meta_date": "Data do relatório",
        "meta_report_code": "Código do relatório",
        "section_01_no": "SECTION 02 · MÉTRICAS PRINCIPAIS",
        "section_01_title": "Quatro números que enquadram a situação",
        "kpi_unbranded": "Presença sem marca",
        "kpi_unbranded_note": "Vezes em que {brand_name} apareceu quando compradores perguntam sem nomear uma marca.",
        "kpi_branded": "Reconhecimento com marca",
        "kpi_branded_note": "Quando os usuários nomeiam a marca, a maioria das respostas a reconhece — os ativos existem, mas precisam ser expostos mais cedo.",
        "kpi_competitor": "Respostas ocupadas por concorrentes",
        "kpi_competitor_note": "Respostas em que {brand_name} está ausente e pelo menos um concorrente aparece; cada resposta conta uma vez ({rate}% dos cenários de ausência).",
        "kpi_dr": "Pontuação de autoridade do domínio",
        "kpi_dr_note": "Concorrentes pontuam {comp_min}–{comp_max}. Pontuações mais altas correlacionam com preferência de citação pela IA.",
        "status_pending": "Pendente",
        "status_tested": "Medido",
        "status_detected": "Detectado",
        "status_partial": "Cobertura parcial",
        "status_critical_gap": "Lacuna crítica",
        "status_not_deployed": "Não implantado",
        "insight_label": "Insight",
        "platform_brand_visibility": "Visibilidade da marca",
        "platform_unbranded_visibility": "Visibilidade sem marca",
        "platform_official_cite": "Taxa de citação do site oficial",
        "platform_competitor_mentions": "Menções de concorrentes",
        "platform_samples_mentioned": "amostras mencionadas",
        "platform_unbranded_samples": "amostras sem marca",
        "platform_cited_official": "citações do site oficial",
        "platform_low_competitor": "Baixa participação de concorrentes",
        "platform_footer": "As métricas da plataforma vêm das amostras de respostas de IA desta rodada; a visibilidade sem marca é a métrica-chave pré-conversão.",
        "platform_pending": "Próxima rodada",
        "platform_pending_sub": "Pendente",
        "platform_untested_note": "Nota: {name} não foi testado de forma independente nesta rodada; não interprete itens pendentes como desempenho zero.",
        "platform_competitive_strength": "Baixa participação de concorrentes {pct}",
        "meta_per_platform_prompts": "{count} prompts por plataforma",
        "meta_per_platform_prompts_partial": "Planejados {planned} prompts por plataforma (cobertura real incompleta)",
        "compare_unbranded": "Visibilidade sem marca",
        "compare_branded": "Visibilidade da marca",
        "compare_competitor_inverse": "Baixa participação de concorrentes",
        "compare_pending": "Pendente — próxima rodada",
        "cover_platforms_and_more": "{joined} e {count} plataformas",
        "cover_platforms_count_only": "{count} principais plataformas de IA",
        "funnel_seg_complete": "Totalmente visível",
        "funnel_seg_partial": "Parcialmente visível",
        "funnel_seg_brand_absent": "Marca ausente",
        "funnel_seg_mine": "Marca-alvo presente",
        "funnel_seg_comp": "Concorrente presente",
        "funnel_seg_all_blank": "Todos ausentes",
        "vs_label": "vs",
        "status_proxy": "Evidência proxy",
        "status_mixed": "Evidência mista",
        "status_not_tested": "Não testado nesta rodada",
        "status_not_independent": "Não testado de forma independente",
        "status_unavailable": "Indisponível",
        "status_failed": "Falha na coleta",
        "status_blocked": "Rastreamento bloqueado",
        "section_02_no": "SECTION 01 · DISTRIBUIÇÃO TOP",
        "section_02_title": "Onde {brand_name} aparece em {total_samples} amostras de respostas de IA",
        "section_02_desc": "Após classificar as amostras por presença da marca, citação do site oficial e tomada por concorrentes, a principal lacuna não é a precisão do reconhecimento da marca, e sim se a marca consegue entrar nas listas de recomendação no topo do funil (cenários sem marca).",
        "section_02_card_title": "Visão geral da distribuição das amostras",
        "section_02_card_note": "Dois grupos de cenários lado a lado: consultas com marca ({branded_total}) e consultas sem marca ({unbranded_total}); cada linha é normalizada a 100% — passe o mouse para ver percentuais.",
        "legend_visible": "Visível",
        "legend_improve": "Precisa melhorar / concorrente",
        "legend_absent": "Ausente",
        "scenario_card_title": "Detalhamento por cenário",
        "scenario_card_note": "Bases estatísticas diferentes: as linhas com marca são atributos sobrepostos; as linhas sem marca são uma partição MECE (três segmentos somam {unbranded_total}).",
        "scenario_group_branded": "Usuário nomeou a marca · consultas com marca {total}",
        "scenario_group_unbranded": "Usuário não nomeou a marca · consultas sem marca {total}",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · Pré-conversão",
        "scenario_visibility_mix": "Mix de visibilidade",
        "scenario_children_note": "Visibilidade e citação do site oficial nas perguntas com marca",
        "scenario_unbranded_gap_note": "Concorrente {comp_pct}% + totalmente ausente {blank_pct}% = {absent_pct}% fora da recomendação. Esta é a lacuna pré-conversão.",
        "scenario_recognized": "Reconhecida",
        "scenario_not_recognized": "Não reconhecida",
        "scenario_cited": "Site oficial citado",
        "scenario_not_cited": "Site oficial não citado",
        "scenario_mine": "Marca-alvo presente",
        "scenario_comp_takeover": "Ausente · tomada por concorrente",
        "scenario_all_blank": "Ausente · tudo em branco",
        "scenario_read_note": "Consultas sem marca são o funil pré-conversão. Quando ausente (concorrente {comp} + em branco {blank} = {absent}), os concorrentes são recomendados primeiro. Baixa citação do site oficial {cited}/{branded_total} em consultas com marca significa que a IA conhece a marca, mas raramente linka de volta.",
        "section_03_no": "SECTION 03 · SENTIMENTO",
        "section_03_title": "Como a IA fala de {brand_name} — positivo ou negativo",
        "section_03_desc": "Cada resposta de IA é classificada (positiva / neutra / negativa) quando {brand_name} é mencionada. Menor participação negativa é mais seguro; alta participação neutra significa mencionada, mas sem endosso.",
        "senti_overall_title": "Mix geral de sentimento",
        "senti_overall_note": "Participação de todas as {total} respostas após classificação de sentimento por resposta.",
        "senti_platform_title": "Sentimento por plataforma",
        "senti_platform_note": "Mesma metodologia dividida por plataforma testada para comparar consistência.",
        "senti_positive": "Positivo",
        "senti_neutral": "Neutro",
        "senti_negative": "Negativo",
        "senti_stat_line": "{label} · {count} respostas",
        "senti_plat_counts": "pos {pos} · neu {neu} · neg {neg}",
        "senti_insight_with_data": "Em {total} respostas de IA, {pos} positivas ({pos_pct}) e apenas {neg} negativas ({neg_pct}) — pouco risco reputacional quando a IA discute {brand_name}. A oportunidade está nos {neu_pct} neutros: mencionada sem endosso. Converter neutro em respaldo positivo é o salto da visibilidade para a recomendação.",
        "senti_insight_no_data": "Nenhuma amostra de sentimento classificável nesta rodada.",
        "senti_cloud_title": "Nuvem de palavras de sentimento",
        "senti_cloud_badge": "Extração de frases por LLM",
        "senti_cloud_note": "Frases extraídas de respostas positivas/neutras/negativas que mencionam {brand_name}; tipo maior significa mais respostas.",
        "senti_cloud_tab_positive": "Palavras-chave positivas",
        "senti_cloud_tab_neutral": "Palavras-chave neutras",
        "senti_cloud_tab_negative": "Palavras-chave negativas",
        "senti_cloud_tooltip_count": "Visto em {count} respostas",
        "senti_cloud_empty_generic": "Ainda sem palavras-chave para esta polaridade.",
        "senti_cloud_empty_missing": "O artefato de palavras-chave de sentimento não foi produzido nesta rodada.",
        "senti_cloud_empty_no_answers": "Poucas respostas com menção para extrair palavras-chave.",
        "senti_cloud_empty_no_phrases": "Existem amostras de sentimento, mas nenhuma frase exibível foi extraída.",
        "section_04_no": "SECTION 04 · DESEMPENHO POR PLATAFORMA",
        "section_04_title": "Diferenças de visibilidade entre os principais modelos de IA",
        "section_04_desc": "Plataformas testadas compartilham o mesmo conjunto de prompts; plataformas não testadas permanecem marcadas como pendentes — não pontuadas como zero.",
        "plat_compare_title": "Comparação de visibilidade por plataforma",
        "plat_compare_note": "Três métricas de visibilidade (0–100%, quanto maior melhor) por plataforma; a taxa de citação do site oficial está nos cards de plataforma acima.",
        "plat_matrix_title": "Matriz de resistência à recomendação",
        "plat_matrix_note": "X = visibilidade sem marca (direita é melhor); Y = participação de concorrentes (menor é melhor); tamanho da bolha = contagem de amostras. Azul inferior direito = ideal; superior esquerdo = alto risco.",
        "section_05_no": "SECTION 05 · AUTORIDADE DE FONTES",
        "section_05_title": "Que tipos de fonte a IA pode citar sobre nós",
        "section_05_desc": "Azul claro = baseline cross-categoria; roxo = estado atual; estimativas proxy estão rotuladas.",
        "auth_radar_title": "Radar de credibilidade da marca",
        "auth_radar_note": "Cinco dimensões medem a pegada de conteúdo autoritativo: fonte oficial = DA + citação por IA (6:4, medido); enciclopédia / mídia / comunidade / profundidade são direcionais.",
        "auth_dim_title": "Interpretação das dimensões",
        "auth_dim_note": "As pontuações refletem quanto conteúdo credível a IA encontra por canal (0–100 relativo).",
        "auth_focus_note": "Foque em: enciclopédia, mídia e comunidade — sinais principais de validação externa.",
        "legend_radar_industry": "Baseline cross-categoria",
        "legend_radar_current": "{brand_name} atual",
        "section_06_no": "SECTION 06 · PRESENÇA POR CANAL",
        "section_06_title": "Onde a IA encontra conteúdo sobre nós",
        "section_06_desc": "Mesma escala 0–100 do radar: site / enciclopédia / mídia mapeiam para os eixos; YouTube e Reddit dividem o eixo comunidade (comunidade = média deles). Quanto maior, melhor.",
        "src_bar_title": "Comparação de pontuação por canal",
        "src_bar_note": "Roxo = {brand_name} atual; cinza = nível de referência de pares (direcional).",
        "legend_peer_ref": "Referência de pares",
        "section_07_no": "SECTION 07 · GAP DE CONCORRENTES",
        "section_07_title": "Resistência à recomendação e pressão de concorrentes",
        "section_07_desc": "X = visibilidade de IA sem marca (% medido); Y = participação de respostas que citam a marca como fonte (%). Pontos ocos = proxy a partir da autoridade do domínio quando a participação de citação não está disponível.",
        "comp_bubble_title": "Presença de concorrentes nas respostas de IA",
        "comp_bubble_note": "X = frequência de menção em consultas sem marca (medido); Y = participação de citação como fonte. Oco = estimativa proxy.",
        "dr_bar_title": "Comparação de autoridade do domínio",
        "dr_bar_note": "A autoridade do domínio reflete quantos sites externos linkam para o domínio; pontuações mais altas correlacionam com confiança da IA. Máx. 100.",
        "search_dr_row": "DA {dr} · Organic {organic} · Keywords {keywords}",
        "section_08_no": "SECTION 08 · RANKING DE CONCORRENTES",
        "section_08_title": "Quem a IA menciona mais na categoria",
        "section_08_desc": "Classifique {brand_name} contra concorrentes por contagens reais de menção em {denom} respostas de IA de categoria (sem marca). Ranking mais alto = melhor slot de recomendação pré-decisão.",
        "rank_card_title": "Ranking de menções na categoria",
        "rank_card_note": "Destaque roxo = {brand_name}; comprimento da barra = frequência relativa de menção; à direita = contagem absoluta e participação das consultas sem marca.",
        "rank_card_badge": "{denom} consultas sem marca",
        "rank_you_tag": "Esta marca",
        "rank_focus_tag": "Foco",
        "rank_count_line": "{mentions} menções · {rate}",
        "rank_phrase": "posição #{rank}",
        "rank_not_listed": "fora do ranking",
        "rank_headline_ranked": "Entre {total_brands} marcas na categoria, {brand_name} fica em <b>{rank_phrase}</b> por frequência de menção em consultas de IA sem marca.",
        "rank_headline_unranked": "Entre {total_brands} marcas na categoria, {brand_name} ainda não entrou no ranking de menções em consultas de IA sem marca.",
        "focus_comp_kicker": "Concorrentes em foco",
        "focus_comp_title": "Concorrentes observados neste relatório",
        "focus_comp_note": "Da configuração do relatório (mais preciso que a descoberta automática). As menções abaixo foram medidas na amostra sem marca desta rodada; ausência significa não nomeado na amostra, não “não é concorrente”.",
        "focus_comp_mentions": "{count} menções sem marca",
        "focus_comp_rank": "posição #{rank}",
        "focus_comp_absent": "não nomeado nesta rodada",
        "section_09_no": "SECTION 09 · DIAGNÓSTICO POR CANAL",
        "section_09_title": "Onde estão as lacunas e o que corrigir rápido",
        "section_09_desc": "Site oficial primeiro, depois pegada off-site / social. Azul = medido OK; amarelo = precisa melhorar; vermelho = lacuna clara; cinza = não testado de forma independente nesta rodada.",
        "channel_group_official_kicker": "01 · On-site",
        "channel_group_official_title": "Site oficial",
        "channel_group_official_note": "Legibilidade por máquinas do site: marcação estruturada, limites semânticos, hierarquia de títulos, definição em uma linha, dicas de rastreamento e densidade citável no corpo/páginas internas.",
        "channel_group_offsite_kicker": "02 · Off-site",
        "channel_group_offsite_title": "Backlinks / social",
        "channel_group_offsite_note": "Pegada off-site: totais de backlinks, volume de busca em vídeo/comunidade, presença em enciclopédia. Contagens sociais vêm de busca por palavra-chave e podem não igualar conteúdo verificado relacionado à marca.",
        "section_10_no": "SECTION 10 · CAUSAS-RAIZ",
        "section_10_title": "Por que a IA ainda não recomenda ativamente {brand_name}",
        "section_11_no": "SECTION 11 · RECOMENDAÇÕES",
        "section_11_title": "Por onde começar e como",
        "section_11_desc": "O trabalho no site oficial vem sempre primeiro: estrutura legível por máquinas e páginas citáveis antes de off-site/social. Ordenado por esforço e impacto esperado.",
        "recs_col_priority": "Prioridade",
        "recs_col_action": "Ação",
        "recs_col_why": "Por que isto",
        "recs_col_metric": "Mudança esperada de métrica",
        "recs_col_effort": "Faixa de esforço",
        "recs_site_markup_hint": "JSON-LD Schema · HTML semântico · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "Páginas de categoria · guias de comparação/compra · seções H2 claras · blocos de fatos citáveis",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        "section_12_no": "SECTION 12 · FONTES CITADAS",
        "section_12_title": "Quais sites e artigos a IA realmente citou",
        "section_12_desc": "Conta citações que aparecem na resposta (não listagens de busca). Ordenado por frequência de domínio; mostra os 30 principais. Se o site oficial ficar fora do top 30, aparece no final. Abra a linha para ver URLs e contagens.",
        "cite_rank_tab_branded": "Consultas com marca",
        "cite_rank_tab_unbranded": "Consultas sem marca",
        "cite_rank_tab_meta": "{answers} respostas · {citations} citações",
        "cite_rank_empty": "Nenhuma citação aplicada foi capturada neste conjunto",
        "cite_rank_count": "{count}×",
        "cite_rank_official": "Site oficial",
        "cite_rank_urls_n": "{count} artigos",
        "cite_rank_truncated": "Exibindo os {n} principais de {total} domínios",
        "cite_rank_unlisted": "Fora do ranking",
        "section_13_no": "SECTION 12 · PROMPTS E RESPOSTAS",
        "section_13_title": "Abra qualquer linha para inspecionar o que a IA realmente respondeu",
        "qa_group_branded": "Prompt com marca",
        "qa_group_unbranded": "Prompt sem marca",
        "qa_group_default": "Consulta",
        "qa_dot_mentioned": "Mencionada",
        "qa_dot_not_mentioned": "Não mencionada",
        "qa_badge_mentioned": "Marca mencionada",
        "qa_badge_not_mentioned": "Não mencionada",
        "qa_badge_cite_official": "Site oficial citado",
        "qa_badge_cite_missing": "Site oficial não citado",
        "qa_badge_partial_visible": "Parcialmente visível",
        "qa_badge_fully_visible": "Totalmente visível",
        "qa_dots_legend": "Pontos = se cada plataforma mencionou a marca (azul = sim, cinza = não)",
        "qa_comp_mentioned": "Concorrentes na mesma resposta: {names}",
        "qa_queried_as": "Prompt real: {text}",
        "qa_no_excerpt": "(Resposta completa não armazenada — frequentemente falha de coleta ou relatório legado sem corpo da resposta.)",
        "qa_evidence": "Base da classificação:",
        "qa_evidence_corrected": "Nome da marca não encontrado no corpo da resposta; corrigido para não mencionada",
        "qa_evidence_corrected_original": "Nome da marca não encontrado no corpo da resposta; corrigido para não mencionada. Base original: {evidence}",
        "qa_sources": "Fontes",
        "qa_source_cited": "Visto na resposta",
        "qa_source_listed": "Fonte listada",
        "qa_no_sources": "Nenhuma fonte capturada para esta resposta",
        "qa_expand_answer": "Expandir resposta completa",
        "qa_collapse_answer": "Recolher resposta",
        "qa_open_modal": "Ver detalhes",
        "qa_modal_close": "Fechar",
        "qa_modal_question": "Prompt",
        "qa_modal_actual_prompt": "Prompt real da plataforma",
        "qa_modal_status": "Tags de status",
        "qa_modal_ranking": "Ordem de marca / concorrente na resposta",
        "qa_modal_competitors": "Concorrentes mencionados",
        "qa_no_platform": "Sem respostas de plataforma para este prompt",
        "qa_no_competitors": "Nenhuma menção de concorrente detectada",
        "qa_no_rank": "Nenhum sinal de ranking disponível",
        "qa_rank_absent": "Ausente",
        "qa_section_note": "Clique em qualquer prompt para abrir um modal com abas por plataforma, respostas renderizadas em Markdown, fontes, notas de classificação e ordem de menção.",
        "boundary_title": "Notas sobre os dados",
        "boundary_tested": "Testado nesta rodada:",
        "boundary_not_tested": "Não testado de forma independente nesta rodada",
        "boundary_not_tested_note": "(não é pontuação zero — pode ser testado na próxima rodada)",
        "boundary_proxy": "Estimativas proxy",
        "boundary_proxy_note": "(direcional, não medição precisa)",
        "boundary_scope": "Os achados refletem o escopo de prompts desta rodada, não todos os cenários de busca possíveis.",
        "boundary_legal": "Apenas para avaliação de status e medição da próxima rodada — não constitui compromisso de implementação, cotação ou cláusula contratual.",
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "Marca-alvo",
        "rivals_fallback": "concorrentes",
        "industry_mean": "Média do setor (direcional)",
        "chart_tooltip_seg": "{label}: {pct}% ({count}/{total})",
        "chart_tooltip_plat_bubble": "{name}: visibilidade sem marca {x}%, participação de concorrentes {y}%, n={n}",
        "chart_tooltip_comp_scatter": "{name}: visibilidade {x}%, participação de fontes {y}%{tag}",
        "chart_tooltip_comp_proxy": " (est.)",
        "fallback_section_01_desc": "A IA reconhece {brand_name} em {branded_mentioned}/{branded_total} respostas com marca nomeada ({branded_rate}%). Em perguntas de categoria pré-decisão, {brand_name} aparece em {unbranded_mentioned}/{unbranded_total} casos; concorrentes ocupam o slot {takeover} vezes.",
        "fallback_main_insight": "Esta rodada mostra <b>reconhecimento com marca de {branded_rate}%</b> para {brand_name}, mas ausência em {unbranded_absent}/{unbranded_total} cenários de decisão sem marca, incluindo {takeover} slots de recomendação ocupados por {rivals}. Priorize evidências que melhorem a descoberta sem marca e depois reteste com o mesmo conjunto de prompts.",
        "fallback_section_05_insight": "Concorrentes pontuam mais em fontes externas porque têm citações geradas por usuários mais densas no YouTube, Reddit e mídia do setor — sinais em que a IA confia para recomendações sem marca. O conteúdo próprio de {brand_name} está bem, mas a densidade de citação de terceiros é menor. Barras cinza são não testadas, não zero; comece com Schema, Meta e llms.txt e depois construa citações externas.",
        "fallback_section_06_dr_note": "O DA de {brand_name} é {dr}; concorrentes variam {comp_min}–{comp_max} — um gap modesto. DA mede volume de backlinks, não relevância tópica. Concorrentes têm citações de nicho mais densas em mídia e comunidades, o que pesa mais para recomendações de IA do que DA bruto. Busque citações de autoridade tópica, não só DA.",
        "fallback_section_07_insight": "{brand_name} tem ativos maduros — site e reconhecimento de marca — mas a maioria foi feita para humanos e buscadores, não para a lógica de recomendação da IA. Concorrentes são mais estruturados e citados externamente, então a IA os prefere em consultas sem marca. Reencode ativos existentes para IA; o atraso reforça a vantagem de corpus dos concorrentes. Canais cinza não foram testados de forma independente.",
        "fallback_section_08_desc": "Três lacunas empilhadas deslocam {brand_name} nas recomendações de IA: limites de produto pouco claros → sem páginas citáveis em consultas sem marca → concorrentes com sinais mais fortes vencem o slot. As camadas se amplificam mutuamente.",
        "fallback_section_09_insight": "O site oficial é a primeira fonte confiável da IA para {brand_name} — continue melhorando, não é trabalho único. P0 cobre duas frentes: (1) estrutura legível por máquinas (Schema, tags semânticas, H1/H2, Meta, llms.txt); (2) conteúdo citável e páginas de entrada de categoria. Off-site/social amplificam o trabalho on-site e não devem vir primeiro. Vincule cada iniciativa a métricas de IA retestáveis.",
        "fallback_root_expression": "O conteúdo do site de {brand} pode parecer completo para humanos, mas estrutura fraca ou seções pouco citáveis forçam a IA a montar o posicionamento a partir de parágrafos dispersos — menos eficiente que concorrentes bem estruturados, e visível em recomendações sem marca ignoradas.<br/><br/>Evidência: {evidence}.",
        "fallback_root_supply": "{brand} carece de páginas que respondam perguntas de categoria pré-decisão — comparações, seleção e diferenciação de concorrentes que a IA possa citar. Concorrentes cobrem esses nós semânticos de forma mais densa.<br/><br/>Evidência: {evidence}.",
        "fallback_root_distribution": "Este é o primeiro portão de aquisição: compradores perguntam à IA antes de escolher um fornecedor. Em cenários sem marca, {brand} frequentemente está ausente e concorrentes ocupam o slot de recomendação. Cada ausência encaminha um prospecto aos rivais.<br/><br/>Evidência: {evidence}.",
        "ch_desc_backlinks": "{desc} Volume e qualidade de backlinks ajudam a IA a julgar se recomenda uma marca. Próxima rodada: verifique mídia, sites de avaliação e diretórios do setor.",
        "ch_desc_youtube_tested": "{desc} A IA usa vídeo (reviews, tutoriais, unboxing) para descrever produtos; mais vídeo visível da marca gera copy de IA mais específica.",
        "ch_desc_youtube_untested": "YouTube não foi testado de forma independente nesta rodada. A IA usa conteúdo em vídeo para respostas de produto; verifique a pegada de vídeo da marca na próxima rodada.",
        "ch_desc_reddit_tested": "{desc} A IA considera Reddit e fóruns para feedback de usuários — elogios e reclamações — afetando se adiciona ressalvas ou recomenda alternativas.",
        "ch_desc_reddit_untested": "O sentimento da comunidade não foi testado de forma independente. Reddit e fóruns moldam como a IA enquadra feedback e recomendações.",
        "ch_desc_wikipedia": "{desc} A Wikipedia é uma fonte comum de desambiguação. Sem artigo, aumenta o risco de confusão quando nomes de marca colidem.",
        "ch_desc_schema": "{desc} Schema torna as páginas legíveis por máquinas para a IA — marca, categoria, público. Sem ele, a IA adivinha pelo corpo do texto. Baixo custo, alta prioridade.",
        "ch_desc_semantic": "{desc} Sem títulos e seções claros, a IA tem dificuldade de analisar a página e pode pegar frases de concorrentes. Corrigível on-site.",
        "ch_desc_meta": "{desc} A meta description costuma ser a primeira fonte para resumos de marca pela IA. Meta vazia força copy improvisada e mais fraca.",
        "ch_desc_llms": "{desc} llms.txt é uma convenção emergente para dizer aos crawlers quais páginas importam. Combine com Schema e Meta para melhorar mais rápido a legibilidade por máquinas.",
    },
    "pt-PT": {
        "report_title_suffix": "Relatório de Diagnóstico de Desempenho em Modelos de IA",
        "report_sub": "Com base em {total_samples} amostras de respostas em {platform_phrase}, combinadas com sinais estruturais do site oficial, perfis de tráfego de busca e benchmarks de concorrentes, este relatório avalia a menção, citação e presença de recomendação de {brand_name} em busca generativa e motores de resposta.",
        "report_audience": "Para decisores de marca, marketing e negócios.",
        "meta_subject": "Objeto",
        "meta_business": "Escopo de negócio",
        "meta_platforms": "Plataformas amostradas",
        "meta_date": "Data do relatório",
        "meta_report_code": "Código do relatório",
        "section_01_no": "SECTION 02 · MÉTRICAS PRINCIPAIS",
        "section_01_title": "Quatro números que enquadram a situação",
        "kpi_unbranded": "Presença sem marca",
        "kpi_unbranded_note": "Vezes em que {brand_name} apareceu quando compradores perguntam sem nomear uma marca.",
        "kpi_branded": "Reconhecimento com marca",
        "kpi_branded_note": "Quando os utilizadores nomeiam a marca, a maioria das respostas a reconhece — os ativos existem, mas precisam ser expostos mais cedo.",
        "kpi_competitor": "Respostas ocupadas por concorrentes",
        "kpi_competitor_note": "Respostas em que {brand_name} está ausente e pelo menos um concorrente aparece; cada resposta conta uma vez ({rate}% dos cenários de ausência).",
        "kpi_dr": "Pontuação de autoridade do domínio",
        "kpi_dr_note": "Concorrentes pontuam {comp_min}–{comp_max}. Pontuações mais altas correlacionam com preferência de citação pela IA.",
        "status_pending": "Pendente",
        "status_tested": "Medido",
        "status_detected": "Detectado",
        "status_partial": "Cobertura parcial",
        "status_critical_gap": "Lacuna crítica",
        "status_not_deployed": "Não implantado",
        "insight_label": "Insight",
        "platform_brand_visibility": "Visibilidade da marca",
        "platform_unbranded_visibility": "Visibilidade sem marca",
        "platform_official_cite": "Taxa de citação do site oficial",
        "platform_competitor_mentions": "Menções de concorrentes",
        "platform_samples_mentioned": "amostras mencionadas",
        "platform_unbranded_samples": "amostras sem marca",
        "platform_cited_official": "citações do site oficial",
        "platform_low_competitor": "Baixa participação de concorrentes",
        "platform_footer": "As métricas da plataforma vêm das amostras de respostas de IA desta rodada; a visibilidade sem marca é a métrica-chave pré-conversão.",
        "platform_pending": "Próxima rodada",
        "platform_pending_sub": "Pendente",
        "platform_untested_note": "Nota: {name} não foi testado de forma independente nesta rodada; não interprete itens pendentes como desempenho zero.",
        "platform_competitive_strength": "Baixa participação de concorrentes {pct}",
        "meta_per_platform_prompts": "{count} prompts por plataforma",
        "meta_per_platform_prompts_partial": "Planejados {planned} prompts por plataforma (cobertura real incompleta)",
        "compare_unbranded": "Visibilidade sem marca",
        "compare_branded": "Visibilidade da marca",
        "compare_competitor_inverse": "Baixa participação de concorrentes",
        "compare_pending": "Pendente — próxima rodada",
        "cover_platforms_and_more": "{joined} e {count} plataformas",
        "cover_platforms_count_only": "{count} principais plataformas de IA",
        "funnel_seg_complete": "Totalmente visível",
        "funnel_seg_partial": "Parcialmente visível",
        "funnel_seg_brand_absent": "Marca ausente",
        "funnel_seg_mine": "Marca-alvo presente",
        "funnel_seg_comp": "Concorrente presente",
        "funnel_seg_all_blank": "Todos ausentes",
        "vs_label": "vs",
        "status_proxy": "Evidência proxy",
        "status_mixed": "Evidência mista",
        "status_not_tested": "Não testado nesta rodada",
        "status_not_independent": "Não testado de forma independente",
        "status_unavailable": "Indisponível",
        "status_failed": "Falha na coleta",
        "status_blocked": "Rastreamento bloqueado",
        "section_02_no": "SECTION 01 · DISTRIBUIÇÃO TOP",
        "section_02_title": "Onde {brand_name} aparece em {total_samples} amostras de respostas de IA",
        "section_02_desc": "Após classificar as amostras por presença da marca, citação do site oficial e tomada por concorrentes, a principal lacuna não é a precisão do reconhecimento da marca, e sim se a marca consegue entrar nas listas de recomendação no topo do funil (cenários sem marca).",
        "section_02_card_title": "Visão geral da distribuição das amostras",
        "section_02_card_note": "Dois grupos de cenários lado a lado: consultas com marca ({branded_total}) e consultas sem marca ({unbranded_total}); cada linha é normalizada a 100% — passe o rato para ver percentuais.",
        "legend_visible": "Visível",
        "legend_improve": "Precisa melhorar / concorrente",
        "legend_absent": "Ausente",
        "scenario_card_title": "Detalhamento por cenário",
        "scenario_card_note": "Bases estatísticas diferentes: as linhas com marca são atributos sobrepostos; as linhas sem marca são uma partição MECE (três segmentos somam {unbranded_total}).",
        "scenario_group_branded": "Utilizador nomeou a marca · consultas com marca {total}",
        "scenario_group_unbranded": "Utilizador não nomeou a marca · consultas sem marca {total}",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · Pré-conversão",
        "scenario_visibility_mix": "Mix de visibilidade",
        "scenario_children_note": "Visibilidade e citação do site oficial nas perguntas com marca",
        "scenario_unbranded_gap_note": "Concorrente {comp_pct}% + totalmente ausente {blank_pct}% = {absent_pct}% fora da recomendação. Esta é a lacuna pré-conversão.",
        "scenario_recognized": "Reconhecida",
        "scenario_not_recognized": "Não reconhecida",
        "scenario_cited": "Site oficial citado",
        "scenario_not_cited": "Site oficial não citado",
        "scenario_mine": "Marca-alvo presente",
        "scenario_comp_takeover": "Ausente · tomada por concorrente",
        "scenario_all_blank": "Ausente · tudo em branco",
        "scenario_read_note": "Consultas sem marca são o funil pré-conversão. Quando ausente (concorrente {comp} + em branco {blank} = {absent}), os concorrentes são recomendados primeiro. Baixa citação do site oficial {cited}/{branded_total} em consultas com marca significa que a IA conhece a marca, mas raramente linka de volta.",
        "section_03_no": "SECTION 03 · SENTIMENTO",
        "section_03_title": "Como a IA fala de {brand_name} — positivo ou negativo",
        "section_03_desc": "Cada resposta de IA é classificada (positiva / neutra / negativa) quando {brand_name} é mencionada. Menor participação negativa é mais seguro; alta participação neutra significa mencionada, mas sem endosso.",
        "senti_overall_title": "Mix geral de sentimento",
        "senti_overall_note": "Participação de todas as {total} respostas após classificação de sentimento por resposta.",
        "senti_platform_title": "Sentimento por plataforma",
        "senti_platform_note": "Mesma metodologia dividida por plataforma testada para comparar consistência.",
        "senti_positive": "Positivo",
        "senti_neutral": "Neutro",
        "senti_negative": "Negativo",
        "senti_stat_line": "{label} · {count} respostas",
        "senti_plat_counts": "pos {pos} · neu {neu} · neg {neg}",
        "senti_insight_with_data": "Em {total} respostas de IA, {pos} positivas ({pos_pct}) e apenas {neg} negativas ({neg_pct}) — pouco risco reputacional quando a IA discute {brand_name}. A oportunidade está nos {neu_pct} neutros: mencionada sem endosso. Converter neutro em respaldo positivo é o salto da visibilidade para a recomendação.",
        "senti_insight_no_data": "Nenhuma amostra de sentimento classificável nesta rodada.",
        "senti_cloud_title": "Nuvem de palavras de sentimento",
        "senti_cloud_badge": "Extração de frases por LLM",
        "senti_cloud_note": "Frases extraídas de respostas positivas/neutras/negativas que mencionam {brand_name}; tipo maior significa mais respostas.",
        "senti_cloud_tab_positive": "Palavras-chave positivas",
        "senti_cloud_tab_neutral": "Palavras-chave neutras",
        "senti_cloud_tab_negative": "Palavras-chave negativas",
        "senti_cloud_tooltip_count": "Visto em {count} respostas",
        "senti_cloud_empty_generic": "Ainda sem palavras-chave para esta polaridade.",
        "senti_cloud_empty_missing": "O artefato de palavras-chave de sentimento não foi produzido nesta rodada.",
        "senti_cloud_empty_no_answers": "Poucas respostas com menção para extrair palavras-chave.",
        "senti_cloud_empty_no_phrases": "Existem amostras de sentimento, mas nenhuma frase exibível foi extraída.",
        "section_04_no": "SECTION 04 · DESEMPENHO POR PLATAFORMA",
        "section_04_title": "Diferenças de visibilidade entre os principais modelos de IA",
        "section_04_desc": "Plataformas testadas compartilham o mesmo conjunto de prompts; plataformas não testadas permanecem marcadas como pendentes — não pontuadas como zero.",
        "plat_compare_title": "Comparação de visibilidade por plataforma",
        "plat_compare_note": "Três métricas de visibilidade (0–100%, quanto maior melhor) por plataforma; a taxa de citação do site oficial está nos cards de plataforma acima.",
        "plat_matrix_title": "Matriz de resistência à recomendação",
        "plat_matrix_note": "X = visibilidade sem marca (direita é melhor); Y = participação de concorrentes (menor é melhor); tamanho da bolha = contagem de amostras. Azul inferior direito = ideal; superior esquerdo = alto risco.",
        "section_05_no": "SECTION 05 · AUTORIDADE DE FONTES",
        "section_05_title": "Que tipos de fonte a IA pode citar sobre nós",
        "section_05_desc": "Azul claro = baseline cross-categoria; roxo = estado atual; estimativas proxy estão rotuladas.",
        "auth_radar_title": "Radar de credibilidade da marca",
        "auth_radar_note": "Cinco dimensões medem a pegada de conteúdo autoritativo: fonte oficial = DA + citação por IA (6:4, medido); enciclopédia / media / comunidade / profundidade são direcionais.",
        "auth_dim_title": "Interpretação das dimensões",
        "auth_dim_note": "As pontuações refletem quanto conteúdo credível a IA encontra por canal (0–100 relativo).",
        "auth_focus_note": "Foque em: enciclopédia, mídia e comunidade — sinais principais de validação externa.",
        "legend_radar_industry": "Baseline cross-categoria",
        "legend_radar_current": "{brand_name} atual",
        "section_06_no": "SECTION 06 · PRESENÇA POR CANAL",
        "section_06_title": "Onde a IA encontra conteúdo sobre nós",
        "section_06_desc": "Mesma escala 0–100 do radar: site / enciclopédia / mídia mapeiam para os eixos; YouTube e Reddit dividem o eixo comunidade (comunidade = média deles). Quanto maior, melhor.",
        "src_bar_title": "Comparação de pontuação por canal",
        "src_bar_note": "Roxo = {brand_name} atual; cinza = nível de referência de pares (direcional).",
        "legend_peer_ref": "Referência de pares",
        "section_07_no": "SECTION 07 · GAP DE CONCORRENTES",
        "section_07_title": "Resistência à recomendação e pressão de concorrentes",
        "section_07_desc": "X = visibilidade de IA sem marca (% medido); Y = participação de respostas que citam a marca como fonte (%). Pontos ocos = proxy a partir da autoridade do domínio quando a participação de citação não está disponível.",
        "comp_bubble_title": "Presença de concorrentes nas respostas de IA",
        "comp_bubble_note": "X = frequência de menção em consultas sem marca (medido); Y = participação de citação como fonte. Oco = estimativa proxy.",
        "dr_bar_title": "Comparação de autoridade do domínio",
        "dr_bar_note": "A autoridade do domínio reflete quantos sites externos linkam para o domínio; pontuações mais altas correlacionam com confiança da IA. Máx. 100.",
        "search_dr_row": "DA {dr} · Organic {organic} · Keywords {keywords}",
        "section_08_no": "SECTION 08 · RANKING DE CONCORRENTES",
        "section_08_title": "Quem a IA menciona mais na categoria",
        "section_08_desc": "Classifique {brand_name} contra concorrentes por contagens reais de menção em {denom} respostas de IA de categoria (sem marca). Ranking mais alto = melhor slot de recomendação pré-decisão.",
        "rank_card_title": "Ranking de menções na categoria",
        "rank_card_note": "Destaque roxo = {brand_name}; comprimento da barra = frequência relativa de menção; à direita = contagem absoluta e participação das consultas sem marca.",
        "rank_card_badge": "{denom} consultas sem marca",
        "rank_you_tag": "Esta marca",
        "rank_focus_tag": "Foco",
        "rank_count_line": "{mentions} menções · {rate}",
        "rank_phrase": "posição #{rank}",
        "rank_not_listed": "fora do ranking",
        "rank_headline_ranked": "Entre {total_brands} marcas na categoria, {brand_name} fica em <b>{rank_phrase}</b> por frequência de menção em consultas de IA sem marca.",
        "rank_headline_unranked": "Entre {total_brands} marcas na categoria, {brand_name} ainda não entrou no ranking de menções em consultas de IA sem marca.",
        "focus_comp_kicker": "Concorrentes em foco",
        "focus_comp_title": "Concorrentes observados neste relatório",
        "focus_comp_note": "Da configuração do relatório (mais preciso que a descoberta automática). As menções abaixo foram medidas na amostra sem marca desta rodada; ausência significa não nomeado na amostra, não “não é concorrente”.",
        "focus_comp_mentions": "{count} menções sem marca",
        "focus_comp_rank": "posição #{rank}",
        "focus_comp_absent": "não nomeado nesta rodada",
        "section_09_no": "SECTION 09 · DIAGNÓSTICO POR CANAL",
        "section_09_title": "Onde estão as lacunas e o que corrigir rápido",
        "section_09_desc": "Site oficial primeiro, depois pegada off-site / social. Azul = medido OK; amarelo = precisa melhorar; vermelho = lacuna clara; cinza = não testado de forma independente nesta rodada.",
        "channel_group_official_kicker": "01 · On-site",
        "channel_group_official_title": "Site oficial",
        "channel_group_official_note": "Legibilidade por máquinas do site: marcação estruturada, limites semânticos, hierarquia de títulos, definição em uma linha, dicas de rastreamento e densidade citável no corpo/páginas internas.",
        "channel_group_offsite_kicker": "02 · Off-site",
        "channel_group_offsite_title": "Backlinks / social",
        "channel_group_offsite_note": "Pegada off-site: totais de backlinks, volume de busca em vídeo/comunidade, presença em enciclopédia. Contagens sociais vêm de busca por palavra-chave e podem não igualar conteúdo verificado relacionado à marca.",
        "section_10_no": "SECTION 10 · CAUSAS-RAIZ",
        "section_10_title": "Por que a IA ainda não recomenda ativamente {brand_name}",
        "section_11_no": "SECTION 11 · RECOMENDAÇÕES",
        "section_11_title": "Por onde começar e como",
        "section_11_desc": "O trabalho no site oficial vem sempre primeiro: estrutura legível por máquinas e páginas citáveis antes de off-site/social. Ordenado por esforço e impacto esperado.",
        "recs_col_priority": "Prioridade",
        "recs_col_action": "Ação",
        "recs_col_why": "Por que isto",
        "recs_col_metric": "Mudança esperada de métrica",
        "recs_col_effort": "Faixa de esforço",
        "recs_site_markup_hint": "JSON-LD Schema · HTML semântico · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "Páginas de categoria · guias de comparação/compra · secções H2 claras · blocos de fatos citáveis",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        "section_12_no": "SECTION 12 · FONTES CITADAS",
        "section_12_title": "Quais sites e artigos a IA realmente citou",
        "section_12_desc": "Conta citações que aparecem na resposta (não listagens de busca). Ordenado por frequência de domínio; mostra os 30 principais. Se o site oficial ficar fora do top 30, aparece no final. Abra a linha para ver URLs e contagens.",
        "cite_rank_tab_branded": "Consultas com marca",
        "cite_rank_tab_unbranded": "Consultas sem marca",
        "cite_rank_tab_meta": "{answers} respostas · {citations} citações",
        "cite_rank_empty": "Nenhuma citação aplicada foi capturada neste conjunto",
        "cite_rank_count": "{count}×",
        "cite_rank_official": "Site oficial",
        "cite_rank_urls_n": "{count} artigos",
        "cite_rank_truncated": "Exibindo os {n} principais de {total} domínios",
        "cite_rank_unlisted": "Fora do ranking",
        "section_13_no": "SECTION 12 · PROMPTS E RESPOSTAS",
        "section_13_title": "Abra qualquer linha para inspecionar o que a IA realmente respondeu",
        "qa_group_branded": "Prompt com marca",
        "qa_group_unbranded": "Prompt sem marca",
        "qa_group_default": "Consulta",
        "qa_dot_mentioned": "Mencionada",
        "qa_dot_not_mentioned": "Não mencionada",
        "qa_badge_mentioned": "Marca mencionada",
        "qa_badge_not_mentioned": "Não mencionada",
        "qa_badge_cite_official": "Site oficial citado",
        "qa_badge_cite_missing": "Site oficial não citado",
        "qa_badge_partial_visible": "Parcialmente visível",
        "qa_badge_fully_visible": "Totalmente visível",
        "qa_dots_legend": "Pontos = se cada plataforma mencionou a marca (azul = sim, cinza = não)",
        "qa_comp_mentioned": "Concorrentes na mesma resposta: {names}",
        "qa_queried_as": "Prompt real: {text}",
        "qa_no_excerpt": "(Resposta completa não armazenada — frequentemente falha de coleta ou relatório legado sem corpo da resposta.)",
        "qa_evidence": "Base da classificação:",
        "qa_evidence_corrected": "Nome da marca não encontrado no corpo da resposta; corrigido para não mencionada",
        "qa_evidence_corrected_original": "Nome da marca não encontrado no corpo da resposta; corrigido para não mencionada. Base original: {evidence}",
        "qa_sources": "Fontes",
        "qa_source_cited": "Visto na resposta",
        "qa_source_listed": "Fonte listada",
        "qa_no_sources": "Nenhuma fonte capturada para esta resposta",
        "qa_expand_answer": "Expandir resposta completa",
        "qa_collapse_answer": "Recolher resposta",
        "qa_open_modal": "Ver detalhes",
        "qa_modal_close": "Fechar",
        "qa_modal_question": "Prompt",
        "qa_modal_actual_prompt": "Prompt real da plataforma",
        "qa_modal_status": "Tags de status",
        "qa_modal_ranking": "Ordem de marca / concorrente na resposta",
        "qa_modal_competitors": "Concorrentes mencionados",
        "qa_no_platform": "Sem respostas de plataforma para este prompt",
        "qa_no_competitors": "Nenhuma menção de concorrente detectada",
        "qa_no_rank": "Nenhum sinal de ranking disponível",
        "qa_rank_absent": "Ausente",
        "qa_section_note": "Clique em qualquer prompt para abrir um modal com abas por plataforma, respostas renderizadas em Markdown, fontes, notas de classificação e ordem de menção.",
        "boundary_title": "Notas sobre os dados",
        "boundary_tested": "Testado nesta rodada:",
        "boundary_not_tested": "Não testado de forma independente nesta rodada",
        "boundary_not_tested_note": "(não é pontuação zero — pode ser testado na próxima rodada)",
        "boundary_proxy": "Estimativas proxy",
        "boundary_proxy_note": "(direcional, não medição precisa)",
        "boundary_scope": "Os achados refletem o escopo de prompts desta rodada, não todos os cenários de busca possíveis.",
        "boundary_legal": "Apenas para avaliação de status e medição da próxima rodada — não constitui compromisso de implementação, cotação ou cláusula contratual.",
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "Marca-alvo",
        "rivals_fallback": "concorrentes",
        "industry_mean": "Média do setor (direcional)",
        "chart_tooltip_seg": "{label}: {pct}% ({count}/{total})",
        "chart_tooltip_plat_bubble": "{name}: visibilidade sem marca {x}%, participação de concorrentes {y}%, n={n}",
        "chart_tooltip_comp_scatter": "{name}: visibilidade {x}%, participação de fontes {y}%{tag}",
        "chart_tooltip_comp_proxy": " (est.)",
        "fallback_section_01_desc": "A IA reconhece {brand_name} em {branded_mentioned}/{branded_total} respostas com marca nomeada ({branded_rate}%). Em perguntas de categoria pré-decisão, {brand_name} aparece em {unbranded_mentioned}/{unbranded_total} casos; concorrentes ocupam o slot {takeover} vezes.",
        "fallback_main_insight": "Esta rodada mostra <b>reconhecimento com marca de {branded_rate}%</b> para {brand_name}, mas ausência em {unbranded_absent}/{unbranded_total} cenários de decisão sem marca, incluindo {takeover} slots de recomendação ocupados por {rivals}. Priorize evidências que melhorem a descoberta sem marca e depois reteste com o mesmo conjunto de prompts.",
        "fallback_section_05_insight": "Concorrentes pontuam mais em fontes externas porque têm citações geradas por utilizadores mais densas no YouTube, Reddit e media do setor — sinais em que a IA confia para recomendações sem marca. O conteúdo próprio de {brand_name} está bem, mas a densidade de citação de terceiros é menor. Barras cinza são não testadas, não zero; comece com Schema, Meta e llms.txt e depois construa citações externas.",
        "fallback_section_06_dr_note": "O DA de {brand_name} é {dr}; concorrentes variam {comp_min}–{comp_max} — um gap modesto. DA mede volume de backlinks, não relevância tópica. Concorrentes têm citações de nicho mais densas em media e comunidades, o que pesa mais para recomendações de IA do que DA bruto. Busque citações de autoridade tópica, não só DA.",
        "fallback_section_07_insight": "{brand_name} tem ativos maduros — site e reconhecimento de marca — mas a maioria foi feita para humanos e buscadores, não para a lógica de recomendação da IA. Concorrentes são mais estruturados e citados externamente, então a IA os prefere em consultas sem marca. Reencode ativos existentes para IA; o atraso reforça a vantagem de corpus dos concorrentes. Canais cinza não foram testados de forma independente.",
        "fallback_section_08_desc": "Três lacunas empilhadas deslocam {brand_name} nas recomendações de IA: limites de produto pouco claros → sem páginas citáveis em consultas sem marca → concorrentes com sinais mais fortes vencem o slot. As camadas se amplificam mutuamente.",
        "fallback_section_09_insight": "O site oficial é a primeira fonte confiável da IA para {brand_name} — continue melhorando, não é trabalho único. P0 cobre duas frentes: (1) estrutura legível por máquinas (Schema, tags semânticas, H1/H2, Meta, llms.txt); (2) conteúdo citável e páginas de entrada de categoria. Off-site/social amplificam o trabalho on-site e não devem vir primeiro. Vincule cada iniciativa a métricas de IA retestáveis.",
        "fallback_root_expression": "O conteúdo do site de {brand} pode parecer completo para humanos, mas estrutura fraca ou secções pouco citáveis forçam a IA a montar o posicionamento a partir de parágrafos dispersos — menos eficiente que concorrentes bem estruturados, e visível em recomendações sem marca ignoradas.<br/><br/>Evidência: {evidence}.",
        "fallback_root_supply": "{brand} carece de páginas que respondam perguntas de categoria pré-decisão — comparações, seleção e diferenciação de concorrentes que a IA possa citar. Concorrentes cobrem esses nós semânticos de forma mais densa.<br/><br/>Evidência: {evidence}.",
        "fallback_root_distribution": "Este é o primeiro portão de aquisição: compradores perguntam à IA antes de escolher um fornecedor. Em cenários sem marca, {brand} frequentemente está ausente e concorrentes ocupam o slot de recomendação. Cada ausência encaminha um prospecto aos rivais.<br/><br/>Evidência: {evidence}.",
        "ch_desc_backlinks": "{desc} Volume e qualidade de backlinks ajudam a IA a julgar se recomenda uma marca. Próxima rodada: verifique media, sites de avaliação e diretórios do setor.",
        "ch_desc_youtube_tested": "{desc} A IA usa vídeo (reviews, tutoriais, unboxing) para descrever produtos; mais vídeo visível da marca gera copy de IA mais específica.",
        "ch_desc_youtube_untested": "YouTube não foi testado de forma independente nesta rodada. A IA usa conteúdo em vídeo para respostas de produto; verifique a pegada de vídeo da marca na próxima rodada.",
        "ch_desc_reddit_tested": "{desc} A IA considera Reddit e fóruns para feedback de utilizadores — elogios e reclamações — afetando se adiciona ressalvas ou recomenda alternativas.",
        "ch_desc_reddit_untested": "O sentimento da comunidade não foi testado de forma independente. Reddit e fóruns moldam como a IA enquadra feedback e recomendações.",
        "ch_desc_wikipedia": "{desc} A Wikipedia é uma fonte comum de desambiguação. Sem artigo, aumenta o risco de confusão quando nomes de marca colidem.",
        "ch_desc_schema": "{desc} Schema torna as páginas legíveis por máquinas para a IA — marca, categoria, público. Sem ele, a IA adivinha pelo corpo do texto. Baixo custo, alta prioridade.",
        "ch_desc_semantic": "{desc} Sem títulos e secções claros, a IA tem dificuldade de analisar a página e pode pegar frases de concorrentes. Corrigível on-site.",
        "ch_desc_meta": "{desc} A meta description costuma ser a primeira fonte para resumos de marca pela IA. Meta vazia força copy improvisada e mais fraca.",
        "ch_desc_llms": "{desc} llms.txt é uma convenção emergente para dizer aos crawlers quais páginas importam. Combine com Schema e Meta para melhorar mais rápido a legibilidade por máquinas.",
    },
    "fr": {
        "report_title_suffix": "Rapport de diagnostic de performance des modèles d’IA",
        "report_sub": "Sur la base de {total_samples} échantillons de réponses sur {platform_phrase}, combinés aux signaux structurels du site officiel, aux profils de trafic de recherche et aux référentiels concurrentiels, ce rapport évalue la mention, la citation et la présence en recommandation de {brand_name} dans la recherche générative et les moteurs de réponses.",
        "report_audience": "Pour les décideurs marque, marketing et business.",
        "meta_subject": "Objet",
        "meta_business": "Périmètre métier",
        "meta_platforms": "Plateformes échantillonnées",
        "meta_date": "Date du rapport",
        "meta_report_code": "Code du rapport",
        "section_01_no": "SECTION 02 · MÉTRIQUES CLÉS",
        "section_01_title": "Quatre chiffres pour situer le contexte",
        "kpi_unbranded": "Présence sans marque",
        "kpi_unbranded_note": "Nombre de fois où {brand_name} apparaît lorsque les acheteurs posent une question sans nommer de marque.",
        "kpi_branded": "Reconnaissance avec marque",
        "kpi_branded_note": "Lorsque les utilisateurs nomment la marque, la plupart des réponses la reconnaissent — les actifs existent mais doivent être exposés plus tôt.",
        "kpi_competitor": "Réponses occupées par des concurrents",
        "kpi_competitor_note": "Réponses où {brand_name} est absent et au moins un concurrent apparaît ; chaque réponse compte une fois ({rate}% des scénarios d’absence).",
        "kpi_dr": "Score d’autorité de domaine",
        "kpi_dr_note": "Les concurrents marquent {comp_min}–{comp_max}. Des scores plus élevés corrèlent avec la préférence de citation par l’IA.",
        "status_pending": "En attente",
        "status_tested": "Mesuré",
        "status_detected": "Détecté",
        "status_partial": "Couverture partielle",
        "status_critical_gap": "Écart critique",
        "status_not_deployed": "Non déployé",
        "insight_label": "Insight",
        "platform_brand_visibility": "Visibilité de la marque",
        "platform_unbranded_visibility": "Visibilité sans marque",
        "platform_official_cite": "Taux de citation du site officiel",
        "platform_competitor_mentions": "Mentions de concurrents",
        "platform_samples_mentioned": "échantillons mentionnés",
        "platform_unbranded_samples": "échantillons sans marque",
        "platform_cited_official": "citations du site officiel",
        "platform_low_competitor": "Faible part concurrentielle",
        "platform_footer": "Les métriques plateforme proviennent des échantillons de réponses IA de cette vague ; la visibilité sans marque est la métrique clé pré-conversion.",
        "platform_pending": "Prochaine vague",
        "platform_pending_sub": "En attente",
        "platform_untested_note": "Note : {name} n’a pas été testé indépendamment sur cette vague ; n’interprétez pas les éléments en attente comme une performance nulle.",
        "platform_competitive_strength": "Faible part concurrentielle {pct}",
        "meta_per_platform_prompts": "{count} prompts par plateforme",
        "meta_per_platform_prompts_partial": "{planned} prompts prévus par plateforme (couverture réelle incomplète)",
        "compare_unbranded": "Visibilité sans marque",
        "compare_branded": "Visibilité de la marque",
        "compare_competitor_inverse": "Faible part concurrentielle",
        "compare_pending": "En attente — prochaine vague",
        "cover_platforms_and_more": "{joined} et {count} plateformes",
        "cover_platforms_count_only": "{count} grandes plateformes d’IA",
        "funnel_seg_complete": "Entièrement visible",
        "funnel_seg_partial": "Partiellement visible",
        "funnel_seg_brand_absent": "Marque absente",
        "funnel_seg_mine": "Cible présente",
        "funnel_seg_comp": "Concurrent présent",
        "funnel_seg_all_blank": "Tous absents",
        "vs_label": "vs",
        "status_proxy": "Preuve proxy",
        "status_mixed": "Preuve mixte",
        "status_not_tested": "Non testé cette vague",
        "status_not_independent": "Non testé indépendamment",
        "status_unavailable": "Indisponible",
        "status_failed": "Échec de collecte",
        "status_blocked": "Crawl bloqué",
        "section_02_no": "SECTION 01 · DISTRIBUTION TOP",
        "section_02_title": "Où {brand_name} apparaît parmi {total_samples} échantillons de réponses IA",
        "section_02_desc": "Après classification des échantillons par présence de marque, citation du site officiel et reprise concurrentielle, l’écart principal n’est pas la précision de reconnaissance de marque, mais la capacité à entrer dans les listes de recommandation en haut de funnel (scénarios sans marque).",
        "section_02_card_title": "Vue d’ensemble de la distribution des échantillons",
        "section_02_card_note": "Deux groupes de scénarios côte à côte : requêtes de marque ({branded_total}) et requêtes sans marque ({unbranded_total}) ; chaque ligne est normalisée à 100 % — survolez pour les pourcentages.",
        "legend_visible": "Visible",
        "legend_improve": "À améliorer / concurrent",
        "legend_absent": "Absent",
        "scenario_card_title": "Détail par scénario",
        "scenario_card_note": "Bases statistiques différentes : les lignes de marque sont des attributs qui se chevauchent ; les lignes sans marque forment une partition MECE (trois segments totalisent {unbranded_total}).",
        "scenario_group_branded": "L’utilisateur a nommé la marque · requêtes de marque {total}",
        "scenario_group_unbranded": "L’utilisateur n’a pas nommé la marque · requêtes sans marque {total}",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · Pré-conversion",
        "scenario_visibility_mix": "Mix de visibilité",
        "scenario_children_note": "Visibilité et citation du site officiel dans les questions de marque",
        "scenario_unbranded_gap_note": "Concurrent {comp_pct} % + absence totale {blank_pct} % = {absent_pct} % hors recommandation. C’est l’écart pré-conversion.",
        "scenario_recognized": "Reconnue",
        "scenario_not_recognized": "Non reconnue",
        "scenario_cited": "Site officiel cité",
        "scenario_not_cited": "Site officiel non cité",
        "scenario_mine": "Cible présente",
        "scenario_comp_takeover": "Absent · reprise concurrentielle",
        "scenario_all_blank": "Absent · tout vide",
        "scenario_read_note": "Les requêtes sans marque sont le funnel pré-conversion. En cas d’absence (concurrent {comp} + vide {blank} = {absent}), les concurrents sont recommandés en premier. Une faible citation du site officiel {cited}/{branded_total} sur les requêtes de marque signifie que l’IA connaît la marque mais renvoie rarement vers le site.",
        "section_03_no": "SECTION 03 · SENTIMENT",
        "section_03_title": "Comment l’IA parle de {brand_name} — positif ou négatif",
        "section_03_desc": "Chaque réponse IA est classée (positive / neutre / négative) lorsque {brand_name} est mentionné. Une part négative plus faible est plus sûre ; une part neutre élevée signifie mentionné sans endorsement.",
        "senti_overall_title": "Mix de sentiment global",
        "senti_overall_note": "Part de l’ensemble des {total} réponses après classification du sentiment réponse par réponse.",
        "senti_platform_title": "Sentiment par plateforme",
        "senti_platform_note": "Même méthodologie découpée par plateforme testée pour comparer la cohérence.",
        "senti_positive": "Positif",
        "senti_neutral": "Neutre",
        "senti_negative": "Négatif",
        "senti_stat_line": "{label} · {count} réponses",
        "senti_plat_counts": "pos {pos} · neu {neu} · neg {neg}",
        "senti_insight_with_data": "Sur {total} réponses IA, {pos} positives ({pos_pct}) et seulement {neg} négatives ({neg_pct}) — peu de risque réputationnel lorsque l’IA parle de {brand_name}. L’opportunité est dans les {neu_pct} neutres : mentionnés sans endorsement. Convertir le neutre en soutien positif est le saut de la visibilité à la recommandation.",
        "senti_insight_no_data": "Aucun échantillon de sentiment classifiable sur cette vague.",
        "senti_cloud_title": "Nuage de mots du sentiment",
        "senti_cloud_badge": "Extraction de phrases LLM",
        "senti_cloud_note": "Phrases extraites des réponses positives/neutres/négatives qui mentionnent {brand_name} ; une taille plus grande signifie plus de réponses.",
        "senti_cloud_tab_positive": "Mots-clés positifs",
        "senti_cloud_tab_neutral": "Mots-clés neutres",
        "senti_cloud_tab_negative": "Mots-clés négatifs",
        "senti_cloud_tooltip_count": "Vu dans {count} réponses",
        "senti_cloud_empty_generic": "Pas encore de mots-clés pour cette polarité.",
        "senti_cloud_empty_missing": "L’artefact de mots-clés de sentiment n’a pas été produit sur cette vague.",
        "senti_cloud_empty_no_answers": "Trop peu de réponses mentionnées pour extraire des mots-clés.",
        "senti_cloud_empty_no_phrases": "Des échantillons de sentiment existent, mais aucune phrase affichable n’a été extraite.",
        "section_04_no": "SECTION 04 · PERFORMANCE PLATEFORME",
        "section_04_title": "Écarts de visibilité entre les principaux modèles d’IA",
        "section_04_desc": "Les plateformes testées partagent le même jeu de prompts ; les plateformes non testées restent marquées en attente — non scorées à zéro.",
        "plat_compare_title": "Comparaison de visibilité par plateforme",
        "plat_compare_note": "Trois métriques de visibilité (0–100 %, plus c’est haut mieux c’est) par plateforme ; le taux de citation du site officiel figure sur les cartes plateforme ci-dessus.",
        "plat_matrix_title": "Matrice de résistance à la recommandation",
        "plat_matrix_note": "X = visibilité sans marque (à droite = mieux) ; Y = part concurrentielle (plus bas = mieux) ; taille de bulle = nombre d’échantillons. Bleu bas-droite = idéal ; haut-gauche = risque élevé.",
        "section_05_no": "SECTION 05 · AUTORITÉ DES SOURCES",
        "section_05_title": "Quels types de sources l’IA peut citer à notre sujet",
        "section_05_desc": "Bleu clair = baseline cross-catégorie ; violet = état actuel ; les estimations proxy sont étiquetées.",
        "auth_radar_title": "Radar de crédibilité de la marque",
        "auth_radar_note": "Cinq dimensions mesurent l’empreinte de contenu autoritatif : source officielle = DA + citation IA (6:4, mesuré) ; encyclopédie / médias / communauté / profondeur sont directionnels.",
        "auth_dim_title": "Interprétation des dimensions",
        "auth_dim_note": "Les scores reflètent combien de contenu crédible l’IA trouve par canal (0–100 relatif).",
        "auth_focus_note": "Focus : encyclopédie, médias et communauté — signaux principaux de validation externe.",
        "legend_radar_industry": "Baseline cross-catégorie",
        "legend_radar_current": "{brand_name} actuel",
        "section_06_no": "SECTION 06 · PRÉSENCE PAR CANAL",
        "section_06_title": "Où l’IA trouve du contenu à notre sujet",
        "section_06_desc": "Même échelle 0–100 que le radar : site / encyclopédie / médias correspondent aux axes ; YouTube et Reddit scindent l’axe communauté (communauté = leur moyenne). Plus haut = mieux.",
        "src_bar_title": "Comparaison des scores par canal",
        "src_bar_note": "Violet = {brand_name} actuel ; gris = niveau de référence pairs (directionnel).",
        "legend_peer_ref": "Référence pairs",
        "section_07_no": "SECTION 07 · ÉCART CONCURRENTIEL",
        "section_07_title": "Résistance à la recommandation et pression concurrentielle",
        "section_07_desc": "X = visibilité IA sans marque (% mesuré) ; Y = part des réponses citant la marque comme source (%). Points creux = proxy à partir de l’autorité de domaine lorsque la part de citation est indisponible.",
        "comp_bubble_title": "Présence concurrentielle dans les réponses IA",
        "comp_bubble_note": "X = fréquence de mention sur requêtes sans marque (mesuré) ; Y = part de citation comme source. Creux = estimation proxy.",
        "dr_bar_title": "Comparaison d’autorité de domaine",
        "dr_bar_note": "L’autorité de domaine reflète combien de sites externes pointent vers le domaine ; des scores plus élevés corrèlent avec la confiance de l’IA. Max 100.",
        "search_dr_row": "DA {dr} · Organic {organic} · Keywords {keywords}",
        "section_08_no": "SECTION 08 · CLASSEMENT CONCURRENTIEL",
        "section_08_title": "Qui l’IA mentionne le plus dans la catégorie",
        "section_08_desc": "Classez {brand_name} face aux concurrents selon les comptes de mentions réels dans {denom} réponses IA de catégorie (sans marque). Rang plus élevé = meilleur créneau de recommandation pré-décision.",
        "rank_card_title": "Classement des mentions de catégorie",
        "rank_card_note": "Surbrillance violette = {brand_name} ; longueur de barre = fréquence relative de mention ; à droite = compte absolu et part des requêtes sans marque.",
        "rank_card_badge": "{denom} requêtes sans marque",
        "rank_you_tag": "Cette marque",
        "rank_focus_tag": "Focus",
        "rank_count_line": "{mentions} mentions · {rate}",
        "rank_phrase": "rang #{rank}",
        "rank_not_listed": "non classé",
        "rank_headline_ranked": "Parmi {total_brands} marques de la catégorie, {brand_name} est <b>{rank_phrase}</b> en fréquence de mention sur les requêtes IA sans marque.",
        "rank_headline_unranked": "Parmi {total_brands} marques de la catégorie, {brand_name} n’est pas encore entré dans le classement des mentions sur les requêtes IA sans marque.",
        "focus_comp_kicker": "Concurrents suivis",
        "focus_comp_title": "Concurrents observés pour ce rapport",
        "focus_comp_note": "Issus de la configuration du rapport (plus précis que la découverte auto). Les mentions ci-dessous sont mesurées sur l’échantillon sans marque de cette vague ; l’absence signifie non nommé dans l’échantillon, pas « pas un concurrent ».",
        "focus_comp_mentions": "{count} mentions sans marque",
        "focus_comp_rank": "rang #{rank}",
        "focus_comp_absent": "non nommé cette vague",
        "section_09_no": "SECTION 09 · DIAGNOSTIC PAR CANAL",
        "section_09_title": "Où sont les écarts et quoi corriger vite",
        "section_09_desc": "Site officiel d’abord, puis empreinte off-site / sociale. Bleu = mesuré OK ; jaune = à améliorer ; rouge = écart clair ; gris = non testé indépendamment cette vague.",
        "channel_group_official_kicker": "01 · On-site",
        "channel_group_official_title": "Site officiel",
        "channel_group_official_note": "Lisibilité machine du site : balisage structuré, frontières sémantiques, hiérarchie de titres, définition en une ligne, indices de crawl et densité citable du corps / pages internes.",
        "channel_group_offsite_kicker": "02 · Off-site",
        "channel_group_offsite_title": "Backlinks / social",
        "channel_group_offsite_note": "Empreinte off-site : totaux de backlinks, volume de recherche vidéo/communauté, présence encyclopédique. Les comptes sociaux viennent de recherches par mots-clés et peuvent ne pas égaler un contenu de marque vérifié.",
        "section_10_no": "SECTION 10 · CAUSES RACINES",
        "section_10_title": "Pourquoi l’IA ne recommande pas encore activement {brand_name}",
        "section_11_no": "SECTION 11 · RECOMMANDATIONS",
        "section_11_title": "Par où commencer et comment",
        "section_11_desc": "Le travail sur le site officiel passe toujours en premier : structure lisible par machine et pages citables avant off-site/social. Trié par effort et impact attendu.",
        "recs_col_priority": "Priorité",
        "recs_col_action": "Action",
        "recs_col_why": "Pourquoi ceci",
        "recs_col_metric": "Changement de métrique attendu",
        "recs_col_effort": "Bande d’effort",
        "recs_site_markup_hint": "JSON-LD Schema · HTML sémantique · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "Pages catégorie · guides comparaison/achat · sections H2 claires · blocs de faits citables",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        "section_12_no": "SECTION 12 · SOURCES CITÉES",
        "section_12_title": "Quels sites et articles l’IA a réellement cités",
        "section_12_desc": "Compte les citations présentes dans la réponse (pas les listes de recherche). Classé par fréquence de domaine ; affiche le top 30. Si le site officiel est hors du top 30, il est listé à la fin. Ouvrez une ligne pour voir les URL et les comptes.",
        "cite_rank_tab_branded": "Requêtes de marque",
        "cite_rank_tab_unbranded": "Requêtes sans marque",
        "cite_rank_tab_meta": "{answers} réponses · {citations} citations",
        "cite_rank_empty": "Aucune citation appliquée n’a été capturée pour cet ensemble",
        "cite_rank_count": "{count}×",
        "cite_rank_official": "Site officiel",
        "cite_rank_urls_n": "{count} articles",
        "cite_rank_truncated": "Affichage des {n} premiers domaines sur {total}",
        "cite_rank_unlisted": "Hors classement",
        "section_13_no": "SECTION 12 · PROMPTS & RÉPONSES",
        "section_13_title": "Ouvrez n’importe quelle ligne pour inspecter ce que l’IA a réellement répondu",
        "qa_group_branded": "Prompt de marque",
        "qa_group_unbranded": "Prompt sans marque",
        "qa_group_default": "Requête",
        "qa_dot_mentioned": "Mentionné",
        "qa_dot_not_mentioned": "Non mentionné",
        "qa_badge_mentioned": "Marque mentionnée",
        "qa_badge_not_mentioned": "Non mentionné",
        "qa_badge_cite_official": "Site officiel cité",
        "qa_badge_cite_missing": "Site officiel non cité",
        "qa_badge_partial_visible": "Partiellement visible",
        "qa_badge_fully_visible": "Entièrement visible",
        "qa_dots_legend": "Points = si chaque plateforme a mentionné la marque (bleu = oui, gris = non)",
        "qa_comp_mentioned": "Concurrents dans la même réponse : {names}",
        "qa_queried_as": "Prompt réel : {text}",
        "qa_no_excerpt": "(Réponse complète non stockée — souvent échec de collecte ou rapport legacy sans corps de réponse.)",
        "qa_evidence": "Base de classification :",
        "qa_evidence_corrected": "Nom de marque introuvable dans le corps de la réponse ; corrigé en non mentionné",
        "qa_evidence_corrected_original": "Nom de marque introuvable dans le corps de la réponse ; corrigé en non mentionné. Base d’origine : {evidence}",
        "qa_sources": "Sources",
        "qa_source_cited": "Vu dans la réponse",
        "qa_source_listed": "Source listée",
        "qa_no_sources": "Aucune source capturée pour cette réponse",
        "qa_expand_answer": "Développer la réponse complète",
        "qa_collapse_answer": "Réduire la réponse",
        "qa_open_modal": "Voir les détails",
        "qa_modal_close": "Fermer",
        "qa_modal_question": "Prompt",
        "qa_modal_actual_prompt": "Prompt réel de la plateforme",
        "qa_modal_status": "Tags de statut",
        "qa_modal_ranking": "Ordre marque / concurrent dans la réponse",
        "qa_modal_competitors": "Concurrents mentionnés",
        "qa_no_platform": "Aucune réponse plateforme pour ce prompt",
        "qa_no_competitors": "Aucune mention concurrentielle détectée",
        "qa_no_rank": "Aucun signal de classement disponible",
        "qa_rank_absent": "Absent",
        "qa_section_note": "Cliquez sur n’importe quel prompt pour ouvrir une modale avec onglets plateforme, réponses rendues en Markdown, sources, notes de classification et ordre de mention.",
        "boundary_title": "Notes sur les données",
        "boundary_tested": "Testé cette vague :",
        "boundary_not_tested": "Non testé indépendamment cette vague",
        "boundary_not_tested_note": "(ce n’est pas un score zéro — peut être testé à la prochaine vague)",
        "boundary_proxy": "Estimations proxy",
        "boundary_proxy_note": "(directionnel, pas une mesure précise)",
        "boundary_scope": "Les conclusions reflètent le périmètre de prompts de cette vague, pas tous les scénarios de recherche possibles.",
        "boundary_legal": "Uniquement pour l’évaluation de statut et la mesure de la prochaine vague — ne constitue pas un engagement d’implémentation, un devis ou une clause contractuelle.",
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "Marque cible",
        "rivals_fallback": "concurrents",
        "industry_mean": "Moyenne sectorielle (directionnelle)",
        "chart_tooltip_seg": "{label} : {pct}% ({count}/{total})",
        "chart_tooltip_plat_bubble": "{name} : visibilité sans marque {x}%, part concurrentielle {y}%, n={n}",
        "chart_tooltip_comp_scatter": "{name} : visibilité {x}%, part de sources {y}%{tag}",
        "chart_tooltip_comp_proxy": " (est.)",
        "fallback_section_01_desc": "L’IA reconnaît {brand_name} dans {branded_mentioned}/{branded_total} réponses à marque nommée ({branded_rate}%). Sur les questions de catégorie pré-décision, {brand_name} apparaît dans {unbranded_mentioned}/{unbranded_total} cas ; les concurrents occupent le créneau {takeover} fois.",
        "fallback_main_insight": "Cette vague montre une <b>reconnaissance à marque nommée de {branded_rate}%</b> pour {brand_name}, mais une absence de {unbranded_absent}/{unbranded_total} scénarios de décision sans marque, dont {takeover} créneaux de recommandation occupés par {rivals}. Priorisez les preuves qui améliorent la découverte sans marque, puis retestez avec le même jeu de prompts.",
        "fallback_section_05_insight": "Les concurrents marquent plus haut sur les sources externes car ils ont des citations générées par les utilisateurs plus denses sur YouTube, Reddit et les médias sectoriels — signaux auxquels l’IA fait confiance pour les recommandations sans marque. Le contenu propriétaire de {brand_name} est correct, mais la densité de citations tierces est plus faible. Les barres grises sont non testées, pas zéro ; commencez par Schema, Meta et llms.txt, puis construisez des citations externes.",
        "fallback_section_06_dr_note": "Le DA de {brand_name} est {dr} ; les concurrents vont de {comp_min} à {comp_max} — un écart modeste. Le DA mesure le volume de backlinks, pas la pertinence thématique. Les concurrents ont des citations de niche plus denses dans les médias et communautés, ce qui pèse plus pour les recommandations IA que le DA brut. Visez des citations d’autorité thématique, pas le DA seul.",
        "fallback_section_07_insight": "{brand_name} dispose d’actifs matures — site et notoriété — mais la plupart sont conçus pour les humains et les moteurs de recherche, pas pour la logique de recommandation de l’IA. Les concurrents sont plus structurés et cités en externe, donc l’IA les préfère sur les requêtes sans marque. Réencodez les actifs existants pour l’IA ; le retard renforce l’avantage de corpus des concurrents. Les canaux gris n’ont pas été testés indépendamment.",
        "fallback_section_08_desc": "Trois écarts empilés déplacent {brand_name} dans les recommandations IA : frontières produit floues → pas de pages citables sur les requêtes sans marque → des concurrents aux signaux plus forts gagnent le créneau. Les couches s’amplifient mutuellement.",
        "fallback_section_09_insight": "Le site officiel est la première source de confiance de l’IA pour {brand_name} — continuez à l’améliorer, ce n’est pas un one-shot. Le P0 couvre deux volets : (1) structure lisible par machine (Schema, balises sémantiques, H1/H2, Meta, llms.txt) ; (2) contenu citable et pages d’entrée de catégorie. L’off-site/social amplifie le travail on-site et ne doit pas venir en premier. Liez chaque initiative à des métriques IA retestables.",
        "fallback_root_expression": "Le contenu du site de {brand} peut paraître complet pour les humains, mais une structure faible ou des sections peu citables forcent l’IA à reconstruire le positionnement à partir de paragraphes dispersés — moins efficace que des concurrents bien structurés, et visible dans les recommandations sans marque ignorées.<br/><br/>Preuve : {evidence}.",
        "fallback_root_supply": "{brand} manque de pages qui répondent aux questions de catégorie pré-décision — comparaisons, sélection et différenciation concurrentielle que l’IA peut citer. Les concurrents couvrent ces nœuds sémantiques plus densément.<br/><br/>Preuve : {evidence}.",
        "fallback_root_distribution": "C’est la première porte d’acquisition : les acheteurs interrogent l’IA avant de choisir un fournisseur. Dans les scénarios sans marque, {brand} est souvent absent et les concurrents prennent le créneau de recommandation. Chaque absence oriente un prospect vers les rivaux.<br/><br/>Preuve : {evidence}.",
        "ch_desc_backlinks": "{desc} Le volume et la qualité des backlinks aident l’IA à juger s’il faut recommander une marque. Prochaine vague : vérifier médias, sites d’avis et annuaires sectoriels.",
        "ch_desc_youtube_tested": "{desc} L’IA utilise la vidéo (avis, tutoriels, unboxing) pour décrire les produits ; plus de vidéo de marque visible produit un texte IA plus spécifique.",
        "ch_desc_youtube_untested": "YouTube n’a pas été testé indépendamment cette vague. L’IA utilise le contenu vidéo pour les réponses produit ; vérifiez l’empreinte vidéo de la marque à la prochaine vague.",
        "ch_desc_reddit_tested": "{desc} L’IA pondère Reddit et les forums pour le feedback utilisateur — éloges et plaintes — ce qui affecte l’ajout de réserves ou la recommandation d’alternatives.",
        "ch_desc_reddit_untested": "Le sentiment communautaire n’a pas été testé indépendamment. Reddit et les forums façonnent la façon dont l’IA cadre le feedback et les recommandations.",
        "ch_desc_wikipedia": "{desc} Wikipédia est une source courante de désambiguïsation. L’absence d’article augmente le risque de confusion lorsque des noms de marque se croisent.",
        "ch_desc_schema": "{desc} Schema rend les pages lisibles par machine pour l’IA — marque, catégorie, audience. Sans cela, l’IA devine à partir du corps du texte. Faible coût, haute priorité.",
        "ch_desc_semantic": "{desc} Sans titres et sections clairs, l’IA peine à analyser la page et peut emprunter le phrasé concurrentiel. Corrigible on-site.",
        "ch_desc_meta": "{desc} La meta description est souvent la première source des résumés de marque par l’IA. Une meta vide force un texte improvisé et plus faible.",
        "ch_desc_llms": "{desc} llms.txt est une convention émergente pour indiquer aux crawlers quelles pages comptent. Combinez avec Schema et Meta pour accélérer la lisibilité machine.",
    },
    "ar": {
        "report_title_suffix": "تقرير تشخيص أداء نماذج الذكاء الاصطناعي",
        "report_sub": "استنادًا إلى {total_samples} عيّنة إجابة عبر {platform_phrase}، مع إشارات هيكلية للموقع الرسمي وملامح حركة البحث ومعايير المنافسين، يقيّم هذا التقرير ذكر {brand_name} واستشهاده وحضور التوصية في البحث التوليدي ومحركات الإجابات.",
        "report_audience": "لصانعي القرار في العلامة والتسويق والأعمال.",
        "meta_subject": "الموضوع",
        "meta_business": "نطاق العمل",
        "meta_platforms": "المنصات المعاينة",
        "meta_date": "تاريخ التقرير",
        "meta_report_code": "رمز التقرير",
        "section_01_no": "SECTION 02 · المقاييس الأساسية",
        "section_01_title": "أربعة أرقام تُحدّد الوضع الحالي",
        "kpi_unbranded": "الحضور بدون علامة",
        "kpi_unbranded_note": "عدد مرات ظهور {brand_name} عندما يسأل المشترون دون تسمية علامة.",
        "kpi_branded": "التعرّف مع العلامة",
        "kpi_branded_note": "عندما يذكر المستخدمون العلامة، تتعرّف معظم الإجابات عليها — الأصول موجودة لكن يجب إبرازها أبكر.",
        "kpi_competitor": "إجابات يشغلها المنافسون",
        "kpi_competitor_note": "إجابات يغيب فيها {brand_name} ويظهر منافس واحد على الأقل؛ تُحسب كل إجابة مرة واحدة ({rate}% من سيناريوهات الغياب).",
        "kpi_dr": "درجة سلطة النطاق",
        "kpi_dr_note": "المنافسون يسجّلون {comp_min}–{comp_max}. الدرجات الأعلى ترتبط بتفضيل الاستشهاد لدى الذكاء الاصطناعي.",
        "status_pending": "قيد الانتظار",
        "status_tested": "مقيس",
        "status_detected": "مكتشف",
        "status_partial": "تغطية جزئية",
        "status_critical_gap": "فجوة حرجة",
        "status_not_deployed": "غير منشور",
        "insight_label": "استنتاج",
        "platform_brand_visibility": "ظهور العلامة",
        "platform_unbranded_visibility": "الظهور بدون علامة",
        "platform_official_cite": "معدل استشهاد الموقع الرسمي",
        "platform_competitor_mentions": "إشارات المنافسين",
        "platform_samples_mentioned": "عيّنات مذكورة",
        "platform_unbranded_samples": "عيّنات بدون علامة",
        "platform_cited_official": "استشهادات الموقع الرسمي",
        "platform_low_competitor": "حصة منافسين منخفضة",
        "platform_footer": "مقاييس المنصة من عيّنات إجابات الذكاء الاصطناعي لهذه الجولة؛ الظهور بدون علامة هو المقياس الرئيسي قبل التحويل.",
        "platform_pending": "الجولة التالية",
        "platform_pending_sub": "قيد الانتظار",
        "platform_untested_note": "ملاحظة: لم يُختبر {name} بشكل مستقل في هذه الجولة؛ لا تفسّر العناصر المعلقة على أنها أداء صفري.",
        "platform_competitive_strength": "حصة منافسين منخفضة {pct}",
        "meta_per_platform_prompts": "{count} مطالبة لكل منصة",
        "meta_per_platform_prompts_partial": "مخطط {planned} مطالبة لكل منصة (التغطية الفعلية غير مكتملة)",
        "compare_unbranded": "الظهور بدون علامة",
        "compare_branded": "ظهور العلامة",
        "compare_competitor_inverse": "حصة منافسين منخفضة",
        "compare_pending": "قيد الانتظار — الجولة التالية",
        "cover_platforms_and_more": "{joined} و{count} منصات",
        "cover_platforms_count_only": "{count} منصات ذكاء اصطناعي رئيسية",
        "funnel_seg_complete": "ظاهر بالكامل",
        "funnel_seg_partial": "ظاهر جزئيًا",
        "funnel_seg_brand_absent": "العلامة غائبة",
        "funnel_seg_mine": "الهدف حاضر",
        "funnel_seg_comp": "المنافس حاضر",
        "funnel_seg_all_blank": "الجميع غائبون",
        "vs_label": "vs",
        "status_proxy": "دليل تقريبي",
        "status_mixed": "دليل مختلط",
        "status_not_tested": "غير مختبر في هذه الجولة",
        "status_not_independent": "غير مختبر بشكل مستقل",
        "status_unavailable": "غير متاح",
        "status_failed": "فشل الجمع",
        "status_blocked": "الزحف محظور",
        "section_02_no": "SECTION 01 · توزيع TOP",
        "section_02_title": "أين يظهر {brand_name} عبر {total_samples} عيّنة إجابة ذكاء اصطناعي",
        "section_02_desc": "بعد تصنيف العيّنات بحسب حضور العلامة واستشهاد الموقع الرسمي واستحواذ المنافسين، الفجوة الرئيسية ليست دقة التعرّف على العلامة، بل قدرة الدخول إلى قوائم التوصية في أعلى القمع (سيناريوهات بدون علامة).",
        "section_02_card_title": "نظرة عامة على توزيع العيّنات",
        "section_02_card_note": "مجموعتا سيناريو جنبًا إلى جنب: استعلامات بالعلامة ({branded_total}) واستعلامات بدون علامة ({unbranded_total})؛ كل صف مُطبَّع إلى 100٪ — مرّر المؤشر للنسب.",
        "legend_visible": "ظاهر",
        "legend_improve": "يحتاج تحسينًا / منافس",
        "legend_absent": "غائب",
        "scenario_card_title": "تفصيل السيناريوهات",
        "scenario_card_note": "أسس إحصائية مختلفة: صفوف العلامة سمات متداخلة؛ صفوف بدون علامة تقسيم MECE (ثلاثة أجزاء مجموعها {unbranded_total}).",
        "scenario_group_branded": "المستخدم سمّى العلامة · استعلامات بالعلامة {total}",
        "scenario_group_unbranded": "المستخدم لم يسمِّ العلامة · استعلامات بدون علامة {total}",
        "scenario_group_kicker_branded": "{count} / {total}",
        "scenario_group_kicker_unbranded": "{count} / {total} · ما قبل التحويل",
        "scenario_visibility_mix": "مزيج الظهور",
        "scenario_children_note": "الرؤية والاستشهاد بالموقع الرسمي في أسئلة العلامة التجارية",
        "scenario_unbranded_gap_note": "منافس {comp_pct}٪ + غياب تام {blank_pct}٪ = {absent_pct}٪ خارج التوصية. هذه فجوة ما قبل التحويل.",
        "scenario_recognized": "تم التعرّف",
        "scenario_not_recognized": "لم يُتعرَّف",
        "scenario_cited": "الموقع الرسمي مستشهد به",
        "scenario_not_cited": "الموقع الرسمي غير مستشهد به",
        "scenario_mine": "الهدف حاضر",
        "scenario_comp_takeover": "غائب · استحواذ المنافس",
        "scenario_all_blank": "غائب · الكل فارغ",
        "scenario_read_note": "الاستعلامات بدون علامة هي قمع ما قبل التحويل. عند الغياب (منافس {comp} + فارغ {blank} = {absent}) يُوصى بالمنافسين أولًا. انخفاض استشهاد الموقع الرسمي {cited}/{branded_total} في استعلامات العلامة يعني أن الذكاء الاصطناعي يعرف العلامة لكنه نادرًا ما يربط بالموقع.",
        "section_03_no": "SECTION 03 · المشاعر",
        "section_03_title": "كيف يتحدث الذكاء الاصطناعي عن {brand_name} — إيجابي أم سلبي",
        "section_03_desc": "تُصنَّف كل إجابة ذكاء اصطناعي (إيجابية / محايدة / سلبية) عند ذكر {brand_name}. انخفاض الحصة السلبية أكثر أمانًا؛ ارتفاع الحصة المحايدة يعني ذكرًا بلا تزكية.",
        "senti_overall_title": "مزيج المشاعر الإجمالي",
        "senti_overall_note": "حصة جميع الإجابات البالغ عددها {total} بعد تصنيف المشاعر لكل إجابة.",
        "senti_platform_title": "المشاعر حسب المنصة",
        "senti_platform_note": "المنهجية نفسها مقسّمة لكل منصة مختبرة لمقارنة الاتساق.",
        "senti_positive": "إيجابي",
        "senti_neutral": "محايد",
        "senti_negative": "سلبي",
        "senti_stat_line": "{label} · {count} إجابة",
        "senti_plat_counts": "إيج {pos} · محا {neu} · سل {neg}",
        "senti_insight_with_data": "عبر {total} إجابة ذكاء اصطناعي، {pos} إيجابية ({pos_pct}) و{neg} سلبية فقط ({neg_pct}) — مخاطر سمعة قليلة عند حديث الذكاء الاصطناعي عن {brand_name}. الفرصة في {neu_pct} المحايدة: مذكورة بلا تزكية. تحويل المحايد إلى دعم إيجابي هو القفزة من الظهور إلى التوصية.",
        "senti_insight_no_data": "لا عيّنات مشاعر قابلة للتصنيف في هذه الجولة.",
        "senti_cloud_title": "سحابة كلمات المشاعر",
        "senti_cloud_badge": "استخراج عبارات LLM",
        "senti_cloud_note": "عبارات مستخرجة من إجابات إيجابية/محايدة/سلبية تذكر {brand_name}؛ الحجم الأكبر يعني إجابات أكثر.",
        "senti_cloud_tab_positive": "كلمات إيجابية",
        "senti_cloud_tab_neutral": "كلمات محايدة",
        "senti_cloud_tab_negative": "كلمات سلبية",
        "senti_cloud_tooltip_count": "ظهر في {count} إجابة",
        "senti_cloud_empty_generic": "لا كلمات لهذه القطبية بعد.",
        "senti_cloud_empty_missing": "لم يُنتَج أثر كلمات المشاعر في هذه الجولة.",
        "senti_cloud_empty_no_answers": "إجابات مذكورة قليلة جدًا لاستخراج الكلمات.",
        "senti_cloud_empty_no_phrases": "توجد عيّنات مشاعر، لكن لم تُستخرج عبارات قابلة للعرض.",
        "section_04_no": "SECTION 04 · أداء المنصات",
        "section_04_title": "فروق الظهور عبر نماذج الذكاء الاصطناعي الرئيسية",
        "section_04_desc": "المنصات المختبرة تشارك مجموعة المطالبات نفسها؛ المنصات غير المختبرة تبقى معلّمة قيد الانتظار — لا تُحسب صفرًا.",
        "plat_compare_title": "مقارنة ظهور المنصات",
        "plat_compare_note": "ثلاثة مقاييس ظهور (0–100٪، الأعلى أفضل) لكل منصة؛ معدل استشهاد الموقع الرسمي على بطاقات المنصة أعلاه.",
        "plat_matrix_title": "مصفوفة مقاومة التوصية",
        "plat_matrix_note": "س = الظهور بدون علامة (اليمين أفضل)؛ ص = حصة المنافسين (الأقل أفضل)؛ حجم الفقاعة = عدد العيّنات. الأزرق أسفل اليمين = مثالي؛ أعلى اليسار = مخاطر عالية.",
        "section_05_no": "SECTION 05 · سلطة المصادر",
        "section_05_title": "أنواع المصادر التي يمكن للذكاء الاصطناعي الاستشهاد بها عنّا",
        "section_05_desc": "أزرق فاتح = خط أساس عبر الفئات؛ بنفسجي = الحالة الحالية؛ التقديرات التقريبية مُعلَّمة.",
        "auth_radar_title": "رادار مصداقية العلامة",
        "auth_radar_note": "خمسة أبعاد تقيس بصمة المحتوى الموثوق: المصدر الرسمي = سلطة النطاق + استشهاد الذكاء الاصطناعي (6:4، مقيس)؛ الموسوعة / الإعلام / المجتمع / العمق اتجاهية.",
        "auth_dim_title": "تفسير الأبعاد",
        "auth_dim_note": "الدرجات تعكس كمية المحتوى الموثوق الذي يجده الذكاء الاصطناعي لكل قناة (0–100 نسبي).",
        "auth_focus_note": "التركيز: الموسوعة والإعلام والمجتمع — إشارات التحقق الخارجي الأساسية.",
        "legend_radar_industry": "خط أساس عبر الفئات",
        "legend_radar_current": "{brand_name} الحالي",
        "section_06_no": "SECTION 06 · الحضور عبر القنوات",
        "section_06_title": "أين يجد الذكاء الاصطناعي محتوىً عنّا",
        "section_06_desc": "نفس مقياس 0–100 للرادار: الموقع / الموسوعة / الإعلام تقابل محاور الرادار؛ YouTube وReddit يقسمان محور المجتمع (المجتمع = متوسطهما). الأعلى أفضل.",
        "src_bar_title": "مقارنة درجات القنوات",
        "src_bar_note": "بنفسجي = {brand_name} الحالي؛ رمادي = مستوى مرجعي للأقران (اتجاهي).",
        "legend_peer_ref": "مرجع الأقران",
        "section_07_no": "SECTION 07 · فجوة المنافسين",
        "section_07_title": "مقاومة التوصية وضغط المنافسين",
        "section_07_desc": "س = ظهور الذكاء الاصطناعي بدون علامة (% مقيس)؛ ص = حصة الإجابات التي تستشهد بالعلامة كمصدر (%). النقاط المجوّفة = تقريب من سلطة النطاق عند غياب حصة الاستشهاد.",
        "comp_bubble_title": "حضور المنافسين في إجابات الذكاء الاصطناعي",
        "comp_bubble_note": "س = تكرار الذكر في استعلامات بدون علامة (مقيس)؛ ص = حصة الاستشهاد كمصدر. مجوّف = تقدير تقريبي.",
        "dr_bar_title": "مقارنة سلطة النطاق",
        "dr_bar_note": "سلطة النطاق تعكس عدد المواقع الخارجية التي تشير إلى النطاق؛ الدرجات الأعلى ترتبط بثقة الذكاء الاصطناعي. الحد الأقصى 100.",
        "search_dr_row": "DR {dr} · Organic {organic} · Keywords {keywords}",
        "section_08_no": "SECTION 08 · ترتيب المنافسين",
        "section_08_title": "من يذكره الذكاء الاصطناعي أكثر في الفئة",
        "section_08_desc": "رتّب {brand_name} مقابل المنافسين بعدد الإشارات الفعلي في {denom} إجابة ذكاء اصطناعي للفئة (بدون علامة). الترتيب الأعلى = خانة توصية أفضل قبل القرار.",
        "rank_card_title": "لوحة صدارة إشارات الفئة",
        "rank_card_note": "تمييز بنفسجي = {brand_name}؛ طول الشريط = التكرار النسبي للإشارة؛ اليمين = العدد المطلق وحصة الاستعلامات بدون علامة.",
        "rank_card_badge": "{denom} استعلام بدون علامة",
        "rank_you_tag": "هذه العلامة",
        "rank_focus_tag": "تركيز",
        "rank_count_line": "{mentions} إشارة · {rate}",
        "rank_phrase": "الترتيب #{rank}",
        "rank_not_listed": "غير مدرج",
        "rank_headline_ranked": "من بين {total_brands} علامة في الفئة، يحتل {brand_name} <b>{rank_phrase}</b> بتكرار الذكر في استعلامات الذكاء الاصطناعي بدون علامة.",
        "rank_headline_unranked": "من بين {total_brands} علامة في الفئة، لم يدخل {brand_name} بعد ترتيب الإشارات في استعلامات الذكاء الاصطناعي بدون علامة.",
        "focus_comp_kicker": "منافسون تحت المتابعة",
        "focus_comp_title": "المنافسون المراقبون لهذا التقرير",
        "focus_comp_note": "من إعداد التقرير (أدق من الاكتشاف التلقائي). الإشارات أدناه مقيسة في عيّنة بدون علامة لهذه الجولة؛ الغياب يعني عدم التسمية في العيّنة، لا «ليس منافسًا».",
        "focus_comp_mentions": "{count} إشارة بدون علامة",
        "focus_comp_rank": "الترتيب #{rank}",
        "focus_comp_absent": "لم يُسمَّ في هذه الجولة",
        "section_09_no": "SECTION 09 · تشخيص القنوات",
        "section_09_title": "أين الفجوات وما الذي يُصلَح بسرعة",
        "section_09_desc": "الموقع الرسمي أولًا، ثم البصمة خارج الموقع / الاجتماعية. أزرق = مقيس ومقبول؛ أصفر = يحتاج تحسينًا؛ أحمر = فجوة واضحة؛ رمادي = غير مختبر بشكل مستقل في هذه الجولة.",
        "channel_group_official_kicker": "01 · داخل الموقع",
        "channel_group_official_title": "الموقع الرسمي",
        "channel_group_official_note": "قابلية قراءة الموقع آليًا: ترميز منظم، حدود دلالية، تراتب العناوين، تعريف بجملة واحدة، تلميحات الزحف، وكثافة قابلة للاستشهاد في المتن/الصفحات الداخلية.",
        "channel_group_offsite_kicker": "02 · خارج الموقع",
        "channel_group_offsite_title": "روابط خلفية / اجتماعي",
        "channel_group_offsite_note": "البصمة خارج الموقع: إجمالي الروابط الخلفية، حجم بحث الفيديو/المجتمع، الحضور الموسوعي. الأعداد الاجتماعية من بحث بالكلمات المفتاحية وقد لا تساوي محتوىً موثّقًا مرتبطًا بالعلامة.",
        "section_10_no": "SECTION 10 · الأسباب الجذرية",
        "section_10_title": "لماذا لا يوصي الذكاء الاصطناعي بـ{brand_name} بنشاط بعد",
        "section_11_no": "SECTION 11 · التوصيات",
        "section_11_title": "من أين تبدأ وكيف",
        "section_11_desc": "عمل الموقع الرسمي دائمًا أولًا: بنية قابلة للقراءة آليًا وصفحات قابلة للاستشهاد قبل خارج الموقع/الاجتماعي. مرتّب حسب الجهد والأثر المتوقع.",
        "recs_col_priority": "الأولوية",
        "recs_col_action": "الإجراء",
        "recs_col_why": "لماذا هذا",
        "recs_col_metric": "تغيّر المقياس المتوقع",
        "recs_col_effort": "نطاق الجهد",
        "recs_site_markup_hint": "JSON-LD Schema · semantic HTML · H1/H2 · meta description · llms.txt · robots/sitemap",
        "recs_site_markup_action_zh": "官网机器可读性与页面结构补强",
        "recs_site_markup_action_en": "Strengthen on-site machine readability and page structure",
        "recs_site_content_hint": "صفحات الفئة · أدلة المقارنة/الشراء · أقسام H2 واضحة · كتل حقائق قابلة للاستشهاد",
        "recs_site_content_action_zh": "官网可引用内容与信息架构建设",
        "recs_site_content_action_en": "Build citable on-site content and information architecture",
        "section_12_no": "SECTION 12 · المصادر المستشهد بها",
        "section_12_title": "المواقع والمقالات التي استشهد بها الذكاء الاصطناعي فعليًا",
        "section_12_desc": "يحصي الاستشهادات الظاهرة في الإجابة (وليس قوائم البحث). مرتبة حسب تكرار النطاق؛ تُعرض أفضل 30. إذا كان الموقع الرسمي خارج الثلاثين الأوائل يُدرج في النهاية. افتح الصف لرؤية الروابط والأعداد.",
        "cite_rank_tab_branded": "استعلامات بالعلامة",
        "cite_rank_tab_unbranded": "استعلامات بدون علامة",
        "cite_rank_tab_meta": "{answers} إجابة · {citations} استشهاد",
        "cite_rank_empty": "لم تُلتقط استشهادات مطبّقة لهذه المجموعة",
        "cite_rank_count": "{count}×",
        "cite_rank_official": "الموقع الرسمي",
        "cite_rank_urls_n": "{count} مقالة",
        "cite_rank_truncated": "عرض أفضل {n} من أصل {total} نطاقًا",
        "cite_rank_unlisted": "خارج الترتيب",
        "section_13_no": "SECTION 12 · المطالبات والإجابات",
        "section_13_title": "افتح أي صف لمعاينة ما أجاب به الذكاء الاصطناعي فعليًا",
        "qa_group_branded": "مطالبة بالعلامة",
        "qa_group_unbranded": "مطالبة بدون علامة",
        "qa_group_default": "استعلام",
        "qa_dot_mentioned": "مذكور",
        "qa_dot_not_mentioned": "غير مذكور",
        "qa_badge_mentioned": "العلامة مذكورة",
        "qa_badge_not_mentioned": "غير مذكور",
        "qa_badge_cite_official": "الموقع الرسمي مستشهد به",
        "qa_badge_cite_missing": "الموقع الرسمي غير مستشهد به",
        "qa_badge_partial_visible": "ظاهر جزئيًا",
        "qa_badge_fully_visible": "ظاهر بالكامل",
        "qa_dots_legend": "النقاط = ما إذا ذكرت كل منصة العلامة (أزرق = نعم، رمادي = لا)",
        "qa_comp_mentioned": "منافسون في نفس الإجابة: {names}",
        "qa_queried_as": "المطالبة الفعلية: {text}",
        "qa_no_excerpt": "(الإجابة الكاملة غير مخزّنة — غالبًا فشل جمع أو تقرير قديم بلا نص إجابة.)",
        "qa_evidence": "أساس التصنيف:",
        "qa_evidence_corrected": "اسم العلامة غير موجود في نص الإجابة؛ صُحّح إلى غير مذكور",
        "qa_evidence_corrected_original": "اسم العلامة غير موجود في نص الإجابة؛ صُحّح إلى غير مذكور. الأساس الأصلي: {evidence}",
        "qa_sources": "المصادر",
        "qa_source_cited": "ظهر في الإجابة",
        "qa_source_listed": "مصدر مدرج",
        "qa_no_sources": "لم تُلتقط مصادر لهذه الإجابة",
        "qa_expand_answer": "توسيع الإجابة الكاملة",
        "qa_collapse_answer": "طي الإجابة",
        "qa_open_modal": "عرض التفاصيل",
        "qa_modal_close": "إغلاق",
        "qa_modal_question": "المطالبة",
        "qa_modal_actual_prompt": "مطالبة المنصة الفعلية",
        "qa_modal_status": "وسوم الحالة",
        "qa_modal_ranking": "ترتيب العلامة / المنافس في الإجابة",
        "qa_modal_competitors": "المنافسون المذكورون",
        "qa_no_platform": "لا إجابات منصة لهذه المطالبة",
        "qa_no_competitors": "لم تُكتشف إشارات منافسين",
        "qa_no_rank": "لا إشارات ترتيب متاحة",
        "qa_rank_absent": "غائب",
        "qa_section_note": "انقر أي مطالبة لفتح نافذة بعلامات تبويب للمنصات وإجابات Markdown والمصادر وملاحظات التصنيف وترتيب الذكر.",
        "boundary_title": "ملاحظات البيانات",
        "boundary_tested": "اختُبر في هذه الجولة:",
        "boundary_not_tested": "لم يُختبر بشكل مستقل في هذه الجولة",
        "boundary_not_tested_note": "(ليست درجة صفر — يمكن اختباره في الجولة التالية)",
        "boundary_proxy": "تقديرات تقريبية",
        "boundary_proxy_note": "(اتجاهية وليست قياسًا دقيقًا)",
        "boundary_scope": "النتائج تعكس نطاق مطالبات هذه الجولة، لا كل سيناريوهات البحث الممكنة.",
        "boundary_legal": "لتقييم الحالة وقياس الجولة التالية فقط — ليست التزام تنفيذ أو عرض سعر أو بندًا تعاقديًا.",
        "badge_data_samples": "DATA · {count} SAMPLES",
        "default_target_brand": "العلامة المستهدفة",
        "rivals_fallback": "المنافسون",
        "industry_mean": "متوسط القطاع (اتجاهي)",
        "chart_tooltip_seg": "{label}: {pct}% ({count}/{total})",
        "chart_tooltip_plat_bubble": "{name}: ظهور بدون علامة {x}%، حصة المنافسين {y}%، n={n}",
        "chart_tooltip_comp_scatter": "{name}: ظهور {x}%، حصة المصادر {y}%{tag}",
        "chart_tooltip_comp_proxy": " (تقدير)",
        "fallback_section_01_desc": "يتعرّف الذكاء الاصطناعي على {brand_name} في {branded_mentioned}/{branded_total} إجابات بعلامة مسمّاة ({branded_rate}%). في أسئلة الفئة قبل القرار، يظهر {brand_name} في {unbranded_mentioned}/{unbranded_total} حالة؛ والمنافسون يملؤون الخانة {takeover} مرة.",
        "fallback_main_insight": "تُظهر هذه الجولة <b>تعرّفًا بعلامة مسمّاة بنسبة {branded_rate}%</b> لـ{brand_name}، لكن غيابًا عن {unbranded_absent}/{unbranded_total} سيناريو قرار بدون علامة، منها {takeover} خانة توصية يشغلها {rivals}. امنح الأولوية للأدلة التي تحسّن الاكتشاف بدون علامة، ثم أعد الاختبار بنفس مجموعة المطالبات.",
        "fallback_section_05_insight": "يسجّل المنافسون أعلى في المصادر الخارجية لأن لديهم استشهادات مولَّدة من المستخدمين بكثافة أعلى على YouTube وReddit وإعلام القطاع — إشارات يثق بها الذكاء الاصطناعي للتوصيات بدون علامة. محتوى {brand_name} المملوك جيد، لكن كثافة استشهاد الطرف الثالث أقل. الأشرطة الرمادية غير مختبرة وليست صفرًا؛ ابدأ بـSchema وMeta وllms.txt ثم ابنِ استشهادات خارجية.",
        "fallback_section_06_dr_note": "درجة سلطة نطاق {brand_name} هي {dr}؛ والمنافسون بين {comp_min}–{comp_max} — فجوة متواضعة. تقيس سلطة النطاق حجم الروابط الخلفية لا الصلة الموضوعية. لدى المنافسين استشهادات تخصصية أكثف في الإعلام والمجتمعات، وهذا أثقل لتوصيات الذكاء الاصطناعي من السلطة الخام. اسعَ لاستشهادات سلطة موضوعية لا لدرجة النطاق وحدها.",
        "fallback_section_07_insight": "لدى {brand_name} أصول ناضجة — موقع ووعي بالعلامة — لكن معظمها مبني للبشر ومحركات البحث لا لمنطق توصية الذكاء الاصطناعي. المنافسون أكثر هيكلة واستشهادًا خارجيًا، لذا يفضّلهم الذكاء الاصطناعي في الاستعلامات بدون علامة. أعد ترميز الأصول الحالية للذكاء الاصطناعي؛ التأخير يعزّز ميزة ذخيرة المنافسين. القنوات الرمادية لم تُختبر بشكل مستقل.",
        "fallback_section_08_desc": "ثلاث فجوات متراكبة تزيح {brand_name} من توصيات الذكاء الاصطناعي: حدود منتج غير واضحة → لا صفحات قابلة للاستشهاد في الاستعلامات بدون علامة → منافسون بإشارات أقوى يفوزون بالخانة. الطبقات تضخّم بعضها.",
        "fallback_section_09_insight": "الموقع الرسمي هو أول مصدر يثق به الذكاء الاصطناعي لـ{brand_name} — واصل تحسينه وليس مرة واحدة وانتهى. يغطي P0 مسارين: (1) بنية قابلة للقراءة آليًا (Schema والوسوم الدلالية وH1/H2 وMeta وllms.txt)؛ (2) محتوى قابل للاستشهاد وصفحات دخول للفئة. خارج الموقع/الاجتماعي يضخّم العمل داخل الموقع ويجب ألا يسبقه. اربط كل مبادرة بمقاييس ذكاء اصطناعي قابلة لإعادة الاختبار.",
        "fallback_root_expression": "قد يبدو محتوى موقع {brand} مكتملًا للبشر، لكن الهيكل الضعيف أو الأقسام ضعيفة الاستشهاد تدفع الذكاء الاصطناعي لتجميع التموضع من فقرات متفرقة — أقل كفاءة من منافسين منظمين جيدًا، ويظهر في توصيات بدون علامة يتم تخطيها.<br/><br/>الدليل: {evidence}.",
        "fallback_root_supply": "يفتقر {brand} إلى صفحات تجيب عن أسئلة الفئة قبل القرار — مقارنات واختيار وتمايز منافسين يمكن للذكاء الاصطناعي الاستشهاد بها. المنافسون يغطّون هذه العقد الدلالية بكثافة أعلى.<br/><br/>الدليل: {evidence}.",
        "fallback_root_distribution": "هذه بوابة الاستحواذ الأولى: يسأل المشترون الذكاء الاصطناعي قبل اختيار المورّد. في سيناريوهات بدون علامة غالبًا ما يغيب {brand} ويأخذ المنافسون خانة التوصية. كل غياب يوجّه عميلًا محتملًا إلى المنافسين.<br/><br/>الدليل: {evidence}.",
        "ch_desc_backlinks": "{desc} يساعد حجم الروابط الخلفية وجودتها الذكاء الاصطناعي على تقرير ما إذا يوصي بعلامة. الجولة التالية: تحقق من الإعلام ومواقع المراجعات وأدلة القطاع.",
        "ch_desc_youtube_tested": "{desc} يستخدم الذكاء الاصطناعي الفيديو (مراجعات، دروس، فتح العلبة) لوصف المنتجات؛ كلما زاد فيديو العلامة الظاهر زاد نص الذكاء الاصطناعي تحديدًا.",
        "ch_desc_youtube_untested": "لم يُختبر YouTube بشكل مستقل في هذه الجولة. يستخدم الذكاء الاصطناعي محتوى الفيديو لإجابات المنتج؛ تحقق من بصمة فيديو العلامة في الجولة التالية.",
        "ch_desc_reddit_tested": "{desc} يزن الذكاء الاصطناعي Reddit والمنتديات لملاحظات المستخدمين — الثناء والشكاوى — مما يؤثر على إضافة تحفظات أو التوصية ببدائل.",
        "ch_desc_reddit_untested": "لم يُختبر شعور المجتمع بشكل مستقل. يشكّل Reddit والمنتديات كيفية تأطير الذكاء الاصطناعي للملاحظات والتوصيات.",
        "ch_desc_wikipedia": "{desc} ويكيبيديا مصدر شائع لرفع الالتباس. غياب مقالة يزيد خطر الخلط عند تصادم أسماء العلامات.",
        "ch_desc_schema": "{desc} يجعل Schema الصفحات قابلة للقراءة آليًا للذكاء الاصطناعي — العلامة والفئة والجمهور. بدونه يخمن من نص الصفحة. تكلفة منخفضة وأولوية عالية.",
        "ch_desc_semantic": "{desc} بدون عناوين وأقسام واضحة يصعب على الذكاء الاصطناعي تحليل الصفحة وقد يستعير صياغة المنافسين. قابل للإصلاح داخل الموقع.",
        "ch_desc_meta": "{desc} غالبًا ما تكون meta description أول مصدر لملخصات العلامة لدى الذكاء الاصطناعي. الـmeta الفارغة تفرض نصًا مرتجلًا أضعف.",
        "ch_desc_llms": "{desc} llms.txt اتفاقية ناشئة لإخبار الزواحف بالصفحات المهمة. اجمعها مع Schema وMeta لتسريع القابلية للقراءة آليًا.",
    },
    "ja": JA_UI_STRINGS,
}
