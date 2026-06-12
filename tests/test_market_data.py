import os
import urllib.request
from datetime import date

import pytest

from news_contracts.storage import ContractStore


def signal(signal_id: str = "sig-1", published_at: str = "2026-06-06T08:00:00Z") -> dict:
    if "early" in signal_id:
        title = "Optical transceiver demand accelerates for AI clusters"
        body = "Optical transceiver demand accelerates as hyperscale AI clusters add more 800G ports and supplier lead times extend."
    elif "late" in signal_id:
        title = "PCB substrate capacity tightens for accelerator platforms"
        body = "PCB substrate capacity tightens for new accelerator platforms after cloud vendors raise board complexity requirements."
    else:
        title = f"AI server supply chain pressure expands {signal_id}"
        body = f"AI server supply chain pressure expands as optical module lead times lengthen for {signal_id} with distinct fixture context."
    return {
        "id": signal_id,
        "source": {
            "id": "rss:test",
            "name": "Test RSS",
            "published_at": published_at,
            "url": f"https://example.com/{signal_id}",
        },
        "title": title,
        "body": body,
        "signal_origin": "news",
        "type_tag": "supply_demand_bottleneck",
        "triage": {"excluded": False, "reasons": [], "strategy": "zh_cn_heuristic_v0"},
        "raw_payload": {"fixture": signal_id},
    }


def thesis(source_ids: list[str] | None = None) -> dict:
    return {
        "id": "thesis-1",
        "source_signal_ids": source_ids if source_ids is not None else ["sig-1"],
        "track_record": {
            "verification_window": {"start": "2026-01-01", "end": "2026-12-31"}
        },
    }


class FakeProvider:
    def __init__(self, *, name="fake", bars=None, names=None, fail_prices=None, fail_names=False):
        self.name = name
        self.bars = bars or {}
        self.names = names or {}
        self.fail_prices = set(fail_prices or [])
        self.fail_names = fail_names
        self.price_calls = []
        self.name_calls = []

    def daily_bars(self, symbol, start_date, end_date):
        self.price_calls.append((symbol, start_date, end_date))
        if symbol in self.fail_prices:
            from market_data import MarketDataError

            raise MarketDataError(f"{self.name} price failed for {symbol}")
        if symbol not in self.bars:
            from market_data import MarketDataError

            raise MarketDataError(f"{self.name} missing bars for {symbol}")
        return self.bars[symbol]

    def security_names(self, symbols):
        self.name_calls.append(list(symbols))
        if self.fail_names:
            from market_data import MarketDataError

            raise MarketDataError(f"{self.name} names failed")
        return {symbol: self.names[symbol] for symbol in symbols if symbol in self.names}


def test_scoped_no_proxy_restores_environment(monkeypatch):
    from market_data import scoped_no_proxy

    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example")
    monkeypatch.setenv("NO_PROXY", "localhost")
    original_getproxies = urllib.request.getproxies

    with scoped_no_proxy():
        assert "HTTP_PROXY" not in os.environ
        assert os.environ["NO_PROXY"] == "*"
        assert urllib.request.getproxies() == {}

    assert os.environ["HTTP_PROXY"] == "http://proxy.example"
    assert os.environ["NO_PROXY"] == "localhost"
    assert urllib.request.getproxies is original_getproxies


def test_provider_chain_uses_tushare_primary_without_calling_akshare():
    from market_data import MarketDataProviderChain

    tushare = FakeProvider(
        name="tushare",
        bars={"300308.SZ": [{"date": date(2026, 6, 5), "close": 100.0}]},
    )
    akshare = FakeProvider(
        name="akshare",
        bars={"300308.SZ": [{"date": date(2026, 6, 5), "close": 200.0}]},
    )

    chain = MarketDataProviderChain([tushare, akshare])

    bars = chain.daily_bars("300308.SZ", date(2026, 6, 5), date(2026, 6, 10))
    assert [(bar.date, bar.close) for bar in bars] == [(date(2026, 6, 5), 100.0)]
    assert akshare.price_calls == []


def test_provider_chain_falls_back_per_symbol_when_tushare_price_fails():
    from market_data import MarketDataProviderChain

    tushare = FakeProvider(name="tushare", fail_prices={"300502.SZ"})
    akshare = FakeProvider(
        name="akshare",
        bars={"300502.SZ": [{"date": date(2026, 6, 5), "close": 88.0}]},
    )

    chain = MarketDataProviderChain([tushare, akshare])

    bars = chain.daily_bars("300502.SZ", date(2026, 6, 5), date(2026, 6, 10))
    assert [(bar.date, bar.close) for bar in bars] == [(date(2026, 6, 5), 88.0)]
    assert tushare.price_calls == [("300502.SZ", date(2026, 6, 5), date(2026, 6, 10))]
    assert akshare.price_calls == [("300502.SZ", date(2026, 6, 5), date(2026, 6, 10))]


def test_real_price_lookup_uses_earliest_persisted_source_signal_date(tmp_path):
    from market_data import MarketDataProviderChain, RealPriceLookup

    store = ContractStore(tmp_path / "contracts.db")
    store.add_signal(signal("sig-late", "2026-06-09T08:00:00Z"))
    store.add_signal(signal("sig-early", "2026-06-06T08:00:00Z"))
    provider = FakeProvider(
        bars={
            "300308.SZ": [
                {"date": date(2026, 6, 8), "close": 100.0},
                {"date": date(2026, 6, 10), "close": 125.0},
            ]
        }
    )

    lookup = RealPriceLookup(store, MarketDataProviderChain([provider]), today=date(2026, 6, 10))

    assert lookup.price_change_since_signal("300308.SZ", thesis(["sig-late", "sig-early"])) == 0.25
    assert provider.price_calls == [("300308.SZ", date(2026, 6, 6), date(2026, 6, 10))]


def test_real_price_lookup_fails_closed_when_source_signal_missing(tmp_path):
    from market_data import MarketDataError, MarketDataProviderChain, RealPriceLookup

    store = ContractStore(tmp_path / "contracts.db")
    provider = FakeProvider(bars={"300308.SZ": [{"date": date(2026, 6, 8), "close": 100.0}]})
    lookup = RealPriceLookup(store, MarketDataProviderChain([provider]), today=date(2026, 6, 10))

    with pytest.raises(MarketDataError, match="source signal not found"):
        lookup.price_change_since_signal("300308.SZ", thesis(["missing-sig"]))


def test_build_universe_prefers_tushare_names_and_tolerates_akshare_name_failure():
    from market_data import MarketDataProviderChain, build_universe

    tushare = FakeProvider(
        name="tushare",
        names={
            "300308.SZ": "中际旭创",
            "300502.SZ": "新易盛",
        },
    )
    akshare = FakeProvider(name="akshare", fail_names=True)

    universe = build_universe(["300308.SZ", "300502.SZ"], MarketDataProviderChain([tushare, akshare]))

    assert universe.symbols == {"300308.SZ": "中际旭创", "300502.SZ": "新易盛"}
    assert universe.source == "tushare"
    assert akshare.name_calls == []


def test_build_universe_records_akshare_failure_for_tushare_gaps():
    from market_data import MarketDataProviderChain, build_universe

    tushare = FakeProvider(name="tushare", names={"300308.SZ": "中际旭创"})
    akshare = FakeProvider(name="akshare", fail_names=True)

    universe = build_universe(["300308.SZ", "300502.SZ"], MarketDataProviderChain([tushare, akshare]))

    assert universe.symbols == {"300308.SZ": "中际旭创"}
    assert universe.source == "tushare"
    assert any("akshare names failed" in reason for reason in universe.skipped_reasons)
    assert "300502.SZ: missing authoritative name" in universe.skipped_reasons


def test_build_universe_skips_missing_codes_with_reason():
    from market_data import MarketDataProviderChain, build_universe

    provider = FakeProvider(name="tushare", names={"300308.SZ": "中际旭创"})

    universe = build_universe(["300308.SZ", "002463.SZ"], MarketDataProviderChain([provider]))

    assert universe.symbols == {"300308.SZ": "中际旭创"}
    assert "002463.SZ: missing authoritative name" in universe.skipped_reasons


def test_build_default_universe_uses_provider_names_not_chokepoint_placeholders():
    from market_data import MarketDataProviderChain, build_default_universe

    provider = FakeProvider(name="tushare", names={"300308.SZ": "中际旭创"})

    universe = build_default_universe(MarketDataProviderChain([provider]))

    assert universe.symbols["300308.SZ"] == "中际旭创"
    assert "" not in universe.symbols.values()
    assert "300502.SZ: missing authoritative name" in universe.skipped_reasons


def test_tushare_provider_uses_injected_client_for_names_and_daily_bars():
    from market_data.providers import TushareProvider

    class FakeTushareClient:
        def __init__(self):
            self.daily_calls = []

        def daily(self, **kwargs):
            self.daily_calls.append(kwargs)
            return [
                {"trade_date": "20260605", "close": 1179.99},
                {"trade_date": "20260610", "close": 1147.0},
            ]

        def stock_basic(self, **kwargs):
            return [
                {"ts_code": "300308.SZ", "name": "中际旭创"},
                {"ts_code": "300502.SZ", "name": "新易盛"},
            ]

    client = FakeTushareClient()
    provider = TushareProvider(client=client)

    bars = provider.daily_bars("300308.SZ", date(2026, 6, 5), date(2026, 6, 10))
    names = provider.security_names(["300308.SZ"])

    assert [(bar.date, bar.close) for bar in bars] == [
        (date(2026, 6, 5), 1179.99),
        (date(2026, 6, 10), 1147.0),
    ]
    assert client.daily_calls == [
        {"ts_code": "300308.SZ", "start_date": "20260605", "end_date": "20260610"}
    ]
    assert names == {"300308.SZ": "中际旭创"}


def test_akshare_provider_uses_injected_module_for_names_and_daily_bars():
    from market_data.providers import AkshareProvider

    class FakeAkshare:
        def __init__(self):
            self.daily_symbols = []

        def stock_zh_a_daily(self, symbol):
            self.daily_symbols.append(symbol)
            return [
                {"date": "2026-06-05", "close": 748.0},
                {"date": "2026-06-10", "close": 772.5},
            ]

        def stock_info_a_code_name(self):
            return [
                {"code": "300502", "name": "新易盛"},
                {"code": "002463", "name": "沪电股份"},
            ]

    fake_ak = FakeAkshare()
    provider = AkshareProvider(ak_module=fake_ak)

    bars = provider.daily_bars("300502.SZ", date(2026, 6, 5), date(2026, 6, 10))
    names = provider.security_names(["300502.SZ"])

    assert [(bar.date, bar.close) for bar in bars] == [
        (date(2026, 6, 5), 748.0),
        (date(2026, 6, 10), 772.5),
    ]
    assert fake_ak.daily_symbols == ["sz300502"]
    assert names == {"300502.SZ": "新易盛"}
