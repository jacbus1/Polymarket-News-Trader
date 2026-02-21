"""Polymarket market/outcome selector.

Fetches active markets from the Polymarket CLOB REST API and selects
the best matching market+token based on a free-text tag from a Rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

import requests

POLYMARKET_GAMMA_API = "https://gamma-api.polymarket.com/markets"
_DEFAULT_LIMIT = 100


@dataclass
class MarketSelection:
    condition_id: str
    question: str
    outcome: str          # "YES" or "NO"
    token_id: str
    market_slug: str


def fetch_markets(limit: int = _DEFAULT_LIMIT, closed: bool = False) -> List[dict]:
    """Fetch a page of active markets from the Polymarket Gamma API."""
    params: dict = {"limit": limit, "closed": str(closed).lower()}
    try:
        resp = requests.get(POLYMARKET_GAMMA_API, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def select_market(market_tag: str, outcome: str, markets: Optional[List[dict]] = None) -> Optional[MarketSelection]:
    """Return the best matching MarketSelection for *market_tag* / *outcome*.

    The match is determined by the number of words from *market_tag* that
    appear in the market question (case-insensitive).  If no market is
    found, returns None.
    """
    if markets is None:
        markets = fetch_markets()

    tag_words = set(re.findall(r"\w+", market_tag.lower()))
    best_score = 0
    best_market: Optional[dict] = None

    for mkt in markets:
        question: str = mkt.get("question", "")
        q_words = set(re.findall(r"\w+", question.lower()))
        score = len(tag_words & q_words)
        if score > best_score:
            best_score = score
            best_market = mkt

    if best_market is None or best_score == 0:
        return None

    # Extract token ID for the requested outcome
    tokens: List[dict] = best_market.get("tokens", [])
    token_id = ""
    for tok in tokens:
        if tok.get("outcome", "").upper() == outcome.upper():
            token_id = tok.get("token_id", "")
            break

    return MarketSelection(
        condition_id=best_market.get("condition_id", ""),
        question=best_market.get("question", ""),
        outcome=outcome.upper(),
        token_id=token_id,
        market_slug=best_market.get("market_slug", ""),
    )
