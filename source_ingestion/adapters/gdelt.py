from __future__ import annotations

from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.core import FetchResult


class GdeltFixtureAdapter:
    def __init__(self, source_id: str, source_name: str, fetcher):
        self.source_id = source_id
        self.source_name = source_name
        self._fetcher = fetcher

    def fetch(self, cursor: str | None) -> FetchResult:
        return self._fetcher(cursor)

    def normalize(self, raw_item) -> list[dict]:
        mapped = {
            "id": raw_item.get("id"),
            "title": raw_item.get("title"),
            "link": raw_item.get("url"),
            "published_at": raw_item.get("seendate") or raw_item.get("published_at"),
            "summary": raw_item.get("summary") or raw_item.get("body"),
            "type_tag": raw_item.get("type_tag"),
            "gdelt": raw_item,
        }
        adapter = RssAtomAdapter(self.source_id, self.source_name, lambda cursor: FetchResult([]))
        signals = adapter.normalize(mapped)
        for signal in signals:
            signal["raw_payload"] = raw_item
        return signals

