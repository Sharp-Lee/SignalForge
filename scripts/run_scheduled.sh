#!/usr/bin/env bash
set -u
set -o pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_project_path() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    ~/*) printf '%s/%s\n' "$HOME" "${1#~/}" ;;
    *) printf '%s/%s\n' "$PROJECT_ROOT" "$1" ;;
  esac
}

RUNTIME_CONFIG="${NEWS_CONFIG_FILE:-"$PROJECT_ROOT/.local/runtime.env"}"
RUNTIME_CONFIG="$(resolve_project_path "$RUNTIME_CONFIG")"

ENV_NEWS_KEYS_FILE_SET="${NEWS_KEYS_FILE+x}"
ENV_NEWS_KEYS_FILE="${NEWS_KEYS_FILE-}"
ENV_NEWS_STORE_PATH_SET="${NEWS_STORE_PATH+x}"
ENV_NEWS_STORE_PATH="${NEWS_STORE_PATH-}"
ENV_NEWS_LOG_DIR_SET="${NEWS_LOG_DIR+x}"
ENV_NEWS_LOG_DIR="${NEWS_LOG_DIR-}"
ENV_NEWS_RUN_MODE_SET="${NEWS_RUN_MODE+x}"
ENV_NEWS_RUN_MODE="${NEWS_RUN_MODE-}"
ENV_RSS_FEED_URL_SET="${RSS_FEED_URL+x}"
ENV_RSS_FEED_URL="${RSS_FEED_URL-}"
ENV_NEWS_RSS_FEED_URL_SET="${NEWS_RSS_FEED_URL+x}"
ENV_NEWS_RSS_FEED_URL="${NEWS_RSS_FEED_URL-}"
ENV_NEWS_RSS_SOURCES_FILE_SET="${NEWS_RSS_SOURCES_FILE+x}"
ENV_NEWS_RSS_SOURCES_FILE="${NEWS_RSS_SOURCES_FILE-}"
ENV_NEWS_PYTHON_SET="${NEWS_PYTHON+x}"
ENV_NEWS_PYTHON="${NEWS_PYTHON-}"
ENV_NEWS_HTTP_PROXY_SET="${NEWS_HTTP_PROXY+x}"
ENV_NEWS_HTTP_PROXY="${NEWS_HTTP_PROXY-}"
ENV_NEWS_SHOW_STORE_AFTER_RUN_SET="${NEWS_SHOW_STORE_AFTER_RUN+x}"
ENV_NEWS_SHOW_STORE_AFTER_RUN="${NEWS_SHOW_STORE_AFTER_RUN-}"
ENV_NEWS_ANALYZE_TOP_K_SET="${NEWS_ANALYZE_TOP_K+x}"
ENV_NEWS_ANALYZE_TOP_K="${NEWS_ANALYZE_TOP_K-}"
ENV_NEWS_PENDING_MAX_AGE_DAYS_SET="${NEWS_PENDING_MAX_AGE_DAYS+x}"
ENV_NEWS_PENDING_MAX_AGE_DAYS="${NEWS_PENDING_MAX_AGE_DAYS-}"
ENV_NEWS_MAX_ANALYSIS_ATTEMPTS_SET="${NEWS_MAX_ANALYSIS_ATTEMPTS+x}"
ENV_NEWS_MAX_ANALYSIS_ATTEMPTS="${NEWS_MAX_ANALYSIS_ATTEMPTS-}"

if [ -r "$RUNTIME_CONFIG" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$RUNTIME_CONFIG"
  set +a
fi

[ "$ENV_NEWS_KEYS_FILE_SET" = "x" ] && NEWS_KEYS_FILE="$ENV_NEWS_KEYS_FILE"
[ "$ENV_NEWS_STORE_PATH_SET" = "x" ] && NEWS_STORE_PATH="$ENV_NEWS_STORE_PATH"
[ "$ENV_NEWS_LOG_DIR_SET" = "x" ] && NEWS_LOG_DIR="$ENV_NEWS_LOG_DIR"
[ "$ENV_NEWS_RUN_MODE_SET" = "x" ] && NEWS_RUN_MODE="$ENV_NEWS_RUN_MODE"
[ "$ENV_RSS_FEED_URL_SET" = "x" ] && RSS_FEED_URL="$ENV_RSS_FEED_URL"
[ "$ENV_NEWS_RSS_FEED_URL_SET" = "x" ] && NEWS_RSS_FEED_URL="$ENV_NEWS_RSS_FEED_URL"
[ "$ENV_NEWS_RSS_SOURCES_FILE_SET" = "x" ] && NEWS_RSS_SOURCES_FILE="$ENV_NEWS_RSS_SOURCES_FILE"
[ "$ENV_NEWS_PYTHON_SET" = "x" ] && NEWS_PYTHON="$ENV_NEWS_PYTHON"
[ "$ENV_NEWS_HTTP_PROXY_SET" = "x" ] && NEWS_HTTP_PROXY="$ENV_NEWS_HTTP_PROXY"
[ "$ENV_NEWS_SHOW_STORE_AFTER_RUN_SET" = "x" ] && NEWS_SHOW_STORE_AFTER_RUN="$ENV_NEWS_SHOW_STORE_AFTER_RUN"
[ "$ENV_NEWS_ANALYZE_TOP_K_SET" = "x" ] && NEWS_ANALYZE_TOP_K="$ENV_NEWS_ANALYZE_TOP_K"
[ "$ENV_NEWS_PENDING_MAX_AGE_DAYS_SET" = "x" ] && NEWS_PENDING_MAX_AGE_DAYS="$ENV_NEWS_PENDING_MAX_AGE_DAYS"
[ "$ENV_NEWS_MAX_ANALYSIS_ATTEMPTS_SET" = "x" ] && NEWS_MAX_ANALYSIS_ATTEMPTS="$ENV_NEWS_MAX_ANALYSIS_ATTEMPTS"

KEY_FILE="${NEWS_KEYS_FILE:-"$HOME/.config/news-llm/keys.env"}"
STORE_PATH="${NEWS_STORE_PATH:-"$PROJECT_ROOT/.local/news-data/live-store.db"}"
LOG_DIR="${NEWS_LOG_DIR:-"$PROJECT_ROOT/.local/news-data/logs"}"
RUN_MODE="${NEWS_RUN_MODE:-"pipeline"}"
RSS_FEED_URL="${RSS_FEED_URL:-${NEWS_RSS_FEED_URL:-""}}"
PYTHON_BIN="${NEWS_PYTHON:-"/opt/homebrew/opt/python@3.12/libexec/bin/python3"}"
PROXY_URL="${NEWS_HTTP_PROXY:-"http://127.0.0.1:6152"}"
SHOW_STORE_AFTER_RUN="${NEWS_SHOW_STORE_AFTER_RUN:-"1"}"
ANALYZE_TOP_K="${NEWS_ANALYZE_TOP_K:-"5"}"
PENDING_MAX_AGE_DAYS="${NEWS_PENDING_MAX_AGE_DAYS:-"7"}"
MAX_ANALYSIS_ATTEMPTS="${NEWS_MAX_ANALYSIS_ATTEMPTS:-"2"}"

KEY_FILE="$(resolve_project_path "$KEY_FILE")"
STORE_PATH="$(resolve_project_path "$STORE_PATH")"
LOG_DIR="$(resolve_project_path "$LOG_DIR")"
if [ "${NEWS_RSS_SOURCES_FILE:-}" != "" ]; then
  NEWS_RSS_SOURCES_FILE="$(resolve_project_path "$NEWS_RSS_SOURCES_FILE")"
fi

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi

mkdir -p "$(dirname "$KEY_FILE")" "$(dirname "$STORE_PATH")" "$LOG_DIR"
LOG_FILE="$LOG_DIR/$(date +%F).log"
LOCK_DIR="$LOG_DIR/.scheduled.lock"

(
  echo "========================================================================"
  echo "scheduled news pipeline start: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "project_root=$PROJECT_ROOT"
  echo "mode=$RUN_MODE"
  echo "store=$STORE_PATH"
  if [ -n "$RSS_FEED_URL" ]; then
    echo "feed=$RSS_FEED_URL"
  else
    echo "sources_file=${NEWS_RSS_SOURCES_FILE:-config/rss_sources.example.json}"
  fi
  echo "log=$LOG_FILE"
  echo "runtime_config=$RUNTIME_CONFIG"

  if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo "python3 not found"
    exit 127
  fi

  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "another scheduled run is active; exiting without work"
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

  if [ "$RUN_MODE" != "capture" ]; then
    if [ ! -r "$KEY_FILE" ]; then
      echo "missing key file: $KEY_FILE"
      echo "create it outside the public repo, for example: $HOME/.config/news-llm/keys.env"
      echo "see config/runtime.env.example and openspec/changes/operationalize-scheduled-run/README.md"
      exit 2
    fi
    set -a
    # shellcheck disable=SC1090
    . "$KEY_FILE"
    set +a
  fi

  export HTTP_PROXY="${HTTP_PROXY:-$PROXY_URL}"
  export HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_URL}"
  export http_proxy="${http_proxy:-$HTTP_PROXY}"
  export https_proxy="${https_proxy:-$HTTPS_PROXY}"
  export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}"
  export no_proxy="${no_proxy:-$NO_PROXY}"
  if [ -n "$RSS_FEED_URL" ]; then
    export RSS_FEED_URL
  else
    unset RSS_FEED_URL
  fi
  if [ "${NEWS_RSS_SOURCES_FILE:-}" != "" ]; then
    export NEWS_RSS_SOURCES_FILE
  fi

  echo "python=$PYTHON_BIN"
  echo "proxy=enabled"
  case "$RUN_MODE" in
    capture)
      "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --capture --store "$STORE_PATH"
      ;;
    analyze)
      "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" \
        --analyze \
        --store "$STORE_PATH" \
        --top-k "$ANALYZE_TOP_K" \
        --pending-max-age-days "$PENDING_MAX_AGE_DAYS" \
        --max-attempts "$MAX_ANALYSIS_ATTEMPTS"
      ;;
    pipeline)
      "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" \
        --pipeline \
        --store "$STORE_PATH" \
        --top-k "$ANALYZE_TOP_K" \
        --pending-max-age-days "$PENDING_MAX_AGE_DAYS" \
        --max-attempts "$MAX_ANALYSIS_ATTEMPTS"
      ;;
    *)
      echo "unknown NEWS_RUN_MODE: $RUN_MODE"
      exit 2
      ;;
  esac
  rc=$?
  if [ "$rc" -eq 0 ] && [ "$SHOW_STORE_AFTER_RUN" != "0" ]; then
    echo "scheduled news $RUN_MODE store summary:"
    "$PYTHON_BIN" "$PROJECT_ROOT/scripts/run_live.py" --show-store "$STORE_PATH"
    rc=$?
  fi
  echo "scheduled news $RUN_MODE exit_code=$rc"
  exit "$rc"
) 2>&1 | sed -E 's/sk-[A-Za-z0-9_-]{10,}/***REDACTED***/g' | tee -a "$LOG_FILE"

exit "${PIPESTATUS[0]}"
