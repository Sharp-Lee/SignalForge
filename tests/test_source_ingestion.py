import json

import pytest

from news_contracts.storage import ContractStore
from news_contracts.validation import ContractError
from source_ingestion.adapters.gdelt import GdeltFixtureAdapter
from source_ingestion.adapters.last30days import Last30DaysAdapter
from source_ingestion.adapters.market_move import MarketMoveAdapter
from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.core import FetchResult, FixtureFetcher
from source_ingestion.runner import run_once


def test_rss_adapter_normalizes_fixture_without_network():
    fetcher = FixtureFetcher(
        [
            {
                "id": "rss-1",
                "title": "Copper supply disruption lifts prices 12%",
                "link": "https://example.com/rss/copper",
                "published_at": "2026-06-09T08:00:00Z",
                "summary": "Chile mine disruption cuts output by 12% this quarter.",
            }
        ],
        next_cursor="rss-cursor-1",
    )
    adapter = RssAtomAdapter(source_id="rss:test", source_name="RSS Test", fetcher=fetcher)

    fetched = adapter.fetch(cursor=None)
    signals = adapter.normalize(fetched.items[0])

    assert fetcher.calls == [None]
    assert fetched.next_cursor == "rss-cursor-1"
    assert signals[0]["signal_origin"] == "news"
    assert signals[0]["source"]["id"] == "rss:test"


def test_gdelt_adapter_normalizes_fixture_to_news_signal():
    adapter = GdeltFixtureAdapter(
        source_id="gdelt:test",
        source_name="GDELT Test",
        fetcher=FixtureFetcher(
            [
                {
                    "url": "https://example.com/gdelt/ai-power",
                    "title": "AI data center power demand rises 30%",
                    "seendate": "2026-06-09T09:00:00Z",
                    "summary": "Grid operators report AI data center power demand up 30% year over year.",
                }
            ],
            next_cursor="gdelt-cursor-1",
        ),
    )

    signals = adapter.normalize(adapter.fetch(None).items[0])

    assert signals[0]["signal_origin"] == "news"
    assert signals[0]["source"]["id"] == "gdelt:test"
    assert "30%" in signals[0]["body"]


def test_last30days_adapter_uses_attention_origin_in_unified_framework():
    output = json.dumps(
        [
            {
                "title": "AI server lead times expand",
                "body": "Lead times expanded from 4 weeks to 12 weeks.",
                "url": "https://example.com/last30/ai",
                "published_at": "2026-06-09T08:00:00Z",
            }
        ]
    )
    adapter = Last30DaysAdapter(fetcher=FixtureFetcher([output], next_cursor="last30-cursor-1"))

    signals = adapter.normalize(adapter.fetch(None).items[0])

    assert signals[0]["signal_origin"] == "last30days_attention"
    assert signals[0]["source"]["id"] == "last30days"


def test_market_move_adapter_normalizes_hard_gated_signal():
    adapter = MarketMoveAdapter(
        fetcher=FixtureFetcher(
            [
                {
                    "id": "move-1",
                    "title": "Pipe sector volume spike after floods",
                    "body": "Pipe sector turnover rose 120% versus 20-day average after backtraced flood news.",
                    "published_at": "2026-06-09T16:00:00Z",
                    "url": "https://example.com/market/move-1",
                    "trigger_reason": {
                        "source_strength": True,
                        "quantified_impact": True,
                        "cross_market_transmission": True,
                        "significant_market_move": True,
                        "summary": "120% turnover spike with backtraced flood news",
                    },
                }
            ],
            next_cursor="move-cursor-1",
        )
    )

    signals = adapter.normalize(adapter.fetch(None).items[0])

    assert signals[0]["signal_origin"] == "market_move"
    assert signals[0]["trigger_reason"]["significant_market_move"] is True


def test_runner_persists_valid_signal_and_updates_cursor(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    adapter = RssAtomAdapter(
        source_id="rss:test",
        source_name="RSS Test",
        fetcher=FixtureFetcher(
            [
                {
                    "id": "rss-1",
                    "title": "Copper supply disruption lifts prices 12%",
                    "link": "https://example.com/rss/copper",
                    "published_at": "2026-06-09T08:00:00Z",
                    "summary": "Chile mine disruption cuts output by 12% this quarter.",
                }
            ],
            next_cursor="rss-cursor-1",
        ),
    )

    result = run_once(store, [adapter])

    assert result.by_source["rss:test"].accepted == 1
    assert result.by_source["rss:test"].rejected == 0
    assert store.get_source_cursor("rss:test") == "rss-cursor-1"
    assert store.connection.execute("select count(*) as count from signals").fetchone()["count"] == 1


def test_runner_repeated_fixture_run_is_idempotent(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    fixture = [
        {
            "id": "rss-1",
            "title": "Copper supply disruption lifts prices 12%",
            "link": "https://example.com/rss/copper",
            "published_at": "2026-06-09T08:00:00Z",
            "summary": "Chile mine disruption cuts output by 12% this quarter.",
        }
    ]
    adapter = RssAtomAdapter("rss:test", "RSS Test", FixtureFetcher(fixture, next_cursor="rss-cursor-1"))

    first = run_once(store, [adapter])
    second = run_once(store, [adapter])

    assert first.by_source["rss:test"].accepted == 1
    assert second.by_source["rss:test"].accepted == 0
    assert second.by_source["rss:test"].rejected == 1
    assert store.connection.execute("select count(*) as count from signals").fetchone()["count"] == 1


def test_runner_reports_weak_market_move_rejection_without_abort(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")
    adapter = MarketMoveAdapter(
        fetcher=FixtureFetcher(
            [
                {
                    "id": "move-weak",
                    "title": "Vague market move",
                    "body": "Sector moved vaguely.",
                    "published_at": "2026-06-09T16:00:00Z",
                    "url": "https://example.com/market/weak",
                    "trigger_reason": {"summary": "no hard gate"},
                }
            ],
            next_cursor="move-cursor-1",
        )
    )

    result = run_once(store, [adapter])

    assert result.by_source["market_move"].accepted == 0
    assert result.by_source["market_move"].rejected == 1
    assert "trigger_reason" in result.by_source["market_move"].errors[0]


def test_adapter_can_return_no_signal_for_unusable_raw_item():
    adapter = RssAtomAdapter("rss:test", "RSS Test", FixtureFetcher([], next_cursor=None))

    assert adapter.normalize({"title": "missing link and timestamp"}) == []
