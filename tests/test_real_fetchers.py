import json

from news_contracts.storage import ContractStore
from source_ingestion.adapters.rss import RssAtomAdapter
from source_ingestion.core import FetchResult, FixtureFetcher
from source_ingestion.fetchers.last30days import Last30DaysSubprocessFetcher
from source_ingestion.fetchers import rss as rss_fetcher
from source_ingestion.fetchers.rss import RSS_BROWSER_USER_AGENT, RssHttpFetcher
from source_ingestion.runner import run_once


RSS_XML_OLDEST_FIRST = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <guid>old-guid</guid>
      <title>Old copper story</title>
      <link>https://example.com/old</link>
      <pubDate>2026-06-08T08:00:00Z</pubDate>
      <description>Old story with prices up 11%.</description>
    </item>
    <item>
      <guid>new-guid</guid>
      <title>New copper disruption lifts prices 12%</title>
      <link>https://example.com/new</link>
      <pubDate>2026-06-09T08:00:00Z</pubDate>
      <description>New disruption cuts output 12% this quarter.</description>
    </item>
  </channel>
</rss>
"""

RSS_XML_NEWEST_FIRST = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <guid>new-guid</guid>
      <title>New copper disruption lifts prices 12%</title>
      <link>https://example.com/new</link>
      <pubDate>Tue, 09 Jun 2026 08:00:00 GMT</pubDate>
      <description>New disruption cuts output 12% this quarter.</description>
    </item>
    <item>
      <guid>old-guid</guid>
      <title>Old copper story</title>
      <link>https://example.com/old</link>
      <pubDate>Mon, 08 Jun 2026 08:00:00 GMT</pubDate>
      <description>Old story with prices up 11%.</description>
    </item>
  </channel>
</rss>
"""


def test_rss_http_fetcher_uses_injected_transport_and_parses_feed():
    calls = []

    def http_get(url):
        calls.append(url)
        return RSS_XML_OLDEST_FIRST

    fetcher = RssHttpFetcher(url="https://example.com/feed.xml", http_get=http_get)

    result = fetcher(cursor=None)

    assert calls == ["https://example.com/feed.xml"]
    assert [item["id"] for item in result.items] == ["old-guid", "new-guid"]
    assert result.next_cursor == "2026-06-09T08:00:00Z"


def test_default_rss_http_get_uses_browser_user_agent(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return RSS_XML_OLDEST_FIRST

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["user_agent"] = request.get_header("User-agent")
        captured["accept"] = request.get_header("Accept")
        return FakeResponse()

    monkeypatch.setattr(rss_fetcher, "urlopen", fake_urlopen)

    payload = rss_fetcher._default_http_get("https://example.com/feed.xml")

    assert payload == RSS_XML_OLDEST_FIRST
    assert captured == {
        "url": "https://example.com/feed.xml",
        "timeout": 20,
        "user_agent": RSS_BROWSER_USER_AGENT,
        "accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }


def test_rss_http_fetcher_cursor_skips_already_seen_entries_oldest_first():
    def http_get(url):
        return RSS_XML_OLDEST_FIRST

    fetcher = RssHttpFetcher(url="https://example.com/feed.xml", http_get=http_get)

    result = fetcher(cursor="2026-06-08T08:00:00Z")

    assert [item["id"] for item in result.items] == ["new-guid"]
    assert result.next_cursor == "2026-06-09T08:00:00Z"


def test_rss_http_fetcher_newest_first_cursor_keeps_new_entries():
    def http_get(url):
        return RSS_XML_NEWEST_FIRST

    fetcher = RssHttpFetcher(url="https://example.com/feed.xml", http_get=http_get)

    result = fetcher(cursor="2026-06-08T08:00:00Z")

    assert [item["id"] for item in result.items] == ["new-guid"]
    assert result.next_cursor == "2026-06-09T08:00:00Z"


def test_last30days_fetcher_uses_real_topic_command_without_since():
    calls = []
    output = json.dumps(
        [
            {
                "title": "AI server lead times expand",
                "body": "Lead times expanded from 4 weeks to 12 weeks.",
                "url": "https://example.com/last30/ai",
                "published_at": "2026-06-09T08:00:00Z",
            }
        ]
    )

    def spawn(command):
        calls.append(command)
        return output

    fetcher = Last30DaysSubprocessFetcher(
        script_path="/tmp/last30days.py",
        topics=["AI server supply chain"],
        spawn=spawn,
    )

    result = fetcher(cursor="2026-06-08T00:00:00Z")

    assert calls == [["python3", "/tmp/last30days.py", "AI server supply chain", "--agent", "--emit=json"]]
    assert "--since" not in calls[0]
    assert result.items == [output]
    assert result.next_cursor is not None


def test_runner_records_fetch_error_and_continues_other_sources(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    class FailingAdapter:
        source_id = "rss:bad"

        def fetch(self, cursor):
            raise TimeoutError("network timed out")

        def normalize(self, raw_item):
            return []

    good_adapter = RssAtomAdapter(
        source_id="rss:good",
        source_name="Good RSS",
        fetcher=FixtureFetcher(
            [
                {
                    "id": "good-1",
                    "title": "Copper supply disruption lifts prices 12%",
                    "link": "https://example.com/rss/copper",
                    "published_at": "2026-06-09T08:00:00Z",
                    "summary": "Chile mine disruption cuts output by 12% this quarter.",
                }
            ],
            next_cursor="good-cursor",
        ),
    )

    result = run_once(store, [FailingAdapter(), good_adapter])

    assert result.by_source["rss:bad"].accepted == 0
    assert result.by_source["rss:bad"].rejected == 0
    assert "network timed out" in result.by_source["rss:bad"].errors[0]
    assert store.get_source_cursor("rss:bad") is None
    assert result.by_source["rss:good"].accepted == 1
    assert store.get_source_cursor("rss:good") == "good-cursor"


def test_runner_records_normalize_error_and_continues_other_sources(tmp_path):
    store = ContractStore(tmp_path / "contracts.db")

    class BadNormalizeAdapter:
        source_id = "rss:bad-normalize"

        def fetch(self, cursor):
            return FetchResult(items=[{"bad": True}], next_cursor="bad-normalize-cursor")

        def normalize(self, raw_item):
            raise ValueError("invalid feed item shape")

    good_adapter = RssAtomAdapter(
        source_id="rss:good",
        source_name="Good RSS",
        fetcher=FixtureFetcher(
            [
                {
                    "id": "good-1",
                    "title": "Copper supply disruption lifts prices 12%",
                    "link": "https://example.com/rss/copper",
                    "published_at": "2026-06-09T08:00:00Z",
                    "summary": "Chile mine disruption cuts output by 12% this quarter.",
                }
            ],
            next_cursor="good-cursor",
        ),
    )

    result = run_once(store, [BadNormalizeAdapter(), good_adapter])

    assert result.by_source["rss:bad-normalize"].accepted == 0
    assert result.by_source["rss:bad-normalize"].rejected == 1
    assert "invalid feed item shape" in result.by_source["rss:bad-normalize"].errors[0]
    assert result.by_source["rss:good"].accepted == 1
    assert store.get_source_cursor("rss:good") == "good-cursor"
