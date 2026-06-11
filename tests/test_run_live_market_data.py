from pathlib import Path

import scripts.run_live as run_live


def test_pipeline_market_data_defaults_to_real(monkeypatch, tmp_path):
    calls = {}

    class FakeStore:
        def __init__(self, path):
            calls["store_path"] = path

    class FakeRealPriceLookup:
        def __init__(self, store, provider_chain):
            calls["lookup_store"] = store
            calls["lookup_chain"] = provider_chain

    class FakeProposer:
        def __init__(self, *, transport, symbol_universe):
            calls["symbol_universe"] = symbol_universe

    class FakeReasoner:
        def __init__(self, identity, transport):
            pass

    class FakeAdapter:
        def __init__(self, source_id, source_name, fetcher):
            pass

    class FakeFetcher:
        def __init__(self, url):
            pass

    def fake_run_pipeline(**kwargs):
        calls["price_lookup"] = kwargs["price_lookup"]
        calls["store"] = kwargs["store"]

        class Ingestion:
            by_source = {}

        class Result:
            ingestion = Ingestion()
            theses = []
            targets = []
            empty_recommendations = []
            errors = []

        return Result()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/feed.xml")
    monkeypatch.setattr(run_live, "build_transport", lambda name: object())
    monkeypatch.setattr(run_live, "ContractStore", FakeStore)
    monkeypatch.setattr(run_live, "RealPriceLookup", FakeRealPriceLookup)
    monkeypatch.setattr(run_live, "build_default_provider_chain", lambda: "provider-chain")
    monkeypatch.setattr(run_live, "build_default_universe", lambda chain: type("Universe", (), {"symbols": {"300308.SZ": "中际旭创"}, "source": "tushare", "skipped_reasons": []})())
    monkeypatch.setattr(run_live, "LlmTargetProposer", FakeProposer)
    monkeypatch.setattr(run_live, "LlmReasoner", FakeReasoner)
    monkeypatch.setattr(run_live, "RssAtomAdapter", FakeAdapter)
    monkeypatch.setattr(run_live, "RssHttpFetcher", FakeFetcher)
    monkeypatch.setattr(run_live, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(run_live.tempfile, "TemporaryDirectory", lambda: _TempDir(tmp_path))

    assert run_live.run_live_pipeline(stub_market_data=False) == 0

    assert isinstance(calls["price_lookup"], FakeRealPriceLookup)
    assert calls["symbol_universe"] == {"300308.SZ": "中际旭创"}
    assert calls["lookup_chain"] == "provider-chain"


def test_pipeline_market_data_stub_mode_uses_fixture(monkeypatch, tmp_path):
    calls = {}

    class FakeStore:
        def __init__(self, path):
            calls["store_path"] = path

    class FakeProposer:
        def __init__(self, *, transport, symbol_universe):
            calls["symbol_universe"] = symbol_universe

    class FakeReasoner:
        def __init__(self, identity, transport):
            pass

    class FakeAdapter:
        def __init__(self, source_id, source_name, fetcher):
            pass

    class FakeFetcher:
        def __init__(self, url):
            pass

    def fake_run_pipeline(**kwargs):
        calls["price_lookup"] = kwargs["price_lookup"]

        class Ingestion:
            by_source = {}

        class Result:
            ingestion = Ingestion()
            theses = []
            targets = []
            empty_recommendations = []
            errors = []

        return Result()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/feed.xml")
    monkeypatch.setattr(run_live, "build_transport", lambda name: object())
    monkeypatch.setattr(run_live, "ContractStore", FakeStore)
    monkeypatch.setattr(run_live, "LlmTargetProposer", FakeProposer)
    monkeypatch.setattr(run_live, "LlmReasoner", FakeReasoner)
    monkeypatch.setattr(run_live, "RssAtomAdapter", FakeAdapter)
    monkeypatch.setattr(run_live, "RssHttpFetcher", FakeFetcher)
    monkeypatch.setattr(run_live, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(run_live.tempfile, "TemporaryDirectory", lambda: _TempDir(tmp_path))

    assert run_live.run_live_pipeline(stub_market_data=True) == 0

    assert calls["symbol_universe"] == run_live.TARGET_SYMBOL_UNIVERSE
    assert calls["price_lookup"].price_changes == run_live.TARGET_PRICE_CHANGES


def test_pipeline_store_path_creates_parent_and_uses_persistent_db(monkeypatch, tmp_path):
    calls = {}
    store_path = tmp_path / "nested" / "store.db"

    class FakeStore:
        def __init__(self, path):
            calls["store_path"] = Path(path)

    class FakeProposer:
        def __init__(self, *, transport, symbol_universe):
            pass

    class FakeReasoner:
        def __init__(self, identity, transport):
            pass

    class FakeAdapter:
        def __init__(self, source_id, source_name, fetcher):
            pass

    class FakeFetcher:
        def __init__(self, url):
            pass

    def fake_run_pipeline(**kwargs):
        calls["store"] = kwargs["store"]

        class Ingestion:
            by_source = {}

        class Result:
            ingestion = Ingestion()
            theses = []
            targets = []
            empty_recommendations = []
            errors = []

        return Result()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("RSS_FEED_URL", "https://example.com/feed.xml")
    monkeypatch.setattr(run_live, "build_transport", lambda name: object())
    monkeypatch.setattr(run_live, "ContractStore", FakeStore)
    monkeypatch.setattr(run_live, "LlmTargetProposer", FakeProposer)
    monkeypatch.setattr(run_live, "LlmReasoner", FakeReasoner)
    monkeypatch.setattr(run_live, "RssAtomAdapter", FakeAdapter)
    monkeypatch.setattr(run_live, "RssHttpFetcher", FakeFetcher)
    monkeypatch.setattr(run_live, "run_pipeline", fake_run_pipeline)

    assert run_live.run_live_pipeline(stub_market_data=True, store_path=store_path) == 0

    assert store_path.parent.exists()
    assert calls["store_path"] == store_path


def test_show_store_prints_accumulated_thesis_and_target_fields(tmp_path, capsys):
    from tests.test_target_generation import confirmed_thesis, qualified_candidate

    store_path = tmp_path / "store.db"
    store = run_live.ContractStore(store_path)
    thesis = confirmed_thesis()
    store.add_thesis(thesis)
    target = {
        "id": "target-1",
        "symbol": "300001.SZ",
        "name": "Power Module Supplier",
        "target_market": "CN-A",
        "thesis_ids": [thesis["id"]],
        "logic_score": qualified_candidate()["logic_score"],
        "buy_point": {**qualified_candidate()["buy_point"], "price_change_since_signal": 0.08},
        "state": "watch",
        "catalysts": qualified_candidate()["catalysts"],
        "exit_triggers": qualified_candidate()["exit_triggers"],
        "priced_in": {"price_change_since_signal": 0.08, "risk": "low"},
    }
    store.add_target(target)

    assert run_live.show_store(store_path) == 0
    output = capsys.readouterr().out

    assert "thesis_count: 1" in output
    assert "target_count: 1" in output
    assert "thesis-ai-server-1" in output
    assert "direction=bullish" in output
    assert "verification_window=" in output
    assert "2026-06-09" in output
    assert "2026-09-07" in output
    assert "300001.SZ" in output
    assert "logic_score=82" in output
    assert "price_change_since_signal=0.08" in output


class _TempDir:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        return str(self.path)

    def __exit__(self, exc_type, exc, tb):
        return False
