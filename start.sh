#!/usr/bin/env bash
# MagUp GEO Report — one-click local start.
# Default: install deps (if needed) and open the web UI.
# Pass --url to generate a report from the CLI instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HOST="${MAGUP_HOST:-127.0.0.1}"
PORT="${MAGUP_PORT:-8787}"
OPEN_BROWSER=1
MODE="serve"
CLI_ARGS=()

usage() {
  cat <<'EOF'
MagUp GEO Report

Usage:
  ./start.sh                         Start the local web UI (default)
  ./start.sh --port 9000             Start the UI on a custom port
  ./start.sh --no-open               Start the UI without opening a browser
  ./start.sh --url https://example.com [cli flags...]
                                     Generate a report from the command line

Examples:
  ./start.sh
  ./start.sh --url https://example.com --out ./out --language en --brand Acme
  ./start.sh --url https://example.com --llm-api-key "$MAGUP_LLM_API_KEY"

Requires Python 3.10+. Optional keys go in .env (see env.example).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --no-open)
      OPEN_BROWSER=0
      shift
      ;;
    --host)
      [[ -n "${2:-}" ]] || die "--host needs a value"
      HOST="$2"
      shift 2
      ;;
    --port)
      [[ -n "${2:-}" ]] || die "--port needs a value"
      PORT="$2"
      shift 2
      ;;
    --url)
      [[ -n "${2:-}" ]] || die "--url needs a value"
      MODE="cli"
      CLI_ARGS+=("$1" "$2")
      shift 2
      ;;
    serve)
      MODE="serve"
      shift
      ;;
    *)
      MODE="cli"
      CLI_ARGS+=("$1")
      shift
      ;;
  esac
done

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

find_python() {
  local candidate version
  for candidate in "${PYTHON:-}" python3.13 python3.12 python3.11 python3.10 python3 python; do
    [[ -n "$candidate" ]] || continue
    if command -v "$candidate" >/dev/null 2>&1; then
      version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
      if [[ -n "$version" ]] && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)" || die "Python 3.10+ is required. Install Python, then re-run ./start.sh"

if [[ ! -d "$ROOT/.venv" ]]; then
  log "Creating virtualenv with $PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

if ! python -c 'import magup_geo_report' >/dev/null 2>&1; then
  log "Installing MagUp GEO Report"
  python -m pip install --upgrade pip
  python -m pip install -e "$ROOT"
fi

if [[ ! -f "$ROOT/.env" && -f "$ROOT/env.example" ]]; then
  cp "$ROOT/env.example" "$ROOT/.env"
  log "Wrote .env from env.example — add LLM or DataForSEO keys there to capture live answers"
fi

if [[ "$MODE" == "cli" ]]; then
  log "Generating report"
  exec magup-geo-report "${CLI_ARGS[@]}"
fi

URL="http://${HOST}:${PORT}"
log "Starting MagUp GEO Report at ${URL}"

if [[ "$OPEN_BROWSER" -eq 1 ]]; then
  (
    sleep 1.2
    if command -v open >/dev/null 2>&1; then
      open "$URL" >/dev/null 2>&1 || true
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$URL" >/dev/null 2>&1 || true
    elif command -v wslview >/dev/null 2>&1; then
      wslview "$URL" >/dev/null 2>&1 || true
    fi
  ) &
fi

exec magup-geo-report serve --host "$HOST" --port "$PORT"
