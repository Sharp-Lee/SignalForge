#!/usr/bin/env python3
"""First live run harness — point the real LlmReasoner at a real provider
(DeepSeek or a relay/中转站 Claude endpoint) and print the first real thesis.

Keys are read from env vars ONLY and are NEVER printed: every line of output,
including exception tracebacks, is passed through a redactor that masks any
known key value. Run it via:

    set -a; source ~/.config/news-llm/keys.env; set +a
    python scripts/run_live.py --author deepseek
    python scripts/run_live.py --author relay
    python scripts/run_live.py --author deepseek --reviewer relay   # mixed

The first run uses a built-in known-good signal so a failure clearly points at
the LLM/transport/schema path, not at RSS. Swap to live RSS once this is green.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis_orchestration.core import LlmReasoner, ReasonerIdentity, analyze  # noqa: E402
from llm_provider.transport import (  # noqa: E402
    AnthropicCompletion,
    LlmProviderError,
    OpenAICompatibleCompletion,
)
from news_contracts.storage import ContractStore  # noqa: E402
from news_contracts.validation import validate_target, validate_thesis  # noqa: E402
from pipeline_orchestration import analyze_pending, capture_sources, run_pipeline, signal_analysis_counts  # noqa: E402
from market_data import (  # noqa: E402
    RealPriceLookup,
    build_default_provider_chain,
    build_default_universe,
)
from source_ingestion.adapters.rss import RssAtomAdapter  # noqa: E402
from source_ingestion.feed_config import build_rss_adapters, load_rss_source_configs  # noqa: E402
from source_ingestion.fetchers.rss import RssHttpFetcher  # noqa: E402
from target_generation import LlmTargetProposer, StubPriceLookup, propose_targets  # noqa: E402
from scripts.generate_digest import generate_digest  # noqa: E402

SECRET_ENV_VARS = ("DEEPSEEK_API_KEY", "RELAY_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TUSHARE_TOKEN")

SIGNAL = {
    "id": "sig-ai-server-1",
    "source": {
        "id": "rss:semis",
        "name": "Global Semis RSS",
        "published_at": "2026-06-09T08:00:00Z",
        "url": "https://example.com/ai-server-supply",
    },
    "title": "AI server backlog expands 25% as power modules tighten",
    "body": "Supplier checks show AI server backlog expanded 25% and power module lead times moved from 6 to 14 weeks.",
    "signal_origin": "news",
    "type_tag": "supply_demand_bottleneck",
    "triage": {"excluded": False, "reasons": [], "strategy": "zh_cn_heuristic_v0"},
    "raw_payload": {"source": "rss"},
}

# TEST FIXTURE, not production: authoritative symbol-name map for the AI-server supply-chain smoke.
TARGET_SYMBOL_UNIVERSE = {
    "300308.SZ": "Zhongji Innolight",
    "300502.SZ": "Eoptolink Technology",
    "002463.SZ": "Wus Printed Circuit",
    "002851.SZ": "Shenzhen Megmeet Electrical",
}

# TEST FIXTURE, not production: stub price layer until the market-data layer exists.
TARGET_PRICE_CHANGES = {
    "300308.SZ": 0.18,
    "300502.SZ": 0.12,
    "002463.SZ": 0.08,
    "002851.SZ": 0.04,
}


def _secret_values() -> list[str]:
    return [v for k in SECRET_ENV_VARS if (v := os.environ.get(k))]


def redact(text: str) -> str:
    for value in _secret_values():
        if value:
            text = text.replace(value, "***REDACTED***")
    return text


def safe_print(text: str = "") -> None:
    print(redact(str(text)))


def build_transport(name: str):
    if name == "deepseek":
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise SystemExit("DEEPSEEK_API_KEY not set (source your keys file first)")
        return OpenAICompatibleCompletion(
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            api_key_env="DEEPSEEK_API_KEY",
            json_mode="object",  # DeepSeek native: json_object, not strict json_schema
        )
    if name == "relay":
        base_url = os.environ.get("RELAY_BASE_URL")
        if not base_url or not os.environ.get("RELAY_API_KEY"):
            raise SystemExit("RELAY_BASE_URL / RELAY_API_KEY not set (source your keys file first)")
        model = os.environ.get("RELAY_MODEL", "claude-opus-4-8")
        fmt = os.environ.get("RELAY_FORMAT", "openai")  # "openai" | "anthropic"
        if fmt == "anthropic":
            import anthropic

            headers = {}
            beta = os.environ.get("RELAY_ANTHROPIC_BETA", "context-1m-2025-08-07")
            if beta:
                headers["anthropic-beta"] = beta
            client = anthropic.Anthropic(
                auth_token=os.environ["RELAY_API_KEY"],
                base_url=base_url,
                default_headers=headers or None,
            )
            return AnthropicCompletion(model=model, client=client, base_url=base_url)
        return OpenAICompatibleCompletion(
            model=model,
            base_url=base_url,
            api_key_env="RELAY_API_KEY",
            json_mode=os.environ.get("RELAY_JSON_MODE", "object"),
        )
    raise SystemExit(f"unknown provider: {name}")


def print_thesis(thesis: dict, heading: str = "FIRST REAL THESIS") -> None:
    safe_print("=" * 72)
    safe_print(heading)
    safe_print("=" * 72)
    safe_print(f"id          : {thesis.get('id')}")
    safe_print(f"direction   : {thesis.get('direction')}")
    safe_print(f"confidence  : {thesis.get('confidence')}")
    safe_print(f"status      : {thesis.get('status')}")
    safe_print(f"source ids  : {thesis.get('source_signal_ids')}")
    safe_print(f"uncertainty : {thesis.get('uncertainty_tags')}")
    if thesis.get("origin_market") or thesis.get("target_market"):
        safe_print(f"markets     : {thesis.get('origin_market')} -> {thesis.get('target_market')}")
    safe_print("")
    safe_print("body:")
    safe_print(f"  {thesis.get('body')}")
    safe_print("")
    safe_print("substantive_claims:")
    for claim in thesis.get("substantive_claims") or []:
        safe_print(f"  - {claim.get('text')}  (src={claim.get('source_signal_ids')})")
    for step in thesis.get("transmission_path") or []:
        safe_print(f"  ~ transmission: {step.get('description')}")
    safe_print("")
    adv = thesis.get("adversarial_falsification") or {}
    safe_print("adversarial (reviewer):")
    safe_print(f"  counterargument: {adv.get('strongest_counterargument')}")
    safe_print(f"  hedge_variables: {adv.get('hedge_variables')}")
    track = thesis.get("track_record") or {}
    safe_print("")
    safe_print(f"falsifiable : {track.get('falsifiable_expectation')}")
    safe_print(f"window      : {track.get('verification_window')}")


def print_usage(label: str, transport) -> None:
    for u in getattr(transport, "usage", []) or []:
        safe_print(
            f"  [{label}] model={u.model} role={u.role} "
            f"in={u.input_tokens} out={u.output_tokens} {u.latency_ms}ms stop={u.stop_reason}"
        )


class RecordingTargetProposer:
    def __init__(self, delegate):
        self.delegate = delegate
        self.candidates: list[dict] = []

    def propose(self, thesis: dict) -> list[dict]:
        self.candidates = self.delegate.propose(thesis)
        return self.candidates


def print_candidate(candidate: dict, index: int) -> None:
    symbol = candidate.get("symbol")
    safe_print("")
    safe_print(f"candidate #{index}")
    safe_print(f"  symbol   : {symbol}")
    safe_print(f"  name     : {candidate.get('name')}")
    safe_print(f"  eligible : {candidate.get('eligible')}")
    safe_print(f"  market   : {candidate.get('target_market')}")
    safe_print("  logic_score:")
    safe_print(f"    score     : {(candidate.get('logic_score') or {}).get('score')}")
    safe_print(f"    rationale : {(candidate.get('logic_score') or {}).get('rationale')}")
    safe_print("  buy_point:")
    safe_print(f"    status    : {(candidate.get('buy_point') or {}).get('status')}")
    safe_print(f"    rationale : {(candidate.get('buy_point') or {}).get('rationale')}")
    safe_print(f"  catalysts     : {json.dumps(candidate.get('catalysts') or [], ensure_ascii=False)}")
    safe_print(f"  exit_triggers : {json.dumps(candidate.get('exit_triggers') or [], ensure_ascii=False)}")
    safe_print(f"  price_stub    : {TARGET_PRICE_CHANGES.get(symbol)}")
    safe_print("  priced_in     : not assembled unless candidate passes target thresholds")


def print_targets(target_result, thesis_id: str, proposed_candidates: list[dict]) -> None:
    safe_print("")
    safe_print("=" * 72)
    safe_print("FIRST REAL TARGETS")
    safe_print("=" * 72)
    safe_print("price layer = STUB")
    safe_print(f"proposed_candidates: {len(proposed_candidates)}")
    for index, candidate in enumerate(proposed_candidates, start=1):
        print_candidate(candidate, index)
    safe_print("")
    safe_print(f"target_ids       : {target_result.target_ids}")
    safe_print(f"rejected_reasons : {target_result.rejected_reasons or []}")
    safe_print(f"empty_recommendation: {target_result.empty_recommendation}")
    if not target_result.targets:
        return

    for index, target in enumerate(target_result.targets, start=1):
        verdict_accepted = False
        verdict_error = None
        try:
            verdict_accepted = validate_target(target, confirmed_thesis_ids={thesis_id}).accepted
        except Exception as exc:  # noqa: BLE001
            verdict_error = f"{type(exc).__name__}: {exc}"

        safe_print("")
        safe_print(f"target #{index}")
        safe_print(f"  symbol   : {target.get('symbol')}")
        safe_print(f"  name     : {target.get('name')}")
        safe_print(f"  state    : {target.get('state')}")
        safe_print(f"  market   : {target.get('target_market')}")
        safe_print("  logic_score:")
        safe_print(f"    score     : {(target.get('logic_score') or {}).get('score')}")
        safe_print(f"    rationale : {(target.get('logic_score') or {}).get('rationale')}")
        safe_print("  buy_point:")
        safe_print(f"    status    : {(target.get('buy_point') or {}).get('status')}")
        safe_print(f"    rationale : {(target.get('buy_point') or {}).get('rationale')}")
        safe_print(f"    price_change_since_signal: {(target.get('buy_point') or {}).get('price_change_since_signal')}")
        safe_print(f"  catalysts     : {json.dumps(target.get('catalysts') or [], ensure_ascii=False)}")
        safe_print(f"  exit_triggers : {json.dumps(target.get('exit_triggers') or [], ensure_ascii=False)}")
        safe_print(f"  priced_in     : {json.dumps(target.get('priced_in') or {}, ensure_ascii=False)}")
        safe_print(f"  validate_target.accepted = {verdict_accepted}")
        if verdict_error:
            safe_print(f"  validate_target.error = {verdict_error}")


def print_pipeline_ingestion(result) -> None:
    safe_print("=" * 72)
    safe_print("PIPELINE INGESTION")
    safe_print("=" * 72)
    total_accepted = 0
    for source_id, source_result in result.ingestion.by_source.items():
        total_accepted += source_result.accepted
        safe_print(f"source {source_id}:")
        safe_print(f"  accepted : {source_result.accepted}")
        safe_print(f"  rejected : {source_result.rejected}")
        safe_print(f"  errors   : {source_result.errors}")
    safe_print(f"new_signal_count: {total_accepted}")


def print_store_counts(store) -> None:
    counts = _store_counts(store)
    if not counts:
        return
    safe_print("")
    safe_print("STORE COUNTS")
    safe_print(f"  signals      : {counts['signals']}")
    safe_print(f"  theses       : {counts['theses']}")
    safe_print(f"  targets      : {counts['targets']}")
    safe_print(f"  track_record : {counts['track_record']}")


def print_analysis_state_counts(store) -> None:
    if not hasattr(store, "connection"):
        return
    counts = signal_analysis_counts(store)
    safe_print("ANALYSIS STATE")
    safe_print(f"  pending        : {counts['pending']}")
    safe_print(f"  analyzed       : {counts['analyzed']}")
    safe_print(f"  skipped_stale  : {counts['skipped_stale']}")
    safe_print(f"  skipped_failed : {counts['skipped_failed']}")


def print_analysis_selection(result) -> None:
    safe_print("ANALYSIS SELECTION")
    safe_print(f"  pending_before : {getattr(result, 'pending_count', 0)}")
    safe_print(f"  clusters       : {getattr(result, 'cluster_count', 0)}")
    safe_print(f"  selected       : {getattr(result, 'selected_cluster_count', 0)}")


def _store_counts(store) -> dict[str, int]:
    if not hasattr(store, "connection"):
        return {}
    return {
        "signals": store.connection.execute("select count(*) as count from signals").fetchone()["count"],
        "theses": store.connection.execute("select count(*) as count from theses").fetchone()["count"],
        "targets": store.connection.execute("select count(*) as count from targets").fetchone()["count"],
        "track_record": store.connection.execute("select count(*) as count from track_record").fetchone()["count"],
    }


def _close_store(store) -> None:
    connection = getattr(store, "connection", None)
    if connection is not None:
        connection.close()


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer") from exc


def print_pipeline_targets(result, *, price_layer: str, universe_source: str) -> None:
    safe_print("")
    safe_print("=" * 72)
    safe_print("PIPELINE TARGETS")
    safe_print("=" * 72)
    safe_print(f"price layer = {price_layer}")
    safe_print(f"universe source = {universe_source}")
    if result.empty_recommendations:
        safe_print(f"empty_recommendations: {result.empty_recommendations}")
    if not result.targets:
        safe_print("targets: []")
        return

    confirmed_ids = {thesis.get("id") for thesis in result.theses if thesis.get("id")}
    safe_print(f"target_ids: {[target.get('id') for target in result.targets]}")
    for index, target in enumerate(result.targets, start=1):
        verdict_accepted = False
        verdict_error = None
        try:
            verdict_accepted = validate_target(target, confirmed_thesis_ids=confirmed_ids).accepted
        except Exception as exc:  # noqa: BLE001
            verdict_error = f"{type(exc).__name__}: {exc}"
        safe_print("")
        safe_print(f"target #{index}")
        safe_print(f"  symbol   : {target.get('symbol')}")
        safe_print(f"  name     : {target.get('name')}")
        safe_print(f"  state    : {target.get('state')}")
        safe_print(f"  market   : {target.get('target_market')}")
        safe_print("  logic_score:")
        safe_print(f"    score     : {(target.get('logic_score') or {}).get('score')}")
        safe_print(f"    rationale : {(target.get('logic_score') or {}).get('rationale')}")
        safe_print("  buy_point:")
        safe_print(f"    status    : {(target.get('buy_point') or {}).get('status')}")
        safe_print(f"    rationale : {(target.get('buy_point') or {}).get('rationale')}")
        safe_print(f"    price_change_since_signal: {(target.get('buy_point') or {}).get('price_change_since_signal')}")
        safe_print(f"  catalysts     : {json.dumps(target.get('catalysts') or [], ensure_ascii=False)}")
        safe_print(f"  exit_triggers : {json.dumps(target.get('exit_triggers') or [], ensure_ascii=False)}")
        safe_print(f"  priced_in     : {json.dumps(target.get('priced_in') or {}, ensure_ascii=False)}")
        safe_print(f"  validate_target.accepted = {verdict_accepted}")
        if verdict_error:
            safe_print(f"  validate_target.error = {verdict_error}")


def print_pipeline_errors(errors) -> None:
    safe_print("")
    safe_print("=" * 72)
    safe_print("PIPELINE ERRORS")
    safe_print("=" * 72)
    if not errors:
        safe_print("errors: []")
        return
    for error in errors:
        safe_print(f"- stage={error.stage} unit={error.unit} message={error.message}")


@contextmanager
def open_pipeline_store(store_path: Path | None):
    if store_path is None:
        with tempfile.TemporaryDirectory() as d:
            store = ContractStore(Path(d) / "pipeline.db")
            try:
                yield store, None
            finally:
                _close_store(store)
        return

    resolved = store_path.expanduser()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    store = ContractStore(resolved)
    try:
        yield store, resolved
    finally:
        _close_store(store)


def build_live_rss_adapters():
    feed_url = os.environ.get("RSS_FEED_URL")
    if feed_url:
        source_id = os.environ.get("RSS_SOURCE_ID", "rss:live")
        source_name = os.environ.get("RSS_SOURCE_NAME", "Live RSS")
        return [RssAtomAdapter(source_id, source_name, RssHttpFetcher(feed_url))]
    adapters = build_rss_adapters(load_rss_source_configs())
    if not adapters:
        raise SystemExit("no enabled RSS sources (set RSS_FEED_URL or NEWS_RSS_SOURCES_FILE)")
    return adapters


def _build_live_analysis_components(*, stub_market_data: bool = False):
    author_transport = build_transport("deepseek")
    reviewer_transport = build_transport("deepseek")
    proposer_transport = build_transport("deepseek")
    author = LlmReasoner(ReasonerIdentity("author-live-1", "synthesis-author"), transport=author_transport)
    reviewer = LlmReasoner(ReasonerIdentity("reviewer-live-1", "skeptic-reviewer"), transport=reviewer_transport)

    provider_chain = None
    universe_source = "fixture"
    universe_skipped_reasons: list[str] = []
    if stub_market_data:
        symbol_universe = TARGET_SYMBOL_UNIVERSE
        price_layer = "STUB"
    else:
        provider_chain = build_default_provider_chain()
        universe = build_default_universe(provider_chain)
        if not universe.symbols:
            raise SystemExit(f"real universe build produced no symbols: {universe.skipped_reasons}")
        symbol_universe = universe.symbols
        universe_source = universe.source
        universe_skipped_reasons = universe.skipped_reasons
        price_layer = "REAL"

    proposer = LlmTargetProposer(transport=proposer_transport, symbol_universe=symbol_universe)
    return {
        "author_transport": author_transport,
        "reviewer_transport": reviewer_transport,
        "proposer_transport": proposer_transport,
        "author": author,
        "reviewer": reviewer,
        "provider_chain": provider_chain,
        "universe_source": universe_source,
        "universe_skipped_reasons": universe_skipped_reasons,
        "price_layer": price_layer,
        "symbol_universe": symbol_universe,
        "proposer": proposer,
    }


def run_live_capture(*, store_path: Path | None = None) -> int:
    adapters = build_live_rss_adapters()
    safe_print(f"→ capture sources={len(adapters)}")
    safe_print(f"→ store={'TEMP' if store_path is None else Path(store_path).expanduser()}")
    safe_print("→ calling capture path (RSS fetch → ingestion only)…\n")
    with open_pipeline_store(store_path) as (store, _resolved_store_path):
        ingestion = capture_sources(store, adapters)
        print_pipeline_ingestion(type("CaptureResult", (), {"ingestion": ingestion})())
        print_store_counts(store)
        print_analysis_state_counts(store)
    return 0


def run_live_analyze(
    *,
    stub_market_data: bool = False,
    store_path: Path | None = None,
    top_k: int = 5,
    pending_max_age_days: int = 7,
    max_attempts: int = 2,
    generate_digest_after: bool = True,
) -> int:
    components = _build_live_analysis_components(stub_market_data=stub_market_data)
    safe_print("→ analyze=deepseek  pending=true")
    safe_print(
        f"→ market_data={components['price_layer']}  "
        f"universe_source={components['universe_source']}  symbols={len(components['symbol_universe'])}"
    )
    safe_print(f"→ budget top_k={top_k} pending_max_age_days={pending_max_age_days} max_attempts={max_attempts}")
    safe_print(f"→ store={'TEMP' if store_path is None else Path(store_path).expanduser()}")
    if components["universe_skipped_reasons"]:
        safe_print(f"→ universe_skipped_reasons={components['universe_skipped_reasons']}")
    safe_print("→ calling analyze path (pending → clustering → top-K → analysis → target_generation)…\n")

    with open_pipeline_store(store_path) as (store, _resolved_store_path):
        price_lookup = (
            StubPriceLookup(TARGET_PRICE_CHANGES)
            if stub_market_data
            else RealPriceLookup(store, components["provider_chain"])
        )
        result = analyze_pending(
            store,
            author_reasoner=components["author"],
            reviewer_reasoner=components["reviewer"],
            proposer=components["proposer"],
            price_lookup=price_lookup,
            period="live",
            top_k=top_k,
            pending_max_age_days=pending_max_age_days,
            max_attempts=max_attempts,
        )
        print_store_counts(store)
        print_analysis_selection(result)
        print_analysis_state_counts(store)
        if result.theses:
            safe_print(f"thesis_count: {len(result.theses)}")
            for index, thesis in enumerate(result.theses, start=1):
                safe_print("")
                print_thesis(thesis, heading=f"PIPELINE THESIS #{index}")
                verdict = validate_thesis(thesis)
                safe_print("")
                safe_print(f"validate_thesis.accepted = {verdict.accepted}")
                if not verdict.accepted:
                    safe_print(f"reasons: {getattr(verdict, 'reasons', None)}")
        else:
            safe_print("")
            safe_print("theses: []")
        print_pipeline_targets(
            result,
            price_layer=components["price_layer"],
            universe_source=components["universe_source"],
        )
        print_pipeline_errors(result.errors)
        if generate_digest_after and store_path is not None:
            digest = generate_digest(store_path=store_path)
            safe_print("")
            safe_print(f"digest_markdown={digest.markdown_path}")
            safe_print(f"digest_html={digest.html_path}")
        safe_print("")
        safe_print("=" * 72)
        safe_print("usage:")
        print_usage("author", components["author_transport"])
        print_usage("reviewer", components["reviewer_transport"])
        print_usage("proposer", components["proposer_transport"])
        safe_print("=" * 72)
    return 0


def run_live_pipeline(
    *,
    stub_market_data: bool = False,
    store_path: Path | None = None,
    top_k: int = 5,
    pending_max_age_days: int = 7,
    max_attempts: int = 2,
) -> int:
    adapters = build_live_rss_adapters()
    components = _build_live_analysis_components(stub_market_data=stub_market_data)

    safe_print(f"→ pipeline=deepseek  sources={len(adapters)}")
    safe_print(
        f"→ market_data={components['price_layer']}  "
        f"universe_source={components['universe_source']}  symbols={len(components['symbol_universe'])}"
    )
    safe_print(f"→ budget top_k={top_k} pending_max_age_days={pending_max_age_days} max_attempts={max_attempts}")
    safe_print(f"→ store={'TEMP' if store_path is None else Path(store_path).expanduser()}")
    if components["universe_skipped_reasons"]:
        safe_print(f"→ universe_skipped_reasons={components['universe_skipped_reasons']}")
    safe_print("→ calling real pipeline (capture → pending analysis → target_generation)…\n")

    with open_pipeline_store(store_path) as (store, _resolved_store_path):
        price_lookup = (
            StubPriceLookup(TARGET_PRICE_CHANGES)
            if stub_market_data
            else RealPriceLookup(store, components["provider_chain"])
        )
        result = run_pipeline(
            adapters=adapters,
            author_reasoner=components["author"],
            reviewer_reasoner=components["reviewer"],
            proposer=components["proposer"],
            price_lookup=price_lookup,
            store=store,
            period="live",
            top_k=top_k,
            pending_max_age_days=pending_max_age_days,
            max_attempts=max_attempts,
        )
        print_pipeline_ingestion(result)
        print_store_counts(store)
        print_analysis_selection(result)
        print_analysis_state_counts(store)
        if result.theses:
            safe_print(f"thesis_count: {len(result.theses)}")
            for index, thesis in enumerate(result.theses, start=1):
                safe_print("")
                print_thesis(thesis, heading=f"PIPELINE THESIS #{index}")
                verdict = validate_thesis(thesis)
                safe_print("")
                safe_print(f"validate_thesis.accepted = {verdict.accepted}")
                if not verdict.accepted:
                    safe_print(f"reasons: {getattr(verdict, 'reasons', None)}")
        else:
            safe_print("")
            safe_print("theses: []")
        print_pipeline_targets(
            result,
            price_layer=components["price_layer"],
            universe_source=components["universe_source"],
        )
        print_pipeline_errors(result.errors)
        safe_print("")
        safe_print("=" * 72)
        safe_print("usage:")
        print_usage("author", components["author_transport"])
        print_usage("reviewer", components["reviewer_transport"])
        print_usage("proposer", components["proposer_transport"])
        safe_print("=" * 72)
    return 0


def show_store(store_path: Path) -> int:
    path = store_path.expanduser()
    if not path.exists():
        raise SystemExit(f"store not found: {path}")

    store = ContractStore(path)
    try:
        safe_print("=" * 72)
        safe_print("STORE SUMMARY")
        safe_print("=" * 72)
        counts = _store_counts(store)
        safe_print(f"signal_count: {counts['signals']}")
        safe_print(f"thesis_count: {counts['theses']}")
        safe_print(f"target_count: {counts['targets']}")
        safe_print(f"track_record_count: {counts['track_record']}")
        print_analysis_state_counts(store)

        safe_print("")
        safe_print("THESES")
        thesis_rows = store.connection.execute(
            "select payload_json from theses order by id asc"
        ).fetchall()
        for row in thesis_rows:
            thesis = json.loads(row["payload_json"])
            track = thesis.get("track_record") or {}
            body = (thesis.get("body") or "").replace("\n", " ")
            preview = body[:80]
            safe_print(
                f"- id={thesis.get('id')} direction={thesis.get('direction')} "
                f"confidence={thesis.get('confidence')} status={thesis.get('status')} "
                f"body={preview!r} verification_window={track.get('verification_window')}"
            )

        safe_print("")
        safe_print("TARGETS")
        target_rows = store.connection.execute(
            "select payload_json from targets order by symbol asc, id asc"
        ).fetchall()
        for row in target_rows:
            target = json.loads(row["payload_json"])
            logic = target.get("logic_score") or {}
            buy_point = target.get("buy_point") or {}
            priced_in = target.get("priced_in") or {}
            safe_print(
                f"- symbol={target.get('symbol')} name={target.get('name')} "
                f"logic_score={logic.get('score')} buy_point={buy_point.get('status')} "
                f"priced_in={priced_in.get('risk')} "
                f"price_change_since_signal={priced_in.get('price_change_since_signal')}"
            )
    finally:
        store.connection.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", default="deepseek", choices=["deepseek", "relay"])
    parser.add_argument("--reviewer", default=None, choices=["deepseek", "relay"])
    parser.add_argument("--targets", action="store_true", help="After analysis, run target generation live smoke.")
    parser.add_argument("--pipeline", action="store_true", help="Run live RSS ingestion through analysis and target generation.")
    parser.add_argument("--capture", action="store_true", help="Run capture only: fetch configured RSS sources and persist accepted signals.")
    parser.add_argument("--analyze", action="store_true", help="Run pending analysis only: cluster pending signals and process top-K.")
    parser.add_argument("--stub-market-data", action="store_true", help="Use fixture universe and stub prices in pipeline mode.")
    parser.add_argument("--store", type=Path, default=None, help="Persistent pipeline store path, e.g. .local/news-data/store.db.")
    parser.add_argument("--show-store", type=Path, default=None, help="Print accumulated thesis/target summaries from a persistent store.")
    parser.add_argument("--top-k", type=int, default=_env_int("NEWS_ANALYZE_TOP_K", 5), help="Maximum pending clusters to analyze.")
    parser.add_argument(
        "--pending-max-age-days",
        type=int,
        default=_env_int("NEWS_PENDING_MAX_AGE_DAYS", 7),
        help="Mark pending signals older than this many days skipped_stale before analysis.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=_env_int("NEWS_MAX_ANALYSIS_ATTEMPTS", 2),
        help="Mark a repeatedly failing selected cluster skipped_failed after this many attempts.",
    )
    args = parser.parse_args()
    if args.show_store is not None:
        return show_store(args.show_store)
    selected_modes = sum(bool(value) for value in (args.pipeline, args.capture, args.analyze))
    if selected_modes > 1:
        raise SystemExit("choose only one of --pipeline, --capture, or --analyze")
    if args.capture:
        return run_live_capture(store_path=args.store)
    if args.analyze:
        if args.author != "deepseek" or args.reviewer is not None:
            raise SystemExit("--analyze is scoped to DeepSeek; omit --author/--reviewer")
        return run_live_analyze(
            stub_market_data=args.stub_market_data,
            store_path=args.store,
            top_k=args.top_k,
            pending_max_age_days=args.pending_max_age_days,
            max_attempts=args.max_attempts,
        )
    if args.pipeline:
        if args.author != "deepseek" or args.reviewer is not None:
            raise SystemExit("--pipeline is scoped to DeepSeek; omit --author/--reviewer")
        return run_live_pipeline(
            stub_market_data=args.stub_market_data,
            store_path=args.store,
            top_k=args.top_k,
            pending_max_age_days=args.pending_max_age_days,
            max_attempts=args.max_attempts,
        )
    reviewer_provider = args.reviewer or args.author
    if args.targets and args.author != "deepseek":
        raise SystemExit("--targets live smoke is scoped to --author deepseek")

    author_transport = build_transport(args.author)
    reviewer_transport = build_transport(reviewer_provider)
    author = LlmReasoner(ReasonerIdentity("author-live-1", "synthesis-author"), transport=author_transport)
    reviewer = LlmReasoner(ReasonerIdentity("reviewer-live-1", "skeptic-reviewer"), transport=reviewer_transport)

    safe_print(f"→ author={args.author}  reviewer={reviewer_provider}  signal={SIGNAL['id']}")
    safe_print("→ calling real provider (free_generation → completeness_critique → adversarial_falsification)…\n")

    with tempfile.TemporaryDirectory() as d:
        store = ContractStore(Path(d) / "live.db")
        store.add_signal(SIGNAL)
        result = analyze([SIGNAL], author, reviewer, store, thesis_id="thesis-live-1")
        print_thesis(result.thesis)
        verdict = validate_thesis(result.thesis)
        safe_print("")
        safe_print("=" * 72)
        safe_print(f"validate_thesis.accepted = {verdict.accepted}")
        if not verdict.accepted:
            safe_print(f"reasons: {getattr(verdict, 'reasons', None)}")
        if args.targets:
            safe_print("")
            safe_print("→ calling real provider (target_proposal)…")
            proposer = RecordingTargetProposer(LlmTargetProposer(
                transport=author_transport,
                symbol_universe=TARGET_SYMBOL_UNIVERSE,
            ))
            target_result = propose_targets(
                result.thesis,
                proposer,
                StubPriceLookup(TARGET_PRICE_CHANGES),
                store,
            )
            print_targets(target_result, result.thesis["id"], proposer.candidates)
        safe_print("usage:")
        print_usage("author", author_transport)
        if reviewer_transport is not author_transport:
            print_usage("reviewer", reviewer_transport)
        safe_print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except LlmProviderError as exc:
        safe_print("")
        safe_print("LLM PROVIDER ERROR (this is the schema/transport truth signal):")
        safe_print(f"  {type(exc).__name__}: {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        safe_print("")
        safe_print("UNEXPECTED ERROR:")
        safe_print(redact("".join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
        sys.exit(1)
