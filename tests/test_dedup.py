"""Tests for the deduplication / seen-store module."""
import json
import os

import pytest

from polymarket_news_trader.store.dedup import SeenStore
from polymarket_news_trader.ingest.rss import NewsItem


def _make_item(item_id: str, title: str = "Headline") -> NewsItem:
    return NewsItem(id=item_id, title=title, summary="", url="https://example.com")


def test_new_items_are_not_seen(tmp_path):
    store = SeenStore(path=str(tmp_path / "seen.json"))
    item = _make_item("abc123")
    assert not store.is_seen("abc123")


def test_mark_seen_persists(tmp_path):
    path = str(tmp_path / "seen.json")
    store = SeenStore(path=path)
    store.mark_seen("abc123")
    # Reload from disk
    store2 = SeenStore(path=path)
    assert store2.is_seen("abc123")


def test_filter_new_removes_seen(tmp_path):
    store = SeenStore(path=str(tmp_path / "seen.json"))
    items = [_make_item("id1"), _make_item("id2"), _make_item("id3")]
    # First pass: all are new
    new = store.filter_new(items)
    assert len(new) == 3
    # Second pass: all are seen
    new2 = store.filter_new(items)
    assert new2 == []


def test_filter_new_partial(tmp_path):
    store = SeenStore(path=str(tmp_path / "seen.json"))
    store.mark_seen("id1")
    items = [_make_item("id1"), _make_item("id2")]
    new = store.filter_new(items)
    assert len(new) == 1
    assert new[0].id == "id2"


def test_corrupted_store_recovers(tmp_path):
    path = str(tmp_path / "seen.json")
    with open(path, "w") as f:
        f.write("not valid json{{{")
    store = SeenStore(path=path)
    assert not store.is_seen("anything")
