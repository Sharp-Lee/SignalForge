from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import importlib.util
import json
import os
from typing import Any, Protocol
import urllib.request

from .universe import DEFAULT_A_SHARE_ALLOWLIST


class MarketDataError(RuntimeError):
    """Raised when real market data cannot be obtained safely."""


@dataclass(frozen=True)
class DailyBar:
    date: date
    close: float


class MarketDataProvider(Protocol):
    name: str

    def daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar | dict]:
        ...

    def security_names(self, symbols: list[str]) -> dict[str, str]:
        ...


_PROXY_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)


@contextmanager
def scoped_no_proxy():
    """Temporarily bypass proxies for market-data providers, then restore exactly."""

    old_env = {key: os.environ.get(key) for key in _PROXY_KEYS}
    old_getproxies = urllib.request.getproxies
    try:
        for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
            os.environ.pop(key, None)
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
        urllib.request.getproxies = lambda: {}
        yield
    finally:
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        urllib.request.getproxies = old_getproxies


class MarketDataProviderChain:
    def __init__(self, providers: list[MarketDataProvider]):
        self.providers = list(providers)
        self.last_errors: list[str] = []

    def daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar]:
        self.last_errors = []
        for provider in self.providers:
            try:
                bars = [_coerce_bar(bar) for bar in provider.daily_bars(symbol, start_date, end_date)]
            except Exception as exc:  # noqa: BLE001
                self.last_errors.append(f"{provider.name}: {exc}")
                continue
            if bars:
                return sorted(bars, key=lambda bar: bar.date)
            self.last_errors.append(f"{provider.name}: no bars for {symbol}")
        detail = "; ".join(self.last_errors) or "no market data providers configured"
        raise MarketDataError(f"market data unavailable for {symbol}: {detail}")

    def security_names(self, symbols: list[str]) -> tuple[dict[str, str], str, list[str]]:
        missing = list(dict.fromkeys(symbols))
        names: dict[str, str] = {}
        used_sources: list[str] = []
        skipped_reasons: list[str] = []

        for provider in self.providers:
            if not missing:
                break
            try:
                provider_names = provider.security_names(missing)
            except Exception as exc:  # noqa: BLE001
                skipped_reasons.append(f"{provider.name}: {exc}")
                continue
            if provider_names:
                used_sources.append(provider.name)
            for symbol in list(missing):
                name = provider_names.get(symbol)
                if isinstance(name, str) and name.strip():
                    names[symbol] = name.strip()
                    missing.remove(symbol)

        for symbol in missing:
            skipped_reasons.append(f"{symbol}: missing authoritative name")

        return names, "+".join(used_sources) if used_sources else "none", skipped_reasons


class RealPriceLookup:
    def __init__(self, store, provider_chain: MarketDataProviderChain, today: date | None = None):
        self.store = store
        self.provider_chain = provider_chain
        self.today = today or date.today()

    def price_change_since_signal(self, symbol: str, thesis: dict) -> float:
        signal_date = self._source_signal_date(thesis)
        bars = self.provider_chain.daily_bars(symbol, signal_date, self.today)
        signal_bar = _first_bar_on_or_after(bars, signal_date, symbol)
        current_bar = _latest_bar_on_or_before(bars, self.today, symbol)
        if signal_bar.close <= 0:
            raise MarketDataError(f"{symbol}: invalid signal close {signal_bar.close}")
        return (current_bar.close - signal_bar.close) / signal_bar.close

    def _source_signal_date(self, thesis: dict) -> date:
        source_ids = thesis.get("source_signal_ids") or []
        if not source_ids:
            raise MarketDataError("thesis has no source_signal_ids")

        dates: list[date] = []
        for source_id in source_ids:
            row = self.store.connection.execute(
                "select payload_json from signals where id = ?",
                (source_id,),
            ).fetchone()
            if row is None:
                raise MarketDataError(f"source signal not found: {source_id}")
            payload = json.loads(row["payload_json"])
            published_at = (payload.get("source") or {}).get("published_at")
            if not published_at:
                raise MarketDataError(f"source signal missing published_at: {source_id}")
            dates.append(_parse_date(published_at, f"source signal {source_id} published_at"))
        return min(dates)


@dataclass(frozen=True)
class UniverseBuildResult:
    symbols: dict[str, str]
    source: str
    skipped_reasons: list[str]


def build_universe(symbols: list[str], provider_chain: MarketDataProviderChain) -> UniverseBuildResult:
    names, source, skipped_reasons = provider_chain.security_names(symbols)
    ordered_names = {symbol: names[symbol] for symbol in symbols if symbol in names}
    return UniverseBuildResult(symbols=ordered_names, source=source, skipped_reasons=skipped_reasons)


def build_default_universe(provider_chain: MarketDataProviderChain) -> UniverseBuildResult:
    return build_universe(DEFAULT_A_SHARE_ALLOWLIST, provider_chain)


def build_default_provider_chain() -> MarketDataProviderChain:
    from .providers import AkshareProvider, TushareProvider

    providers: list[MarketDataProvider] = []
    if os.environ.get("TUSHARE_TOKEN"):
        providers.append(TushareProvider())
    if importlib.util.find_spec("akshare") is not None:
        providers.append(AkshareProvider())
    return MarketDataProviderChain(providers)


def _first_bar_on_or_after(bars: list[DailyBar], signal_date: date, symbol: str) -> DailyBar:
    for bar in sorted(bars, key=lambda item: item.date):
        if bar.date >= signal_date:
            return bar
    raise MarketDataError(f"{symbol}: no bar on or after {signal_date.isoformat()}")


def _latest_bar_on_or_before(bars: list[DailyBar], end_date: date, symbol: str) -> DailyBar:
    eligible = [bar for bar in bars if bar.date <= end_date]
    if not eligible:
        raise MarketDataError(f"{symbol}: no latest daily close")
    return sorted(eligible, key=lambda item: item.date)[-1]


def _coerce_bar(bar: DailyBar | dict) -> DailyBar:
    if isinstance(bar, DailyBar):
        return bar
    if not isinstance(bar, dict):
        raise MarketDataError(f"invalid bar: {bar!r}")
    return DailyBar(date=_parse_date(bar.get("date"), "bar date"), close=_parse_float(bar.get("close"), "bar close"))


def _parse_date(value: Any, label: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        raise MarketDataError(f"invalid {label}: {value!r}")
    text = value.strip()
    if not text:
        raise MarketDataError(f"invalid {label}: {value!r}")
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return date.fromisoformat(text[:10])
    if len(text) >= 8 and text[:8].isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError as exc:
        raise MarketDataError(f"invalid {label}: {value!r}") from exc


def _parse_float(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise MarketDataError(f"invalid {label}: {value!r}") from exc
    return parsed
