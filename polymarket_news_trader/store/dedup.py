"""Deduplication and local persistence module.

Seen event IDs are stored in a JSON file so they survive restarts.
"""
import json
import os
from typing import Iterable, List, Set

from ..ingest.rss import NewsItem

DEFAULT_STORE_PATH = os.path.join(os.path.expanduser("~"), ".polymarket_news_trader", "seen.json")


class SeenStore:
    """Tracks which NewsItem IDs have already been processed."""

    def __init__(self, path: str = DEFAULT_STORE_PATH) -> None:
        self.path = path
        self._seen: Set[str] = set()
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self._seen = set(data.get("seen", []))
            except (json.JSONDecodeError, OSError):
                self._seen = set()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump({"seen": list(self._seen)}, fh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def is_seen(self, item_id: str) -> bool:
        return item_id in self._seen

    def mark_seen(self, item_id: str) -> None:
        self._seen.add(item_id)
        self._save()

    def filter_new(self, items: Iterable[NewsItem]) -> List[NewsItem]:
        """Return only items whose ID has not been seen, and mark them."""
        new_items: List[NewsItem] = []
        for item in items:
            if not self.is_seen(item.id):
                new_items.append(item)
                self.mark_seen(item.id)
        return new_items
