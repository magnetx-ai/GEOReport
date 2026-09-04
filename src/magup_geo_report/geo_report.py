from __future__ import annotations

from typing import Any

from magup_geo_report.magup_report.dashboard import build_dashboard
from magup_geo_report.magup_report.renderer import render_html
from magup_geo_report.site_audit import SiteAudit


def render_geo_html(
    audit: SiteAudit | None,
    *,
    answers: dict[str, Any] | None,
    search_raw: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    meta: dict[str, Any] | None = None,
) -> str:
    """Render the magup_v3 masked-sales dashboard HTML (Section 12 omitted)."""
    del search_raw  # Search SERP dump is not a Magup dashboard input.
    data = build_dashboard(audit=audit, answers=answers, analysis=analysis, meta=meta)
    language = str((meta or {}).get("language") or data.get("delivery_language") or "zh-Hans")
    return render_html(data, delivery_language=language)
