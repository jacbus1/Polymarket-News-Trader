"""Simple backtesting engine.

Given a list of (Signal, MarketSelection) pairs and historical price data,
simulate P&L assuming the order fills at a given price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..rules.matcher import Signal
from ..markets.selector import MarketSelection


@dataclass
class BacktestTrade:
    rule_name: str
    question: str
    outcome: str
    side: str             # BUY | SELL
    size: float           # USDC
    fill_price: float     # 0–1
    pnl: float = 0.0      # Unrealised P&L at resolution_price
    resolved: bool = False
    resolution_price: float = 0.0  # 1.0 = YES won, 0.0 = NO won


@dataclass
class BacktestResult:
    trades: List[BacktestTrade] = field(default_factory=list)

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def total_spent(self) -> float:
        return sum(t.size for t in self.trades)

    @property
    def win_rate(self) -> float:
        resolved = [t for t in self.trades if t.resolved]
        if not resolved:
            return 0.0
        winners = [t for t in resolved if t.pnl > 0]
        return len(winners) / len(resolved)


def run_backtest(
    signal_market_pairs: List[Tuple[Signal, MarketSelection]],
    prices: Dict[str, float],
    resolution_prices: Optional[Dict[str, float]] = None,
) -> BacktestResult:
    """Simulate a batch of trades.

    Parameters
    ----------
    signal_market_pairs:
        List of (Signal, MarketSelection) tuples to simulate.
    prices:
        Mapping of token_id -> current fill price (0–1).
        Used as the assumed fill price for each trade.
    resolution_prices:
        Optional mapping of token_id -> resolution price (0 or 1).
        If provided, P&L is calculated for each resolved trade.

    Returns a BacktestResult containing per-trade details and aggregate stats.
    """
    result = BacktestResult()
    for signal, selection in signal_market_pairs:
        rule = signal.rule
        token_id = selection.token_id
        fill_price = prices.get(token_id, 0.5)

        # Shares bought = size / fill_price  (for BUY on YES token)
        # P&L at resolution = shares * (resolution_price - fill_price)
        shares = rule.size / fill_price if fill_price > 0 else 0.0

        trade = BacktestTrade(
            rule_name=rule.name,
            question=selection.question,
            outcome=selection.outcome,
            side=rule.side,
            size=rule.size,
            fill_price=fill_price,
        )

        if resolution_prices and token_id in resolution_prices:
            res_price = resolution_prices[token_id]
            if rule.side == "BUY":
                trade.pnl = shares * (res_price - fill_price)
            else:
                trade.pnl = shares * (fill_price - res_price)
            trade.resolution_price = res_price
            trade.resolved = True

        result.trades.append(trade)

    return result
