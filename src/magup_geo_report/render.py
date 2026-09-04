from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from magup_geo_report import DISPLAY_NAME, PRODUCT_URL, REPO_URL, __version__
from magup_geo_report.geo_report import render_geo_html
from magup_geo_report.i18n import chrome
from magup_geo_report.site_audit import SiteAudit

STATUS_LABEL = {"pass": "Pass", "warn": "Warn", "fail": "Fail", "skip": "Skip"}


def _strings(meta: dict[str, Any] | None) -> dict[str, str]:
    if meta and isinstance(meta.get("strings"), dict):
        return meta["strings"]
    return chrome((meta or {}).get("language") or "en")


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_markdown(
    audit: SiteAudit | None,
    *,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    answers_path: str | None,
    search_path: str | None,
    meta: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    s = _strings(meta)
    brand = (meta or {}).get("brand") or (audit.brand if audit else "")
    lines = [
        f"# {DISPLAY_NAME}",
        "",
        f"> {s['not_production']} "
        f"[{PRODUCT_URL}]({PRODUCT_URL})",
        "",
        f"- Generated: {now}",
        f"- Generator: magup-geo-report {__version__}",
        f"- Repository: {REPO_URL}",
        f"- Brand: {brand}",
        "",
    ]
    intro = (meta or {}).get("brand_intro") or ""
    competitors = (meta or {}).get("competitors") or []
    analysis = (meta or {}).get("analysis")
    if intro or competitors:
        lines += [f"## {s['brief']}", ""]
        if intro:
            lines += [intro, ""]
        if competitors:
            lines += [f"{s['competitors']}: " + ", ".join(competitors), ""]
    if analysis:
        totals = analysis.get("totals") or {}
        lines += [
            f"## {s.get('sec_visibility', 'Visibility')}",
            "",
            analysis.get("disclaimer", ""),
            "",
            f"- {s.get('kpi_mention', 'Brand mentioned')}: {totals.get('brand_rate', 0)}% ({totals.get('brand_hit', 0)}/{totals.get('usable', 0)})",
            f"- {s.get('kpi_cite', 'Official site cited')}: {totals.get('cite_rate', 0)}% ({totals.get('own_site_cited', 0)}/{totals.get('usable', 0)})",
            f"- {s.get('kpi_competitor', 'Competitor mentioned')}: {totals.get('competitor_rate', 0)}% ({totals.get('competitor_hit', 0)}/{totals.get('usable', 0)})",
            f"- {s.get('kpi_samples', 'Samples')}: {totals.get('samples', 0)}",
            "",
        ]
        for _code, row in (analysis.get("by_platform") or {}).items():
            lines += [
                f"### {row.get('label') or _code}",
                "",
                f"- mention {row.get('brand_rate')}% · cite {row.get('cite_rate')}% · competitor {row.get('competitor_rate')}% · n={row.get('total')}",
                "",
            ]
    planned = (meta or {}).get("prompts") or []
    if planned and not answers:
        lines += ["## Prompts", ""]
        for index, text in enumerate(planned, start=1):
            lines += [f"{index}. {text}", ""]
    if audit:
        lines += [
            f"**URL:** {audit.requested_url}  ",
            f"**Final URL:** {audit.final_url}  ",
            f"**Domain:** {audit.domain}  ",
            f"**Brand (heuristic):** {audit.brand}",
            "",
            f"## {s['hygiene']}",
            "",
            f"| {s['check']} | {s['status']} | {s['detail']} |",
            "| --- | --- | --- |",
        ]
        for check in audit.checks:
            lines.append(
                f"| {check.title} | {s.get(check.status, STATUS_LABEL.get(check.status, check.status))} | {check.detail.replace('|', '/')} |"
            )
        lines += [
            "",
            f"### {s['ai_bots']}",
            "",
            f"| {s['bot']} | {s['status']} | {s['detail']} |",
            "| --- | --- | --- |",
        ]
        for row in audit.bot_rules:
            lines.append(
                f"| {row['bot']} | {s.get(row['status'], STATUS_LABEL.get(row['status'], row['status']))} | {row['detail'].replace('|', '/')} |"
            )
        lines += [
            "",
            f"### {s['onpage']}",
            "",
            f"- {s['title']}: {audit.onpage.get('title') or s['missing']}",
            f"- {s['description']}: {audit.onpage.get('description') or s['missing']}",
            f"- {s['canonical']}: {audit.onpage.get('canonical') or s['missing']}",
            f"- {s['h1']}: {', '.join(audit.onpage.get('h1') or []) or s['none']}",
            f"- {s['jsonld']}: {', '.join(audit.json_ld_types) or s['none']}",
            "",
        ]
    else:
        lines += [s["skipped"], ""]

    if answers:
        lines += [
            f"## {s['raw_answers']}",
            "",
            answers.get("disclaimer", ""),
            "",
            f"Saved file: `{answers_path or 'answers.json'}`",
            "",
        ]
        for index, item in enumerate(answers.get("items") or [], start=1):
            platform = item.get("platform") or ""
            heading = f"### Q{item.get('prompt_index') or index}"
            if platform:
                heading += f" · {platform}"
            lines += [
                heading,
                "",
                item.get("prompt", ""),
                "",
                "```",
                (item.get("answer") or item.get("error") or "(empty)"),
                "```",
                "",
            ]
    if search_raw:
        lines += [
            f"## {s['raw_search']}",
            "",
            search_raw.get("disclaimer", ""),
            "",
            f"Saved file: `{search_path or 'search-raw.json'}`",
            "",
        ]
    lines += [
        "---",
        "",
        f"{s['cta_title']} {s['cta_body']} [{PRODUCT_URL}]({PRODUCT_URL}).",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_html(
    audit: SiteAudit | None,
    *,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    answers_path: str | None = None,
    search_path: str | None = None,
    meta: dict[str, Any] | None = None,
) -> str:
    return render_geo_html(
        audit,
        answers=answers,
        search_raw=search_raw,
        analysis=(meta or {}).get("analysis"),
        meta=meta,
    )


def write_outputs(
    out_dir: Path,
    *,
    audit: SiteAudit | None,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    answers_name = "answers.json" if answers else None
    search_name = "search-raw.json" if search_raw else None
    analysis = (meta or {}).get("analysis")
    if audit:
        audit_path = out_dir / "site-audit.json"
        audit_path.write_text(json.dumps(audit.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        written["site_audit"] = audit_path
    if answers:
        path = out_dir / "answers.json"
        path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
        written["answers"] = path
    if analysis:
        path = out_dir / "analysis.json"
        path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        written["analysis"] = path
    if search_raw:
        path = out_dir / "search-raw.json"
        path.write_text(json.dumps(search_raw, ensure_ascii=False, indent=2), encoding="utf-8")
        written["search_raw"] = path
    md = render_markdown(
        audit,
        answers=answers,
        search_raw=search_raw,
        answers_path=answers_name,
        search_path=search_name,
        meta=meta,
    )
    html_doc = render_html(
        audit,
        answers=answers,
        search_raw=search_raw,
        answers_path=answers_name,
        search_path=search_name,
        meta=meta,
    )
    md_path = out_dir / "geo-report.md"
    html_path = out_dir / "geo-report.html"
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    written["markdown"] = md_path
    written["html"] = html_path
    return written
