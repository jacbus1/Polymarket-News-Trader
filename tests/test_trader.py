"""Tests for the order execution module."""
from unittest.mock import patch, MagicMock

import pytest

from polymarket_news_trader.ingest.rss import NewsItem
from polymarket_news_trader.rules.matcher import Rule, Signal
from polymarket_news_trader.markets.selector import MarketSelection
from polymarket_news_trader.execution.trader import Trader, OrderResult


def _make_signal(order_type="market", limit_price=None):
    rule = Rule(
        name="test-rule",
        keywords=["test"],
        market_tag="test market",
        outcome="YES",
        side="BUY",
        size=10.0,
        order_type=order_type,
        limit_price=limit_price,
    )
    item = NewsItem(id="item1", title="Test", summary="", url="https://example.com")
    return Signal(rule=rule, item=item)


def _make_selection() -> MarketSelection:
    return MarketSelection(
        condition_id="cond1",
        question="Will event X happen?",
        outcome="YES",
        token_id="tok-yes-001",
        market_slug="event-x",
    )


def test_dry_run_does_not_call_api():
    trader = Trader(api_key="", live_mode=False)
    signal = _make_signal()
    selection = _make_selection()

    with patch("requests.post") as mock_post:
        result = trader.submit(signal, selection)
        mock_post.assert_not_called()

    assert result.success
    assert result.dry_run


def test_live_market_order_success():
    trader = Trader(api_key="test-key", live_mode=True)
    signal = _make_signal(order_type="market")
    selection = _make_selection()

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"orderID": "order-abc"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        result = trader.submit(signal, selection)

    assert result.success
    assert result.order_id == "order-abc"
    assert not result.dry_run


def test_live_limit_order_success():
    trader = Trader(api_key="test-key", live_mode=True)
    signal = _make_signal(order_type="limit", limit_price=0.65)
    selection = _make_selection()

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"orderID": "order-xyz"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        result = trader.submit(signal, selection)

    assert result.success
    assert result.order_id == "order-xyz"
    # Verify the limit price was included in the payload
    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["json"]["price"] == 0.65


def test_live_order_http_error():
    trader = Trader(api_key="test-key", live_mode=True)
    signal = _make_signal()
    selection = _make_selection()

    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP 401 Unauthorized")
        mock_post.return_value = mock_resp
        result = trader.submit(signal, selection)

    assert not result.success
    assert "401" in result.message
