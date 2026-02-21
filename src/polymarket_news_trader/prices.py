from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class PricePoint:
    t: int
    p: float


def get_price_history(
    host: str,
    *,
    token_id: str,
    start_ts: int,
    end_ts: int,
    fidelity_minutes: int = 1,
) -> list[PricePoint]:
    url = host.rstrip("/") + "/prices-history"
    params = {
        "market": str(token_id),
        "startTs": int(start_ts),
        "endTs": int(end_ts),
        "fidelity": int(fidelity_minutes),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    raw = resp.json() or {}
    history = raw.get("history") or []

    points: list[PricePoint] = []
    for pt in history:
        try:
            points.append(PricePoint(t=int(pt["t"]), p=float(pt["p"])))
        except Exception:
            continue

    points.sort(key=lambda x: x.t)
    return points


def last_price_at_or_before(points: list[PricePoint], ts: int) -> PricePoint | None:
    best: PricePoint | None = None
    for pt in points:
        if pt.t <= ts:
            best = pt
        else:
            break
    return best
