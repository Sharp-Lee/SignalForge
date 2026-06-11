from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class FetchResult:
    items: list
    next_cursor: str | None = None


class Fetcher(Protocol):
    def __call__(self, cursor: str | None) -> FetchResult:
        ...


class SourceAdapter(Protocol):
    source_id: str

    def fetch(self, cursor: str | None) -> FetchResult:
        ...

    def normalize(self, raw_item) -> list[dict]:
        ...


class FixtureFetcher:
    def __init__(self, items: list, next_cursor: str | None = None):
        self.items = items
        self.next_cursor = next_cursor
        self.calls: list[str | None] = []

    def __call__(self, cursor: str | None) -> FetchResult:
        self.calls.append(cursor)
        return FetchResult(items=list(self.items), next_cursor=self.next_cursor)


@dataclass
class SourceRunResult:
    source_id: str
    accepted: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class IngestionRunResult:
    by_source: dict[str, SourceRunResult] = field(default_factory=dict)

