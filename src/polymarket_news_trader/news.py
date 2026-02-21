from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import calendar
import feedparser


@dataclass(frozen=True)
class NewsItem:
    source: str
    category: str
    item_id: str
    title: str
    summary: str
    link: str
    published: str
    published_ts: int | None


def _parse_published_ts(entry) -> int | None:
    ts = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not ts:
        return None
    try:
        return int(calendar.timegm(ts))
    except Exception:
        return None


def fetch_feed(url: str, *, category: str = "general") -> list[NewsItem]:
    feed = feedparser.parse(url)
    items: list[NewsItem] = []

    for entry in feed.entries or []:
        link = getattr(entry, "link", "") or ""
        entry_id = (
            getattr(entry, "id", None)
            or getattr(entry, "guid", None)
            or link
            or (getattr(entry, "title", "") + ":" + (getattr(entry, "published", "") or ""))
        )
        title = getattr(entry, "title", "") or ""
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        published = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
        published_ts = _parse_published_ts(entry)

        items.append(
            NewsItem(
                source=url,
                category=category,
                item_id=str(entry_id),
                title=title.strip(),
                summary=summary.strip(),
                link=link.strip(),
                published=published.strip(),
                published_ts=published_ts,
            )
        )

    return items


def fetch_all(feeds: Iterable[dict]) -> list[NewsItem]:
    out: list[NewsItem] = []
    for feed in feeds:
        out.extend(fetch_feed(str(feed["url"]), category=str(feed.get("category") or "general")))
    return out
