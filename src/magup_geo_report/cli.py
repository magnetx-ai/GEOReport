from __future__ import annotations

import argparse
import sys
from pathlib import Path

from magup_geo_report import DISPLAY_NAME, PRODUCT_URL, __version__
from magup_geo_report.envutil import env_get, load_dotenv
from magup_geo_report.pipeline import ReportRequest, run_report


def _env(name: str, *aliases: str) -> str | None:
    return env_get(name, *aliases)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="magup-geo-report",
        description=(
            f"{DISPLAY_NAME}. Open-source: configure your own LLM and search keys. "
            f"Contact us for a free hosted run: {PRODUCT_URL}"
        ),
    )
    parser.add_argument("--url", help="Site URL or domain (required unless serving)")
    parser.add_argument("--out", default="./out", help="Output directory (default: ./out)")
    parser.add_argument("--brand", default="", help="Brand display name")
    parser.add_argument("--language", default="en", help="Report language (en, zh-Hans, ja, …)")
    parser.add_argument("--answers-only", action="store_true", help="Skip site hygiene; write raw answers only (LLM or DataForSEO)")
    parser.add_argument("--prompts-file", help="Optional prompt list (one per line). Default: 8 built-in prompts")
    parser.add_argument("--llm-api-key", help="OpenAI-compatible API key (or MAGUP_LLM_API_KEY / OPENAI_API_KEY)")
    parser.add_argument("--llm-base-url", default=None, help="Chat Completions root (default MAGUP_LLM_BASE_URL or OpenAI)")
    parser.add_argument("--llm-model", default=None, help="Model id (default MAGUP_LLM_MODEL or gpt-4o-mini)")
    parser.add_argument("--dataforseo-login", help="DataForSEO login (or DATAFORSEO_LOGIN)")
    parser.add_argument("--dataforseo-password", help="DataForSEO password (or DATAFORSEO_PASSWORD)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def serve_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="magup-geo-report serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("Install web extras: pip install -e '.[web]'", file=sys.stderr)
        return 2
    from magup_geo_report.webapp import app

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def report_main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if not args.url:
        build_parser().error("--url is required")
    llm_key = args.llm_api_key or _env("MAGUP_LLM_API_KEY", "OPENAI_API_KEY")
    dfs_login = args.dataforseo_login or _env("DATAFORSEO_LOGIN")
    dfs_password = args.dataforseo_password or _env("DATAFORSEO_PASSWORD")
    has_dfs = bool(dfs_login and dfs_password)
    if args.answers_only and not llm_key and not has_dfs:
        print("--answers-only requires an LLM key or DataForSEO credentials", file=sys.stderr)
        return 2
    result = run_report(
        ReportRequest(
            url=args.url,
            out_dir=Path(args.out),
            brand=args.brand,
            language=args.language,
            prompts_file=args.prompts_file,
            answers_only=args.answers_only,
            fetch_answers=bool(llm_key or has_dfs),
            llm_api_key=llm_key,
            llm_base_url=args.llm_base_url or _env("MAGUP_LLM_BASE_URL") or "https://api.openai.com/v1",
            llm_model=args.llm_model or _env("MAGUP_LLM_MODEL") or "gpt-4o-mini",
            dataforseo_login=dfs_login,
            dataforseo_password=dfs_password,
        )
    )
    print("Wrote:")
    for key, path in result["files"].items():
        print(f"  {key}: {path}")
    print(f"\nOpen-source self-hosted run. Contact us for a free generation: {PRODUCT_URL}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "serve":
        return serve_main(argv[1:])
    return report_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
