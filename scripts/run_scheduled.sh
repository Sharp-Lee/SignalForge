#!/usr/bin/env bash
set -u
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_project_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) printf '%s/%s\n' "$PROJECT_ROOT" "$1" ;;
  esac
}

RUNTIME_CONFIG="${NEWS_CONFIG_FILE:-"$PROJECT_ROOT/.local/runtime.env"}"
RUNTIME_CONFIG="$(resolve_project_path "$RUNTIME_CONFIG")"

if [ -r "$RUNTIME_CONFIG" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$RUNTIME_CONFIG"
  set +a
fi

KEY_FILE="${NEWS_KEYS_FILE:-"$PROJECT_ROOT/.local/keys.env"}"
STORE_PATH="${NEWS_STORE_PATH:-"$PROJECT_ROOT/.local/news-data/live-store.db"}"
LOG_DIR="${NEWS_LOG_DIR:-"$PROJECT_ROOT/.local/news-data/logs"}"
RSS_FEED_URL="${RSS_FEED_URL:-${NEWS_RSS_FEED_URL:-"https://www.servethehome.com/feed/"}}"
PYTHON_BIN="${NEWS_PYTHON:-"/opt/homebrew/opt/python@3.12/libexec/bin/python3"}"
PROXY_URL="${NEWS_HTTP_PROXY:-"http://127.0.0.1:6152"}"
SHOW_STORE_AFTER_RUN="${NEWS_SHOW_STORE_AFTER_RUN:-"1"}"

KEY_FILE="$(resolve_project_path "$KEY_FILE")"
STORE_PATH="$(resolve_project_path "$STORE_PATH")"
LOG_DIR="$(resolve_project_path "$LOG_DIR")"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

mkdir -p "$(dirname "$STORE_PATH")" "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%F).log"

(
  echo "========================================================================"
  echo "scheduled news pipeline start: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "project_root=$PROJECT_ROOT"
  echo "store=$STORE_PATH"
  echo "feed=$RSS_FEED_URL"
  echo "log=$LOG_FILE"
  echo "runtime_config=$RUNTIME_CONFIG"

  if [ ! -r "$KEY_FILE" ]; then
    echo "missing key file: $KEY_FILE"
    exit 2
  fi

  if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo "python3 not found"
    exit 127
  fi

  set -a
  # shellcheck disable=SC1090
  . "$KEY_FILE"
  set +a

  export HTTP_PROXY="${HTTP_PROXY:-$PROXY_URL}"
  export HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_URL}"
  export http_proxy="${http_proxy:-$HTTP_PROXY}"
  export https_proxy="${https_proxy:-$HTTPS_PROXY}"
  export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}"
  export no_proxy="${no_proxy:-$NO_PROXY}"
  export RSS_FEED_URL

  echo "python=$PYTHON_BIN"
  echo "proxy=enabled"
  "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --pipeline --store "$STORE_PATH"
  rc=$?
  if [ "$rc" -eq 0 ] && [ "$SHOW_STORE_AFTER_RUN" != "0" ]; then
    echo "scheduled news pipeline store summary:"
    "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --show-store "$STORE_PATH"
    rc=$?
  fi
  echo "scheduled news pipeline exit_code=$rc"
  exit "$rc"
) 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{10,}/***REDACTED***/g' | tee -a "$LOG_FILE"

exit "${PIPESTATUS[0]}"
