from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.request import urlopen
from xml.etree import ElementTree

from source_ingestion.core import FetchResult


class RssHttpFetcher:
    def __init__(self, url: str, http_get=None):
        self.url = url
        self._http_get = http_get or _default_http_get

    def __call__(self, cursor: str | None) -> FetchResult:
        payload = self._http_get(self.url)
        items = _parse_feed(payload)
        if cursor:
            items = _filter_newer_than(items, cursor)
        next_cursor = _max_published_at(items) or cursor
        return FetchResult(items=items, next_cursor=next_cursor)


def _default_http_get(url: str) -> bytes:
    with urlopen(url, timeout=20) as response:
        return response.read()


def _parse_feed(payload: bytes | str) -> list[dict]:
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    root = ElementTree.fromstring(payload)
    if _strip_namespace(root.tag) == "rss":
        return _parse_rss(root)
    if _strip_namespace(root.tag) == "feed":
        return _parse_atom(root)
    return []


def _parse_rss(root) -> list[dict]:
    items = []
    for item in root.findall(".//item"):
        title = _text(item, "title")
        link = _text(item, "link")
        published_at = _normalize_datetime(_text(item, "pubDate") or _text(item, "date"))
        summary = _text(item, "description") or _text(item, "summary")
        item_id = _text(item, "guid") or link
        if not (item_id and title and link and published_at and summary):
            continue
        items.append(
            {
                "id": item_id,
                "title": title,
                "link": link,
                "published_at": published_at,
                "summary": summary,
            }
        )
    return items


def _parse_atom(root) -> list[dict]:
    items = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns) or root.findall("entry")
    for entry in entries:
        title = _text(entry, "title")
        link_node = entry.find("atom:link", ns) or entry.find("link")
        link = link_node.get("href") if link_node is not None else None
        published_at = _normalize_datetime(_text(entry, "updated") or _text(entry, "published"))
        summary = _text(entry, "summary") or _text(entry, "content")
        item_id = _text(entry, "id") or link
        if not (item_id and title and link and published_at and summary):
            continue
        items.append(
            {
                "id": item_id,
                "title": title,
                "link": link,
                "published_at": published_at,
                "summary": summary,
            }
        )
    return items


def _filter_newer_than(items: list[dict], cursor: str) -> list[dict]:
    cursor_dt = _parse_datetime(cursor)
    if cursor_dt is None:
        return items
    return [
        item
        for item in items
        if (item_dt := _parse_datetime(item.get("published_at"))) is not None and item_dt > cursor_dt
    ]


def _max_published_at(items: list[dict]) -> str | None:
    datetimes = [_parse_datetime(item.get("published_at")) for item in items]
    valid = [value for value in datetimes if value is not None]
    if not valid:
        return None
    return _to_iso(max(valid))


def _normalize_datetime(value: str | None) -> str | None:
    parsed = _parse_datetime(value)
    return _to_iso(parsed) if parsed else value


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError):
            return None


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text(node, child_name: str) -> str | None:
    for child in list(node):
        if _strip_namespace(child.tag) == child_name:
            return child.text.strip() if child.text else None
    return None


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
