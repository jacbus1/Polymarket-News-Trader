from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import websockets


DEFAULT_MARKET_WSS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


async def market_stream(asset_ids: list[str], *, url: str = DEFAULT_MARKET_WSS) -> AsyncIterator[dict]:
    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "market",
                    "assets_ids": asset_ids,
                    "custom_feature_enabled": False,
                }
            )
        )
        async for msg in ws:
            yield json.loads(msg)


def print_market_stream(asset_ids: list[str], *, max_messages: int | None = None, url: str = DEFAULT_MARKET_WSS) -> None:
    async def _run() -> None:
        count = 0
        async for event in market_stream(asset_ids, url=url):
            print(json.dumps(event, ensure_ascii=False))
            count += 1
            if max_messages is not None and count >= max_messages:
                break

    asyncio.run(_run())
