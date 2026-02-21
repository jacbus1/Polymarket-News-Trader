"""Order execution module.

Only places real orders when live_mode=True.  In dry-run / backtest mode
every call logs the intended action without touching any external API.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

from ..rules.matcher import Signal
from ..markets.selector import MarketSelection

logger = logging.getLogger(__name__)

POLYMARKET_CLOB_API = "https://clob.polymarket.com"


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    dry_run: bool = False


class Trader:
    """Manages order submission to the Polymarket CLOB API."""

    def __init__(self, api_key: str = "", live_mode: bool = False) -> None:
        self.api_key = api_key
        self.live_mode = live_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def submit(self, signal: Signal, selection: MarketSelection) -> OrderResult:
        """Submit a market or limit order for *signal* on *selection*.

        When live_mode is False, logs the intended action and returns a
        simulated success result without touching any external service.
        """
        rule = signal.rule
        if not self.live_mode:
            logger.info(
                "[DRY-RUN] Would place %s %s order: %s outcome=%s size=%.2f%s",
                rule.order_type.upper(),
                rule.side,
                selection.question,
                selection.outcome,
                rule.size,
                f" @ {rule.limit_price}" if rule.limit_price is not None else "",
            )
            return OrderResult(success=True, message="dry-run", dry_run=True)

        if rule.order_type == "market":
            return self._place_market_order(rule, selection)
        return self._place_limit_order(rule, selection)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _place_market_order(self, rule, selection: MarketSelection) -> OrderResult:
        payload = {
            "token_id": selection.token_id,
            "side": rule.side,
            "amount": rule.size,
            "type": "MARKET",
        }
        try:
            resp = requests.post(
                f"{POLYMARKET_CLOB_API}/order",
                json=payload,
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            order_id = data.get("orderID") or data.get("order_id", "")
            return OrderResult(success=True, order_id=order_id)
        except requests.HTTPError as exc:
            return OrderResult(success=False, message=f"Market order failed: {exc}")
        except Exception as exc:
            return OrderResult(success=False, message=f"Market order failed: {exc}")

    def _place_limit_order(self, rule, selection: MarketSelection) -> OrderResult:
        price = rule.limit_price if rule.limit_price is not None else 0.5
        payload = {
            "token_id": selection.token_id,
            "side": rule.side,
            "amount": rule.size,
            "type": "LIMIT",
            "price": price,
        }
        try:
            resp = requests.post(
                f"{POLYMARKET_CLOB_API}/order",
                json=payload,
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            order_id = data.get("orderID") or data.get("order_id", "")
            return OrderResult(success=True, order_id=order_id)
        except requests.HTTPError as exc:
            return OrderResult(success=False, message=f"Limit order failed: {exc}")
        except Exception as exc:
            return OrderResult(success=False, message=f"Limit order failed: {exc}")
