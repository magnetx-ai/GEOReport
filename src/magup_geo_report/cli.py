from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from magup_geo_report import DISPLAY_NAME, PRODUCT_URL, __version__
from magup_geo_report.dataforseo_raw import collect_search_raw
from magup_geo_report.llm_raw import collect_raw_answers
from magup_geo_report.prompts import fill_prompts, load_prompts
from magup_geo_report.render import write_outputs
from magup_geo_report.site_audit import audit_url, infer_brand, registrable_host


def _env(name: str, *aliases: str) -> str | None:
    for key in (name, *aliases):
        value = os.environ.get(key)
        if value:
            return value
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magup-geo-report",
        description=(
            f"{DISPLAY_NAME}: site GEO hygiene by default. "
            "Optional official LLM / DataForSEO keys dump raw payloads only. "
            f"Not MagUp production detection. Full reports: {PRODUCT_URL}"
        ),
    )
    parser.add_argument("--url", required=True, help="Site URL or domain")
    parser.add_argument("--out", default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--answers-only", action="store_true", help="Skip site hygiene; write raw answers only")
    parser.add_argument("--prompts-file", help="Optional prompt list (one per line). Default: 8 built-in prompts")
    parser.add_argument("--llm-api-key", help="OpenAI-compatible API key (or MAGUP_LLM_API_KEY / OPENAI_API_KEY)")
    parser.add_argument("--llm-base-url", default=None, help="Chat Completions root (default MAGUP_LLM_BASE_URL or OpenAI)")
    parser.add_argument("--llm-model", default=None, help="Model id (default MAGUP_LLM_MODEL or gpt-4o-mini)")
    parser.add_argument("--dataforseo-login", help="DataForSEO login (or DATAFORSEO_LOGIN)")
    parser.add_argument("--dataforseo-password", help="DataForSEO password (or DATAFORSEO_PASSWORD)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    llm_key = args.llm_api_key or _env("MAGUP_LLM_API_KEY", "OPENAI_API_KEY")
    dfs_login = args.dataforseo_login or _env("DATAFORSEO_LOGIN")
    dfs_password = args.dataforseo_password or _env("DATAFORSEO_PASSWORD")
    llm_base = args.llm_base_url or _env("MAGUP_LLM_BASE_URL") or "https://api.openai.com/v1"
    llm_model = args.llm_model or _env("MAGUP_LLM_MODEL") or "gpt-4o-mini"

    if args.answers_only and not llm_key:
        print("--answers-only requires --llm-api-key (or MAGUP_LLM_API_KEY)", file=sys.stderr)
        return 2

    audit = None
    if not args.answers_only:
        print(f"Auditing {args.url} …")
        audit = audit_url(args.url)

    answers = None
    if llm_key:
        if audit:
            brand, domain, url = audit.brand, audit.domain, audit.final_url
        else:
            raw = args.url if "://" in args.url else "https://" + args.url
            domain = registrable_host(raw)
            brand = infer_brand(raw, None)
            url = raw
        prompts = fill_prompts(load_prompts(args.prompts_file), brand=brand, domain=domain, url=url)
        print(f"Fetching {len(prompts)} raw LLM answers via official API (no analysis) …")
        answers = collect_raw_answers(
            prompts=prompts,
            api_key=llm_key,
            base_url=llm_base,
            model=llm_model,
        )
        answers["url"] = url
        answers["brand"] = brand
        answers["domain"] = domain

    search_raw = None
    if dfs_login and dfs_password:
        domain = audit.domain if audit else registrable_host(args.url if "://" in args.url else "https://" + args.url)
        print(f"Fetching raw DataForSEO SERP JSON for {domain} (no Search Profile) …")
        search_raw = collect_search_raw(login=dfs_login, password=dfs_password, domain=domain)
    elif dfs_login or dfs_password:
        print("DataForSEO skipped: need both login and password", file=sys.stderr)

    out_dir = Path(args.out)
    written = write_outputs(out_dir, audit=audit, answers=answers, search_raw=search_raw)
    print("Wrote:")
    for key, path in written.items():
        print(f"  {key}: {path}")
    print(f"\nCommunity report only. Production MagUp GEO reports: {PRODUCT_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
