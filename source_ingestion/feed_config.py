from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable

from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.fetchers.rss import RssHttpFetcher


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RSS_SOURCES_FILE = PROJECT_ROOT / "config" / "rss_sources.example.json"


@dataclass(frozen=True)
class RssSourceConfig:
    id: str
    name: str
    url: str
    enabled: bool = True
    quality: str = "standard"
    domain: str = "general"


def load_rss_source_configs(path: str | Path | None = None) -> list[RssSourceConfig]:
    env_urls = os.environ.get("NEWS_RSS_FEED_URLS")
    if path is None and env_urls:
        return _configs_from_url_list(env_urls)
    resolved = _resolve_config_path(path)
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("RSS source config must be a list")
    configs = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("RSS source config entries must be objects")
        configs.append(
            RssSourceConfig(
                id=_required_text(item, "id"),
                name=_required_text(item, "name"),
                url=_required_text(item, "url"),
                enabled=bool(item.get("enabled", True)),
                quality=str(item.get("quality") or "standard"),
                domain=str(item.get("domain") or "general"),
            )
        )
    return configs


def _configs_from_url_list(value: str) -> list[RssSourceConfig]:
    configs = []
    for index, url in enumerate([part.strip() for part in value.split(",") if part.strip()], start=1):
        configs.append(
            RssSourceConfig(
                id=f"rss:env:{index}",
                name=f"Configured RSS {index}",
                url=url,
                enabled=True,
                quality="configured",
                domain="configured",
            )
        )
    return configs


def build_rss_adapters(
    configs: list[RssSourceConfig],
    *,
    http_get: Callable[[str], bytes] | None = None,
):
    adapters = []
    for config in configs:
        if not config.enabled:
            continue
        adapters.append(
            RssAtomAdapter(
                config.id,
                config.name,
                RssHttpFetcher(config.url, http_get=http_get),
            )
        )
    return adapters


def _resolve_config_path(path: str | Path | None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    env_path = os.environ.get("NEWS_RSS_SOURCES_FILE")
    if env_path:
        return Path(env_path).expanduser()
    local_path = PROJECT_ROOT / ".local" / "rss_sources.json"
    if local_path.exists():
        return local_path
    return DEFAULT_RSS_SOURCES_FILE


def _required_text(item: dict, field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"RSS source config requires {field_name}")
    return value.strip()
