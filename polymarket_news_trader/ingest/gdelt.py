"""GDELT Doc API ingestion module (free, no API key required)."""
import requests
from typing import List, Optional
from .rss import NewsItem

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_gdelt(query: str, mode: str = "artlist", max_records: int = 25, timespan: str = "15min") -> List[NewsItem]:
    """
    Query the GDELT Doc API for articles matching *query*.

    Parameters
    ----------
    query:       Full-text search expression (e.g. "election president").
    mode:        GDELT output mode – "artlist" returns a JSON article list.
    max_records: Maximum number of articles to return (GDELT cap is 250).
    timespan:    How far back to look, e.g. "15min", "1h", "1d".

    Returns a list of NewsItem objects.
    """
    params = {
        "query": query,
        "mode": mode,
        "maxrecords": max_records,
        "timespan": timespan,
        "format": "json",
    }
    try:
        resp = requests.get(GDELT_DOC_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    articles = data.get("articles") or []
    items: List[NewsItem] = []
    for art in articles:
        url = art.get("url", "")
        title = art.get("title", "")
        items.append(
            NewsItem(
                id=url,
                title=title,
                summary="",
                url=url,
                published=None,
                source="gdelt",
            )
        )
    return items
