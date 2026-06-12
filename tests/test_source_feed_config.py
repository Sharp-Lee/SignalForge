import json

from source_ingestion.feed_config import build_rss_adapters, load_rss_source_configs


def test_example_rss_source_config_enables_curated_live_sources():
    configs = load_rss_source_configs()
    enabled = {config.id for config in configs if config.enabled}

    assert enabled == {
        "rss:servethehome",
        "rss:eetimes",
        "rss:semiwiki",
        "rss:edn",
        "rss:theregister",
        "rss:nvidia-blog",
        "rss:marketwatch-top",
        "rss:ritholtz",
        "rss:awealthofcommonsense",
    }
    assert "rss:businessinsider-markets" not in enabled
    assert "rss:wsj-markets" not in enabled
    assert "rss:tomshardware" not in enabled
    assert "rss:techpowerup" not in enabled


def test_rss_source_config_builds_only_enabled_adapters(tmp_path):
    config_path = tmp_path / "rss_sources.json"
    config_path.write_text(
        json.dumps(
            [
                {
                    "id": "rss:one",
                    "name": "One",
                    "url": "https://example.com/one.xml",
                    "enabled": True,
                    "quality": "industry",
                },
                {
                    "id": "rss:two",
                    "name": "Two",
                    "url": "https://example.com/two.xml",
                    "enabled": False,
                    "quality": "broad",
                },
            ]
        ),
        encoding="utf-8",
    )

    configs = load_rss_source_configs(config_path)
    adapters = build_rss_adapters(configs, http_get=lambda url: b"<rss><channel /></rss>")

    assert [adapter.source_id for adapter in adapters] == ["rss:one"]


def test_rss_source_config_can_be_overridden_by_env_url_list(monkeypatch):
    monkeypatch.setenv("NEWS_RSS_FEED_URLS", "https://example.com/a.xml, https://example.com/b.xml")

    configs = load_rss_source_configs()

    assert [(config.id, config.name, config.url, config.enabled) for config in configs] == [
        ("rss:env:1", "Configured RSS 1", "https://example.com/a.xml", True),
        ("rss:env:2", "Configured RSS 2", "https://example.com/b.xml", True),
    ]
