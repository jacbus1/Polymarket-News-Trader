"""Tests for the backtesting engine."""
import pytest

from polymarket_news_trader.ingest.rss import NewsItem
from polymarket_news_trader.rules.matcher import Rule, Signal
from polymarket_news_trader.markets.selector import MarketSelection
from polymarket_news_trader.backtest.engine import run_backtest, BacktestResult


def _make_signal(rule_name="test-rule", side="BUY", size=10.0, outcome="YES") -> Signal:
    rule = Rule(
        name=rule_name,
        keywords=["test"],
        market_tag="test market",
        outcome=outcome,
        side=side,
        size=size,
    )
    item = NewsItem(id="item1", title="Test headline", summary="", url="https://example.com")
    return Signal(rule=rule, item=item)


def _make_selection(token_id="tok1") -> MarketSelection:
    return MarketSelection(
        condition_id="cond1",
        question="Will event X happen?",
        outcome="YES",
        token_id=token_id,
        market_slug="event-x",
    )


def test_backtest_no_resolution():
    signal = _make_signal()
    selection = _make_selection()
    result = run_backtest([(signal, selection)], prices={"tok1": 0.6})
    assert len(result.trades) == 1
    assert result.trades[0].fill_price == 0.6
    assert not result.trades[0].resolved


def test_backtest_with_resolution_win():
    signal = _make_signal(side="BUY", size=10.0)
    selection = _make_selection()
    result = run_backtest(
        [(signal, selection)],
        prices={"tok1": 0.6},
        resolution_prices={"tok1": 1.0},
    )
    trade = result.trades[0]
    assert trade.resolved
    assert trade.pnl > 0  # bought at 0.6, resolved at 1.0 -> profit


def test_backtest_with_resolution_loss():
    signal = _make_signal(side="BUY", size=10.0)
    selection = _make_selection()
    result = run_backtest(
        [(signal, selection)],
        prices={"tok1": 0.6},
        resolution_prices={"tok1": 0.0},
    )
    trade = result.trades[0]
    assert trade.resolved
    assert trade.pnl < 0  # bought at 0.6, resolved at 0.0 -> loss


def test_backtest_total_pnl():
    pairs = [
        (_make_signal(size=10.0), _make_selection("t1")),
        (_make_signal(size=20.0), _make_selection("t2")),
    ]
    result = run_backtest(
        pairs,
        prices={"t1": 0.5, "t2": 0.5},
        resolution_prices={"t1": 1.0, "t2": 0.0},
    )
    assert result.total_spent == 30.0
    assert result.win_rate == 0.5  # 1 win, 1 loss


def test_backtest_empty():
    result = run_backtest([], prices={})
    assert result.trades == []
    assert result.total_pnl == 0.0
    assert result.win_rate == 0.0
