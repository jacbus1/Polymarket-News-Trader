from __future__ import annotations

from dataclasses import dataclass
import time

from .state import State


@dataclass(frozen=True)
class RiskConfig:
    bankroll_usdc: float
    min_trade_usdc: float
    max_trade_usdc: float
    default_trade_usdc: float
    max_daily_usdc: float | None
    max_trades_per_day: int | None
    max_days_to_resolution: int | None


def _today_key(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(now))


def load_risk_config(raw: dict | None) -> RiskConfig:
    raw = raw or {}
    bankroll = float(raw.get("bankroll_usdc") or 200)
    min_trade = float(raw.get("min_trade_usdc") or 10)
    max_trade = float(raw.get("max_trade_usdc") or 20)
    default_trade = float(raw.get("default_trade_usdc") or min_trade)
    max_daily = raw.get("max_daily_usdc")
    max_daily = float(max_daily) if max_daily is not None else None
    max_trades = raw.get("max_trades_per_day")
    max_trades = int(max_trades) if max_trades is not None else None
    max_days = raw.get("max_days_to_resolution")
    max_days = int(max_days) if max_days is not None else None
    return RiskConfig(
        bankroll_usdc=bankroll,
        min_trade_usdc=min_trade,
        max_trade_usdc=max_trade,
        default_trade_usdc=default_trade,
        max_daily_usdc=max_daily,
        max_trades_per_day=max_trades,
        max_days_to_resolution=max_days,
    )


def compute_trade_size_usdc(
    *,
    requested_size: float | None,
    risk: RiskConfig,
    state: State,
    now: float,
) -> float | None:
    size = float(requested_size) if requested_size is not None else risk.default_trade_usdc
    size = max(risk.min_trade_usdc, min(risk.max_trade_usdc, size))

    if risk.max_daily_usdc is not None:
        key = _today_key(now)
        spent = float(state.spent_by_day_usdc.get(key) or 0.0)
        if spent >= risk.max_daily_usdc:
            return None
        remaining = risk.max_daily_usdc - spent
        size = min(size, remaining)

    if risk.max_trades_per_day is not None:
        key = _today_key(now)
        trades = int(state.trades_by_day.get(key) or 0)
        if trades >= risk.max_trades_per_day:
            return None

    if size <= 0:
        return None

    return size


def record_spend(state: State, *, now: float, amount_usdc: float) -> None:
    key = _today_key(now)
    state.spent_by_day_usdc[key] = float(state.spent_by_day_usdc.get(key) or 0.0) + float(amount_usdc)


def record_trade(state: State, *, now: float) -> None:
    key = _today_key(now)
    state.trades_by_day[key] = int(state.trades_by_day.get(key) or 0) + 1
