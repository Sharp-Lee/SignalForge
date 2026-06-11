from __future__ import annotations

from datetime import date
import os
from typing import Any

from .core import DailyBar, MarketDataError, scoped_no_proxy


class TushareProvider:
    name = "tushare"

    def __init__(self, token: str | None = None, client: Any | None = None):
        self.token = token
        self._client = client

    def _get_client(self):
        if self._client is None:
            token = self.token or os.environ.get("TUSHARE_TOKEN")
            if not token:
                raise MarketDataError("TUSHARE_TOKEN not configured")
            import tushare as ts

            self._client = ts.pro_api(token)
        return self._client

    def daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar]:
        with scoped_no_proxy():
            df = self._get_client().daily(
                ts_code=_to_tushare_symbol(symbol),
                start_date=_format_date(start_date),
                end_date=_format_date(end_date),
            )
        return _rows_to_bars(df, date_field="trade_date", close_field="close")

    def security_names(self, symbols: list[str]) -> dict[str, str]:
        with scoped_no_proxy():
            df = self._get_client().stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,market,industry,list_status",
            )
        rows = _records(df)
        wanted = {_to_tushare_symbol(symbol) for symbol in symbols}
        return {
            str(row["ts_code"]): str(row["name"]).strip()
            for row in rows
            if str(row.get("ts_code")) in wanted and str(row.get("name", "")).strip()
        }


class AkshareProvider:
    name = "akshare"

    def __init__(self, ak_module: Any | None = None):
        self._ak = ak_module

    def _get_ak(self):
        if self._ak is None:
            import akshare as ak

            self._ak = ak
        return self._ak

    def daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar]:
        with scoped_no_proxy():
            df = self._get_ak().stock_zh_a_daily(symbol=_to_akshare_daily_symbol(symbol))
        bars = _rows_to_bars(df, date_field="date", close_field="close")
        return [bar for bar in bars if start_date <= bar.date <= end_date]

    def security_names(self, symbols: list[str]) -> dict[str, str]:
        with scoped_no_proxy():
            df = self._get_ak().stock_info_a_code_name()
        wanted = {_plain_code(symbol): symbol for symbol in symbols}
        names: dict[str, str] = {}
        for row in _records(df):
            code = str(row.get("code", "")).zfill(6)
            name = str(row.get("name", "")).strip()
            if code in wanted and name:
                names[wanted[code]] = name
        return names


def _rows_to_bars(df, *, date_field: str, close_field: str) -> list[DailyBar]:
    bars: list[DailyBar] = []
    for row in _records(df):
        raw_date = row.get(date_field)
        raw_close = row.get(close_field)
        try:
            close = float(raw_close)
        except (TypeError, ValueError) as exc:
            raise MarketDataError(f"invalid close {raw_close!r}") from exc
        bars.append(DailyBar(date=_parse_provider_date(raw_date), close=close))
    return sorted(bars, key=lambda bar: bar.date)


def _records(df) -> list[dict]:
    if df is None:
        return []
    if hasattr(df, "to_dict"):
        return list(df.to_dict("records"))
    if isinstance(df, list):
        return [dict(row) for row in df]
    raise MarketDataError(f"unsupported provider frame: {type(df).__name__}")


def _parse_provider_date(value) -> date:
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return date.fromisoformat(text[:10])
    if len(text) >= 8 and text[:8].isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    raise MarketDataError(f"invalid trade date {value!r}")


def _format_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def _to_tushare_symbol(symbol: str) -> str:
    plain = _plain_code(symbol)
    if symbol.endswith(".SH") or plain.startswith("6") or plain.startswith("9"):
        return f"{plain}.SH"
    return f"{plain}.SZ"


def _to_akshare_daily_symbol(symbol: str) -> str:
    plain = _plain_code(symbol)
    prefix = "sh" if symbol.endswith(".SH") or plain.startswith("6") or plain.startswith("9") else "sz"
    return f"{prefix}{plain}"


def _plain_code(symbol: str) -> str:
    return symbol.split(".")[0].zfill(6)
