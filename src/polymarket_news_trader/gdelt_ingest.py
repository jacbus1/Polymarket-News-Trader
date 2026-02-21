from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import calendar
import time
import requests

from .news import NewsItem


GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


@dataclass(frozen=True)
class GdeltQuery:
    query: str
    max_records: int = 100
    language: str | None = None
    timespan: str = "30min"
    mode: str = "ArtList"


def _parse_ts(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        # GDELT uses YYYYMMDDHHMMSS
        return int(calendar.timegm(time.strptime(date_str, "%Y%m%d%H%M%S")))
    except Exception:
        return None


def fetch_gdelt(query: GdeltQuery, *, category: str = "gdelt") -> list[NewsItem]:
    params = {
        "query": query.query,
        "mode": query.mode,
        "maxrecords": str(query.max_records),
        "timespan": query.timespan,
        "format": "json",
    }
    if query.language:
        params["language"] = query.language

    resp = requests.get(GDELT_DOC_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json() or {}
    articles = data.get("articles") or []

    items: list[NewsItem] = []
    for a in articles:
        url = str(a.get("url") or "")
        title = str(a.get("title") or "")
        snippet = str(a.get("seendate") or "")
        published = str(a.get("seendate") or "")
        published_ts = _parse_ts(str(a.get("seendate") or ""))
        item_id = str(a.get("url") or a.get("urlid") or a.get("sourceCountry") or title)

        items.append(
            NewsItem(
                source="gdelt",
                category=category,
                item_id=item_id,
                title=title,
                summary=snippet,
                link=url,
                published=published,
                published_ts=published_ts,
            )
        )

    return items


def fetch_gdelt_all(queries: Iterable[dict]) -> list[NewsItem]:
    out: list[NewsItem] = []
    for q in queries:
        query = str(q.get("query") or "").strip()
        if not query:
            continue
        out.extend(
            fetch_gdelt(
                GdeltQuery(
                    query=query,
                    max_records=int(q.get("max_records") or 100),
                    language=q.get("language"),
                    timespan=str(q.get("timespan") or "30min"),
                    mode=str(q.get("mode") or "ArtList"),
                ),
                category=str(q.get("category") or "gdelt"),
            )
        )
    return out
