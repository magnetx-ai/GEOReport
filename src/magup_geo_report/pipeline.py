from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magup_geo_report.analyze import analyze_answers
from magup_geo_report.dataforseo_answers import collect_dataforseo_answers
from magup_geo_report.dataforseo_raw import collect_search_raw
from magup_geo_report.geo_report import render_geo_html
from magup_geo_report.i18n import REPORT_PLATFORMS, chrome, localize_audit
from magup_geo_report.llm_raw import collect_raw_answers
from magup_geo_report.offsite import collect_offsite_signals
from magup_geo_report.prompts import fill_prompts, load_prompts
from magup_geo_report.render import write_outputs
from magup_geo_report.site_audit import audit_url, infer_brand, registrable_host

_DEFAULT_PLATFORMS = [item["value"] for item in REPORT_PLATFORMS]


@dataclass
class ReportRequest:
    url: str
    out_dir: Path
    brand: str = ""
    brand_intro: str = ""
    competitors: list[str] = field(default_factory=list)
    language: str = "en"
    platforms: list[str] = field(default_factory=lambda: list(_DEFAULT_PLATFORMS))
    write_files: bool = True
    prompts: list[str] | None = None
    prompts_file: str | None = None
    answers_only: bool = False
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    fetch_answers: bool = False


def run_report(
    req: ReportRequest,
    on_progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    def progress(step: str, percent: int, **extra: Any) -> None:
        if on_progress:
            on_progress(step=step, percent=percent, **extra)

    raw_url = req.url if "://" in req.url else "https://" + req.url
    audit = None
    if not req.answers_only:
        progress("audit", 12)
        audit = audit_url(raw_url)
        if req.brand.strip():
            audit.brand = req.brand.strip()
        localize_audit(audit, req.language)

    brand = (req.brand or (audit.brand if audit else infer_brand(raw_url, None))).strip()
    domain = audit.domain if audit else registrable_host(raw_url)
    final_url = audit.final_url if audit else raw_url

    answers = None
    prompt_texts = list(req.prompts or [])
    if not prompt_texts and req.prompts_file:
        prompt_texts = fill_prompts(load_prompts(req.prompts_file), brand=brand, domain=domain, url=final_url)
    has_dfs = bool(req.dataforseo_login and req.dataforseo_password)
    want_answers = req.fetch_answers or bool(req.llm_api_key) or (req.answers_only and has_dfs)
    if not prompt_texts and want_answers:
        prompt_texts = fill_prompts(load_prompts(None), brand=brand, domain=domain, url=final_url)
    if want_answers and prompt_texts:
        platforms = [item for item in (req.platforms or []) if item in _DEFAULT_PLATFORMS] or list(_DEFAULT_PLATFORMS)
        if has_dfs:
            total = max(1, len(prompt_texts) * len(platforms))
            progress("answers", 40, current=0, total=total)

            def on_item(index: int, count: int) -> None:
                pct = 40 + int(40 * index / max(count, 1))
                progress("answers", min(pct, 82), current=index, total=count)

            answers = collect_dataforseo_answers(
                prompts=prompt_texts,
                platforms=platforms,
                login=req.dataforseo_login or "",
                password=req.dataforseo_password or "",
                language=req.language,
                on_item=on_item,
            )
        elif req.llm_api_key:
            total = len(prompt_texts)
            progress("answers", 40, current=0, total=total)

            def on_item(index: int, count: int) -> None:
                pct = 40 + int(40 * index / max(count, 1))
                progress("answers", min(pct, 82), current=index, total=count)

            answers = collect_raw_answers(
                prompts=prompt_texts,
                api_key=req.llm_api_key,
                base_url=req.llm_base_url,
                model=req.llm_model,
                on_item=on_item,
            )
        if answers:
            answers["url"] = final_url
            answers["brand"] = brand
            answers["domain"] = domain

    search_raw = None
    offsite: dict[str, Any] | None = None
    if req.dataforseo_login and req.dataforseo_password:
        progress("search", 86)
        search_raw = collect_search_raw(
            login=req.dataforseo_login,
            password=req.dataforseo_password,
            domain=domain,
        )
        progress("search", 88)
        try:
            offsite = collect_offsite_signals(
                login=req.dataforseo_login,
                password=req.dataforseo_password,
                brand=brand,
                domain=domain,
                language=req.language,
            )
        except Exception as exc:
            offsite = {"probed": False, "error": str(exc)}

    progress("assemble", 90)

    platforms = [item for item in (req.platforms or []) if item in _DEFAULT_PLATFORMS] or list(_DEFAULT_PLATFORMS)
    analysis = None
    if answers:
        analysis = analyze_answers(
            items=list(answers.get("items") or []),
            brand=brand,
            domain=domain,
            competitors=[item.strip() for item in req.competitors if item.strip()][:4],
            platforms=platforms,
            prompts=prompt_texts,
        )
        answers["items"] = analysis.get("items") or answers.get("items")

    progress("assemble", 94)

    meta = {
        "language": req.language,
        "brand": brand,
        "brand_intro": req.brand_intro.strip(),
        "competitors": [item.strip() for item in req.competitors if item.strip()][:4],
        "platforms": platforms,
        "url": raw_url,
        "prompts": prompt_texts,
        "strings": chrome(req.language),
        "analysis": analysis,
        "offsite": offsite or {},
    }
    report_html = render_geo_html(
        audit,
        answers=answers,
        search_raw=search_raw,
        analysis=analysis,
        meta=meta,
    )
    files: dict[str, str] = {}
    if req.write_files:
        written = write_outputs(
            req.out_dir,
            audit=audit,
            answers=answers,
            search_raw=search_raw,
            meta=meta,
        )
        files = {key: str(path) for key, path in written.items()}
    return {
        "brand": brand,
        "domain": domain,
        "url": final_url,
        "language": req.language,
        "platforms": platforms,
        "meta": meta,
        "audit": audit.to_dict() if audit else None,
        "answers": answers,
        "analysis": analysis,
        "report_html": report_html,
        "search_raw": search_raw,
        "files": files,
    }
