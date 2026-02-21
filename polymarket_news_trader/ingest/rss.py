"""RSS/Atom feed ingestion module."""
import feedparser
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsItem:
    """Represents a single ingested news headline."""
    id: str           # Unique identifier (usually the entry link or guid)
    title: str
    summary: str
    url: str
    published: Optional[datetime] = None
    source: str = ""


def fetch_rss(feed_url: str) -> List[NewsItem]:
    """Fetch and parse an RSS/Atom feed, returning a list of NewsItem objects."""
    feed = feedparser.parse(feed_url)
    items: List[NewsItem] = []
    for entry in feed.entries:
        item_id = getattr(entry, "id", None) or getattr(entry, "link", "")
        title = getattr(entry, "title", "")
        summary = getattr(entry, "summary", title)
        url = getattr(entry, "link", "")
        published: Optional[datetime] = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except Exception:
                published = None
        items.append(NewsItem(id=item_id, title=title, summary=summary, url=url, published=published, source=feed_url))
    return items
