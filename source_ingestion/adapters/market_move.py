from __future__ import annotations

from hashlib import sha1

from source_ingestion.core import FetchResult


class MarketMoveAdapter:
    source_id = "market_move"
    source_name = "Market Move Scan"

    def __init__(self, fetcher):
        self._fetcher = fetcher

    def fetch(self, cursor: str | None) -> FetchResult:
        return self._fetcher(cursor)

    def normalize(self, raw_item) -> list[dict]:
        title = raw_item.get("title")
        url = raw_item.get("url")
        published_at = raw_item.get("published_at")
        body = raw_item.get("body")
        if not (title and url and published_at and body):
            return []
        return [
            {
                "id": raw_item.get("id") or f"market-move-{_short_hash(url + title)}",
                "source": {
                    "id": self.source_id,
                    "name": self.source_name,
                    "published_at": published_at,
                    "url": url,
                },
                "title": title,
                "body": body,
                "signal_origin": "market_move",
                "type_tag": raw_item.get("type_tag") or "other",
                "triage": {"excluded": False, "reasons": []},
                "raw_payload": raw_item,
                "trigger_reason": raw_item.get("trigger_reason", {}),
            }
        ]


def _short_hash(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()[:12]

