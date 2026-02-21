"""Tests for the Polymarket market/outcome selector."""
from unittest.mock import patch, MagicMock

import pytest

from polymarket_news_trader.markets.selector import select_market, fetch_markets, MarketSelection

SAMPLE_MARKETS = [
    {
        "condition_id": "cond-001",
        "question": "Will the US presidential election result in a Republican win?",
        "market_slug": "us-election-republican",
        "tokens": [
            {"outcome": "YES", "token_id": "tok-yes-001"},
            {"outcome": "NO", "token_id": "tok-no-001"},
        ],
    },
    {
        "condition_id": "cond-002",
        "question": "Will the Fed raise interest rates in Q1 2024?",
        "market_slug": "fed-rate-q1-2024",
        "tokens": [
            {"outcome": "YES", "token_id": "tok-yes-002"},
            {"outcome": "NO", "token_id": "tok-no-002"},
        ],
    },
]


def test_select_market_returns_best_match():
    sel = select_market("presidential election", "YES", markets=SAMPLE_MARKETS)
    assert sel is not None
    assert "election" in sel.question.lower()
    assert sel.outcome == "YES"
    assert sel.token_id == "tok-yes-001"


def test_select_market_no_match_returns_none():
    sel = select_market("completely unrelated topic xyz", "YES", markets=SAMPLE_MARKETS)
    assert sel is None


def test_select_market_outcome_no():
    sel = select_market("presidential election", "NO", markets=SAMPLE_MARKETS)
    assert sel is not None
    assert sel.token_id == "tok-no-001"
    assert sel.outcome == "NO"


def test_fetch_markets_success():
    fake_response = [{"question": "Test market"}]
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = fake_response
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        markets = fetch_markets(limit=10)
    assert markets == fake_response


def test_fetch_markets_network_error_returns_empty():
    with patch("requests.get", side_effect=ConnectionError("timeout")):
        markets = fetch_markets()
    assert markets == []
