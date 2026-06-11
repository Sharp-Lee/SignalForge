from __future__ import annotations

from hashlib import sha1

from source_ingestion.core import FetchResult


class RssAtomAdapter:
    def __init__(self, source_id: str, source_name: str, fetcher):
        self.source_id = source_id
        self.source_name = source_name
        self._fetcher = fetcher

    def fetch(self, cursor: str | None) -> FetchResult:
        return self._fetcher(cursor)

    def normalize(self, raw_item) -> list[dict]:
        title = raw_item.get("title")
        url = raw_item.get("link") or raw_item.get("url")
        published_at = raw_item.get("published_at") or raw_item.get("updated")
        body = raw_item.get("summary") or raw_item.get("description") or raw_item.get("body")
        if not (title and url and published_at and body):
            return []
        return [
            {
                "id": raw_item.get("id") or f"{self.source_id}-{_short_hash(url + title)}",
                "source": {
                    "id": self.source_id,
                    "name": self.source_name,
                    "published_at": published_at,
                    "url": url,
                },
                "title": title,
                "body": body,
                "signal_origin": "news",
                "type_tag": raw_item.get("type_tag") or _infer_type_tag(title, body),
                "triage": {"excluded": False, "reasons": []},
                "raw_payload": raw_item,
            }
        ]


def _short_hash(value: str) -> str:
    return sha1(value.encode("utf-8")).hexdigest()[:12]


def _infer_type_tag(title: str, body: str) -> str:
    text = f"{title}\n{body}".lower()
    if any(term in text for term in ("supply", "lead time", "shortage", "capacity", "disruption")):
        return "supply_demand_bottleneck"
    if any(term in text for term in ("policy", "regulation", "tariff")):
        return "policy"
    if any(term in text for term in ("weather", "flood", "climate", "rain")):
        return "weather_climate"
    if any(term in text for term in ("export control", "sanction", "geopolitical")):
        return "export_control_geopolitics"
    if any(term in text for term in ("technology", "breakthrough", "inflection")):
        return "technology_inflection"
    return "other"

