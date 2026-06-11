from __future__ import annotations

from news_contracts.adapters.last30days import adapt_last30days_agent_output
from source_ingestion.core import FetchResult


class Last30DaysAdapter:
    source_id = "last30days"

    def __init__(self, fetcher):
        self._fetcher = fetcher

    def fetch(self, cursor: str | None) -> FetchResult:
        return self._fetcher(cursor)

    def normalize(self, raw_item) -> list[dict]:
        return adapt_last30days_agent_output(raw_item)

