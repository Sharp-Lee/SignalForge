"""Real A-share market data and universe helpers."""

from .core import (
    DailyBar,
    MarketDataError,
    MarketDataProvider,
    MarketDataProviderChain,
    RealPriceLookup,
    UniverseBuildResult,
    build_default_provider_chain,
    build_default_universe,
    build_universe,
    scoped_no_proxy,
)
from .universe import DEFAULT_A_SHARE_ALLOWLIST

__all__ = [
    "DEFAULT_A_SHARE_ALLOWLIST",
    "DailyBar",
    "MarketDataError",
    "MarketDataProvider",
    "MarketDataProviderChain",
    "RealPriceLookup",
    "UniverseBuildResult",
    "build_default_provider_chain",
    "build_default_universe",
    "build_universe",
    "scoped_no_proxy",
]
