from __future__ import annotations

import subprocess
from datetime import UTC, datetime

from source_ingestion.core import FetchResult


class Last30DaysSubprocessFetcher:
    def __init__(self, script_path: str = "last30days.py", topics: list[str] | None = None, spawn=None):
        self.script_path = script_path
        self.topics = topics or []
        self._spawn = spawn or _default_spawn

    def __call__(self, cursor: str | None) -> FetchResult:
        if not self.topics:
            raise ValueError("last30days fetcher requires at least one topic")
        outputs = []
        for topic in self.topics:
            command = ["python3", self.script_path, topic, "--agent", "--emit=json"]
            outputs.append(self._spawn(command))
        next_cursor = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return FetchResult(items=outputs, next_cursor=next_cursor)


def _default_spawn(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout
