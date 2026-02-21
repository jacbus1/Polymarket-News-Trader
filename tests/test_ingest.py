"""Tests for RSS and GDELT ingestion modules."""
import json
from unittest.mock import patch, MagicMock

import pytest

from polymarket_news_trader.ingest.rss import fetch_rss, NewsItem
from polymarket_news_trader.ingest.gdelt import fetch_gdelt


# ---------------------------------------------------------------------------
# RSS tests
# ---------------------------------------------------------------------------

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <item>
      <title>Breaking: Market Rally</title>
      <link>https://example.com/1</link>
      <description>Stocks surge on economic data.</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
      <guid>https://example.com/1</guid>
    </item>
    <item>
      <title>Election Update</title>
      <link>https://example.com/2</link>
      <description>Candidate leads in polls.</description>
      <pubDate>Mon, 01 Jan 2024 13:00:00 +0000</pubDate>
      <guid>https://example.com/2</guid>
    </item>
  </channel>
</rss>"""


def test_fetch_rss_returns_news_items(tmp_path):
    """fetch_rss should parse feed entries into NewsItem objects."""
    import feedparser

    with patch("feedparser.parse") as mock_parse:
        # Build a minimal feedparser result
        entry1 = MagicMock()
        entry1.id = "https://example.com/1"
        entry1.title = "Breaking: Market Rally"
        entry1.summary = "Stocks surge on economic data."
        entry1.link = "https://example.com/1"
        entry1.published_parsed = (2024, 1, 1, 12, 0, 0, 0, 0, 0)

        entry2 = MagicMock()
        entry2.id = "https://example.com/2"
        entry2.title = "Election Update"
        entry2.summary = "Candidate leads in polls."
        entry2.link = "https://example.com/2"
        entry2.published_parsed = (2024, 1, 1, 13, 0, 0, 0, 0, 0)

        mock_feed = MagicMock()
        mock_feed.entries = [entry1, entry2]
        mock_parse.return_value = mock_feed

        items = fetch_rss("https://fake-feed.example.com/rss")

    assert len(items) == 2
    assert isinstance(items[0], NewsItem)
    assert items[0].title == "Breaking: Market Rally"
    assert items[1].id == "https://example.com/2"


def test_fetch_rss_empty_feed():
    """fetch_rss should return an empty list for an empty feed."""
    with patch("feedparser.parse") as mock_parse:
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        items = fetch_rss("https://empty.example.com/rss")
    assert items == []


# ---------------------------------------------------------------------------
# GDELT tests
# ---------------------------------------------------------------------------

GDELT_RESPONSE = {
    "articles": [
        {"url": "https://news.example.com/a1", "title": "President Signs Bill", "seendate": "20240101T120000Z"},
        {"url": "https://news.example.com/a2", "title": "Trade Deal Reached", "seendate": "20240101T130000Z"},
    ]
}


def test_fetch_gdelt_returns_items():
    """fetch_gdelt should parse GDELT API response into NewsItem objects."""
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = GDELT_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        items = fetch_gdelt("president bill")

    assert len(items) == 2
    assert items[0].title == "President Signs Bill"
    assert items[0].source == "gdelt"
    assert items[1].url == "https://news.example.com/a2"


def test_fetch_gdelt_network_error_returns_empty():
    """fetch_gdelt should return an empty list on network errors."""
    with patch("requests.get", side_effect=ConnectionError("timeout")):
        items = fetch_gdelt("anything")
    assert items == []
