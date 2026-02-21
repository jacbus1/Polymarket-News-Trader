from __future__ import annotations

from dataclasses import dataclass

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL


@dataclass(frozen=True)
class TradingEnv:
    host: str
    chain_id: int
    private_key: str
    funder_address: str
    signature_type: int


def make_readonly_client(host: str) -> ClobClient:
    return ClobClient(host)


def make_trading_client(env: TradingEnv) -> ClobClient:
    client = ClobClient(
        env.host,
        key=env.private_key,
        chain_id=env.chain_id,
        signature_type=env.signature_type,
        funder=env.funder_address,
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    return client


def place_market_order_usdc(
    client: ClobClient,
    *,
    token_id: str,
    side: str,
    amount_usdc: float,
) -> dict:
    side_const = BUY if side.lower() == "buy" else SELL
    mo = MarketOrderArgs(token_id=token_id, amount=float(amount_usdc), side=side_const, order_type=OrderType.FOK)
    signed = client.create_market_order(mo)
    return client.post_order(signed, OrderType.FOK)


def place_limit_order_shares(
    client: ClobClient,
    *,
    token_id: str,
    side: str,
    price: float,
    size: float,
) -> dict:
    side_const = BUY if side.lower() == "buy" else SELL
    order = OrderArgs(token_id=token_id, price=float(price), size=float(size), side=side_const)
    signed = client.create_order(order)
    return client.post_order(signed, OrderType.GTC)
