from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from magup_geo_report import DISPLAY_NAME, PRODUCT_URL, REPO_URL, __version__
from magup_geo_report.site_audit import Check, SiteAudit

STATUS_LABEL = {"pass": "Pass", "warn": "Warn", "fail": "Fail", "skip": "Skip"}


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_markdown(
    audit: SiteAudit | None,
    *,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    answers_path: str | None,
    search_path: str | None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {DISPLAY_NAME}",
        "",
        f"> **Community / 社区版.** This is not a MagUp production GEO detection report. "
        f"It does not include MagUp production scores, mention rates, or semantic analysis (021). "
        f"Full monitoring and scored reports: [{PRODUCT_URL}]({PRODUCT_URL})",
        "",
        f"- Generated: {now}",
        f"- Generator: magup-geo-report {__version__}",
        f"- Repository: {REPO_URL}",
        "",
    ]
    if audit:
        lines += [
            f"**URL:** {audit.requested_url}  ",
            f"**Final URL:** {audit.final_url}  ",
            f"**Domain:** {audit.domain}  ",
            f"**Brand (heuristic):** {audit.brand}",
            "",
            "## Site GEO hygiene",
            "",
            "| Check | Status | Detail |",
            "| --- | --- | --- |",
        ]
        for check in audit.checks:
            lines.append(f"| {check.title} | {STATUS_LABEL.get(check.status, check.status)} | {check.detail.replace('|', '/')} |")
        lines += [
            "",
            "### AI crawler robots.txt",
            "",
            "| Bot | Status | Detail |",
            "| --- | --- | --- |",
        ]
        for row in audit.bot_rules:
            lines.append(f"| {row['bot']} | {STATUS_LABEL.get(row['status'], row['status'])} | {row['detail'].replace('|', '/')} |")
        lines += [
            "",
            "### On-page",
            "",
            f"- Title: {audit.onpage.get('title') or '(missing)'}",
            f"- Description: {audit.onpage.get('description') or '(missing)'}",
            f"- Canonical: {audit.onpage.get('canonical') or '(missing)'}",
            f"- H1: {', '.join(audit.onpage.get('h1') or []) or '(none)'}",
            f"- JSON-LD @type: {', '.join(audit.json_ld_types) or '(none)'}",
            "",
        ]
    else:
        lines += ["Site hygiene chapter skipped (`--answers-only`).", ""]

    if answers:
        lines += [
            "## Raw LLM answers (no analysis)",
            "",
            answers.get("disclaimer", ""),
            "",
            f"Saved file: `{answers_path or 'answers.json'}`",
            "",
        ]
        for index, item in enumerate(answers.get("items") or [], start=1):
            lines += [
                f"### Q{index}",
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
            "## Raw DataForSEO payload (no Search Profile)",
            "",
            search_raw.get("disclaimer", ""),
            "",
            f"Saved file: `{search_path or 'search-raw.json'}`",
            "",
            "The JSON is not interpreted here on purpose.",
            "",
        ]
    lines += [
        "---",
        "",
        f"Need LLM visibility, multi-model mention tracking, and a MagUp production report? "
        f"Submit your site at [{PRODUCT_URL}]({PRODUCT_URL}).",
        "",
    ]
    return "\n".join(lines) + "\n"


def _pill(status: str) -> str:
    return f'<span class="pill {status}">{_esc(STATUS_LABEL.get(status, status))}</span>'


def _check_rows(checks: list[Check]) -> str:
    rows = []
    for check in checks:
        rows.append(
            "<tr>"
            f"<td>{_esc(check.title)}</td>"
            f"<td>{_pill(check.status)}</td>"
            f"<td>{_esc(check.detail)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html(
    audit: SiteAudit | None,
    *,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    answers_path: str | None,
    search_path: str | None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    brand = audit.brand if audit else "Site"
    domain = audit.domain if audit else ""
    hygiene = ""
    if audit:
        bot_rows = "\n".join(
            "<tr>"
            f"<td>{_esc(row['bot'])}</td>"
            f"<td>{_pill(row['status'])}</td>"
            f"<td>{_esc(row['detail'])}</td>"
            "</tr>"
            for row in audit.bot_rules
        )
        h1 = ", ".join(audit.onpage.get("h1") or []) or "(none)"
        types = ", ".join(audit.json_ld_types) or "(none)"
        hygiene = f"""
<section>
  <h2>Site GEO hygiene</h2>
  <p class="meta">Requested {_esc(audit.requested_url)} → {_esc(audit.final_url)}</p>
  <table>
    <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
    <tbody>
      {_check_rows(audit.checks)}
    </tbody>
  </table>
  <h3>AI crawler robots.txt</h3>
  <table>
    <thead><tr><th>Bot</th><th>Status</th><th>Detail</th></tr></thead>
    <tbody>
      {bot_rows}
    </tbody>
  </table>
  <h3>On-page</h3>
  <ul>
    <li>Title: {_esc(audit.onpage.get("title") or "(missing)")}</li>
    <li>Description: {_esc(audit.onpage.get("description") or "(missing)")}</li>
    <li>Canonical: {_esc(audit.onpage.get("canonical") or "(missing)")}</li>
    <li>H1: {_esc(h1)}</li>
    <li>JSON-LD @type: {_esc(types)}</li>
  </ul>
</section>
"""
    else:
        hygiene = "<section><p>Site hygiene chapter skipped (<code>--answers-only</code>).</p></section>"

    answers_html = ""
    if answers:
        blocks = []
        for index, item in enumerate(answers.get("items") or [], start=1):
            body = item.get("answer") or item.get("error") or "(empty)"
            blocks.append(
                f"<article class='qa'><h3>Q{index}</h3>"
                f"<p class='prompt'>{_esc(item.get('prompt'))}</p>"
                f"<pre>{_esc(body)}</pre></article>"
            )
        answers_html = f"""
<section>
  <h2>Raw LLM answers (no analysis)</h2>
  <p class="disclaimer">{_esc(answers.get("disclaimer"))}</p>
  <p class="meta">File: {_esc(answers_path or "answers.json")}</p>
  {"".join(blocks)}
</section>
"""
    search_html = ""
    if search_raw:
        snippet = json.dumps(search_raw.get("response"), ensure_ascii=False, indent=2)[:4000] if search_raw.get("response") is not None else json.dumps(search_raw, ensure_ascii=False, indent=2)[:4000]
        search_html = f"""
<section>
  <h2>Raw DataForSEO payload (no Search Profile)</h2>
  <p class="disclaimer">{_esc(search_raw.get("disclaimer"))}</p>
  <p class="meta">File: {_esc(search_path or "search-raw.json")}</p>
  <pre>{_esc(snippet)}</pre>
</section>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(DISPLAY_NAME)} — {_esc(brand)}</title>
  <style>
    :root {{
      --ink: #14202b;
      --muted: #5b6b78;
      --paper: #f6f3ee;
      --card: #fffdf9;
      --line: #e4ddd3;
      --accent: #c45c26;
      --pass: #2f6f4e;
      --warn: #9a6b12;
      --fail: #a33b32;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif;
      background: var(--paper); color: var(--ink); line-height: 1.5;
    }}
    header {{
      padding: 28px 8vw 16px; border-bottom: 1px solid var(--line);
    }}
    .ribbon {{
      display: inline-block; letter-spacing: 0.14em; text-transform: uppercase;
      font-size: 11px; font-family: ui-sans-serif, system-ui, sans-serif;
      background: var(--accent); color: white; padding: 4px 10px; border-radius: 999px;
    }}
    h1 {{ font-size: 32px; margin: 12px 0 8px; }}
    .sub {{ color: var(--muted); max-width: 720px; }}
    main {{ padding: 24px 8vw 80px; max-width: 980px; }}
    section {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px; margin: 18px 0; }}
    h2 {{ margin-top: 0; font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 14px; }}
    th, td {{ text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    .pill {{ font-size: 11px; font-weight: 700; letter-spacing: 0.04em; padding: 2px 8px; border-radius: 999px; }}
    .pill.pass {{ background: #e5f4ea; color: var(--pass); }}
    .pill.warn {{ background: #f8edd3; color: var(--warn); }}
    .pill.fail {{ background: #f8e3e0; color: var(--fail); }}
    .pill.skip {{ background: #eee; color: var(--muted); }}
    pre {{ white-space: pre-wrap; background: #141a20; color: #f4efe8; padding: 12px; border-radius: 8px; font-size: 13px; overflow: auto; }}
    .disclaimer, .meta {{ color: var(--muted); font-size: 14px; }}
    .prompt {{ font-weight: 600; }}
    footer {{
      margin: 28px 8vw; padding: 20px 22px; background: #14202b; color: #f6f3ee; border-radius: 12px;
      font-family: ui-sans-serif, system-ui, sans-serif;
    }}
    footer a {{ color: #f3c19a; }}
    .zh {{ font-size: 14px; color: #c8d0d6; }}
  </style>
</head>
<body>
  <header>
    <div class="ribbon">Community · not production scores</div>
    <h1>{_esc(DISPLAY_NAME)}</h1>
    <p class="sub">
      MagUp is a Generative Engine Optimization (GEO) platform.
      This file is a <strong>community</strong> report for {_esc(brand)} {_esc(domain)}.
      It is <strong>not</strong> a MagUp production detection report: no MagUp scores, no mention rates, no semantic analysis.
    </p>
    <p class="meta">Generated { _esc(now) } · magup-geo-report {_esc(__version__)}</p>
  </header>
  <main>
    {hygiene}
    {answers_html}
    {search_html}
  </main>
  <footer>
    <p><strong>Need the full MagUp GEO detection report?</strong></p>
    <p>Submit your site at <a href="{_esc(PRODUCT_URL)}">{_esc(PRODUCT_URL)}</a> for multi-model visibility monitoring and a production MagUp report.</p>
    <p class="zh">完整 LLM 可见度监测与商业报告只在 magup.ai 出具。本页为社区精简版，不含生产评分。</p>
    <p class="zh">Repo: <a href="{_esc(REPO_URL)}">{_esc(REPO_URL)}</a></p>
  </footer>
</body>
</html>
"""


def write_outputs(
    out_dir: Path,
    *,
    audit: SiteAudit | None,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    answers_name = "answers.json" if answers else None
    search_name = "search-raw.json" if search_raw else None
    if audit:
        audit_path = out_dir / "site-audit.json"
        audit_path.write_text(json.dumps(audit.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        written["site_audit"] = audit_path
    if answers:
        path = out_dir / "answers.json"
        path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
        written["answers"] = path
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
    )
    html_doc = render_html(
        audit,
        answers=answers,
        search_raw=search_raw,
        answers_path=answers_name,
        search_path=search_name,
    )
    md_path = out_dir / "community-report.md"
    html_path = out_dir / "community-report.html"
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html_doc, encoding="utf-8")
    written["markdown"] = md_path
    written["html"] = html_path
    return written
