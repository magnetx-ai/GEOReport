from __future__ import annotations

import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from magup_geo_report import DISPLAY_NAME, PRODUCT_URL, __version__
from magup_geo_report.envutil import env_status, load_dotenv, resolve_keys
from magup_geo_report.i18n import REPORT_LANGUAGES, REPORT_PLATFORMS
from magup_geo_report.pipeline import ReportRequest, run_report
from magup_geo_report.prompt_gen import (
    DEFAULT_COUNT,
    MAX_PROMPTS,
    generate_prompts_from_templates,
    generate_prompts_with_llm,
)
from magup_geo_report.site_audit import infer_brand, registrable_host
from magup_geo_report.site_brief import resolve_brand_intro

WEB_DIR = Path(__file__).parent / "web"
JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()

app = FastAPI(title=DISPLAY_NAME, version=__version__)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
load_dotenv()


class KeysIn(BaseModel):
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    dataforseo_login: str | None = None
    dataforseo_password: str | None = None


class PromptGenIn(KeysIn):
    url: str
    brand: str
    brand_intro: str = ""
    competitors: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["zh-Hans"])
    total: int = DEFAULT_COUNT
    unbranded_ratio: int = 50
    extra_notes: str = ""
    use_llm: bool = False


class SiteBriefIn(KeysIn):
    url: str
    brand: str = ""
    brand_intro: str = ""


class JobIn(KeysIn):
    url: str
    brand: str
    brand_intro: str = ""
    competitors: list[str] = Field(default_factory=list)
    language: str = "zh-Hans"
    platforms: list[str] = Field(default_factory=lambda: [item["value"] for item in REPORT_PLATFORMS])
    prompts: list[str] = Field(default_factory=list)
    fetch_answers: bool = False


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "name": DISPLAY_NAME,
        "version": __version__,
        "productUrl": PRODUCT_URL,
        "languages": REPORT_LANGUAGES,
        "platforms": REPORT_PLATFORMS,
        "maxPrompts": MAX_PROMPTS,
        "defaultCount": DEFAULT_COUNT,
        "env": env_status(),
    }


@app.post("/api/site-brief")
def create_site_brief(body: SiteBriefIn) -> dict[str, Any]:
    url = body.url.strip()
    brand = (body.brand or "").strip()
    if not url:
        raise HTTPException(400, "url is required")
    raw = url if "://" in url else "https://" + url
    keys = resolve_keys(
        llm_api_key=body.llm_api_key,
        llm_base_url=body.llm_base_url,
        llm_model=body.llm_model,
        dataforseo_login=body.dataforseo_login,
        dataforseo_password=body.dataforseo_password,
    )
    resolved = resolve_brand_intro(
        url=raw,
        brand=brand,
        existing=body.brand_intro,
        llm_api_key=keys["llm_api_key"],
        llm_base_url=keys["llm_base_url"] or "https://api.openai.com/v1",
        llm_model=keys["llm_model"] or "gpt-4o-mini",
    )
    return {
        "intro": resolved["intro"],
        "source": resolved["source"],
        "brand": resolved["brand"],
        "domain": (resolved.get("brief") or {}).get("domain") or registrable_host(raw),
    }


@app.post("/api/prompts")
def create_prompts(body: PromptGenIn) -> dict[str, Any]:
    url = body.url.strip()
    brand = body.brand.strip()
    if not url or not brand:
        raise HTTPException(400, "url and brand are required")
    raw = url if "://" in url else "https://" + url
    domain = registrable_host(raw) or infer_brand(raw, None)
    langs = body.languages or ["en"]
    keys = resolve_keys(
        llm_api_key=body.llm_api_key,
        llm_base_url=body.llm_base_url,
        llm_model=body.llm_model,
        dataforseo_login=body.dataforseo_login,
        dataforseo_password=body.dataforseo_password,
    )
    try:
        resolved = resolve_brand_intro(
            url=raw,
            brand=brand,
            existing=body.brand_intro,
            llm_api_key=None,
            llm_base_url=keys["llm_base_url"] or "https://api.openai.com/v1",
            llm_model=keys["llm_model"] or "gpt-4o-mini",
        )
        intro = resolved["intro"]
        if body.use_llm and keys["llm_api_key"]:
            items = generate_prompts_with_llm(
                brand=brand,
                domain=domain,
                url=raw,
                brand_intro=intro,
                languages=langs,
                total=body.total,
                unbranded_ratio=body.unbranded_ratio,
                competitors=body.competitors,
                extra_notes=body.extra_notes,
                api_key=keys["llm_api_key"],
                base_url=keys["llm_base_url"] or "https://api.openai.com/v1",
                model=keys["llm_model"] or "gpt-4o-mini",
            )
            source = "llm"
        else:
            items = generate_prompts_from_templates(
                brand=brand,
                domain=domain,
                url=raw,
                languages=langs,
                total=body.total,
                unbranded_ratio=body.unbranded_ratio,
                competitors=body.competitors,
                brand_intro=intro,
                extra_notes=body.extra_notes,
            )
            source = "templates"
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "source": source,
        "prompts": items,
        "brand_intro": intro,
        "intro_source": resolved["source"],
    }


@app.post("/api/jobs")
def create_job(body: JobIn) -> dict[str, Any]:
    url = body.url.strip()
    brand = body.brand.strip()
    if not url or not brand:
        raise HTTPException(400, "url and brand are required")
    job_id = uuid.uuid4().hex[:12]
    out_dir = Path(tempfile.gettempdir()) / "magup-geo-report" / job_id
    record = {
        "id": job_id,
        "status": "queued",
        "message": "queued",
        "step": "queued",
        "progress": 0,
        "step_current": None,
        "step_total": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
        "files": {},
        "brand": brand,
        "url": url,
        "language": body.language,
        "platforms": body.platforms,
    }
    with LOCK:
        JOBS[job_id] = record
    thread = threading.Thread(target=_run_job, args=(job_id, body, out_dir), daemon=True)
    thread.start()
    return {"job": record}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with LOCK:
        record = JOBS.get(job_id)
    if not record:
        raise HTTPException(404, "job not found")
    return {"job": record}


@app.get("/api/jobs/{job_id}/html")
def get_job_html(job_id: str) -> FileResponse:
    with LOCK:
        record = JOBS.get(job_id)
    if not record:
        raise HTTPException(404, "job not found")
    html_path = record.get("files", {}).get("html")
    if not html_path or not Path(html_path).is_file():
        raise HTTPException(404, "report not ready")
    return FileResponse(html_path, media_type="text/html")


def _run_job(job_id: str, body: JobIn, out_dir: Path) -> None:
    def set_status(status: str, message: str, **extra: Any) -> None:
        with LOCK:
            JOBS[job_id]["status"] = status
            JOBS[job_id]["message"] = message
            JOBS[job_id].update(extra)

    def on_progress(*, step: str, percent: int, **extra: Any) -> None:
        payload: dict[str, Any] = {
            "step": step,
            "progress": max(0, min(100, int(percent))),
            "step_current": extra.get("current"),
            "step_total": extra.get("total"),
        }
        set_status("running", step, **payload)

    set_status("running", "queued", step="queued", progress=4)
    try:
        keys = resolve_keys(
            llm_api_key=body.llm_api_key,
            llm_base_url=body.llm_base_url,
            llm_model=body.llm_model,
            dataforseo_login=body.dataforseo_login,
            dataforseo_password=body.dataforseo_password,
        )
        resolved = resolve_brand_intro(
            url=body.url,
            brand=body.brand,
            existing=body.brand_intro,
        )
        has_dfs = bool(keys["dataforseo_login"] and keys["dataforseo_password"])
        fetch_answers = bool(body.fetch_answers and body.prompts and (keys["llm_api_key"] or has_dfs))
        result = run_report(
            ReportRequest(
                url=body.url,
                out_dir=out_dir,
                brand=body.brand,
                brand_intro=resolved["intro"],
                competitors=body.competitors,
                language=body.language,
                platforms=body.platforms,
                prompts=body.prompts or None,
                write_files=False,
                fetch_answers=fetch_answers,
                llm_api_key=keys["llm_api_key"] if fetch_answers else None,
                llm_base_url=keys["llm_base_url"] or "https://api.openai.com/v1",
                llm_model=keys["llm_model"] or "gpt-4o-mini",
                dataforseo_login=keys["dataforseo_login"],
                dataforseo_password=keys["dataforseo_password"],
            ),
            on_progress=on_progress,
        )
        set_status("done", "done", step="done", progress=100, result=result, step_current=None, step_total=None)
    except Exception as exc:
        set_status("error", str(exc), error=str(exc))
