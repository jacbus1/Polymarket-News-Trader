from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from datetime import datetime, timezone

import difflib
import requests


GAMMA_BASE = "https://gamma-api.polymarket.com"


@dataclass(frozen=True)
class MarketSelection:
    condition_id: str
    question: str
    outcome: str
    token_id: str
    end_ts: int | None


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def fetch_markets(active: bool = True, limit: int = 200) -> list[dict[str, Any]]:
    markets: list[dict[str, Any]] = []
    offset = 0

    while True:
        params = {
            "active": str(active).lower(),
            "closed": "false",
            "archived": "false",
            "limit": str(limit),
            "offset": str(offset),
        }
        resp = requests.get(f"{GAMMA_BASE}/markets", params=params, timeout=30)
        resp.raise_for_status()
        batch = resp.json() or []
        if not isinstance(batch, list):
            break
        markets.extend(batch)
        if len(batch) < limit:
            break
        offset += limit

    return markets


def _pick_token_id(market: dict[str, Any], outcome_label: str) -> str | None:
    outcomes = market.get("outcomes")
    token_ids = market.get("clobTokenIds")
    if not isinstance(outcomes, list) or not isinstance(token_ids, list):
        return None
    if len(outcomes) != len(token_ids):
        return None

    for o, t in zip(outcomes, token_ids):
        if str(o).strip().lower() == outcome_label.strip().lower():
            return str(t)
    return None


def _parse_iso_ts(value: str | None) -> int | None:
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        return None


def _extract_end_ts(market: dict[str, Any]) -> int | None:
    for key in ("endDate", "endTime", "closeTime", "resolutionDate", "resolutionTime", "tradingEndTime"):
        ts = _parse_iso_ts(str(market.get(key) or "")) if market.get(key) else None
        if ts is not None:
            return ts
    return None


def select_market(
    markets: list[dict[str, Any]],
    *,
    condition_id: str | None = None,
    question_contains: str | None = None,
    outcome: str,
) -> MarketSelection:
    if not outcome:
        raise ValueError("market.outcome is required")

    if condition_id:
        for m in markets:
            if str(m.get("conditionId")) == condition_id:
                token_id = _pick_token_id(m, outcome)
                if not token_id:
                    raise ValueError(f"Outcome {outcome!r} not found for conditionId={condition_id}")
                return MarketSelection(
                    condition_id=condition_id,
                    question=str(m.get("question") or ""),
                    outcome=outcome,
                    token_id=token_id,
                    end_ts=_extract_end_ts(m),
                )
        raise ValueError(f"conditionId not found: {condition_id}")

    if question_contains:
        needle = _normalize(question_contains)
        scored: list[tuple[float, dict[str, Any]]] = []
        for m in markets:
            q = str(m.get("question") or "")
            if not q:
                continue
            score = difflib.SequenceMatcher(a=_normalize(q), b=needle).ratio()
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1] if scored else None
        if not best:
            raise ValueError(f"No markets available for question_contains={question_contains!r}")

        cid = str(best.get("conditionId"))
        token_id = _pick_token_id(best, outcome)
        if not token_id:
            raise ValueError(f"Outcome {outcome!r} not found for selected market cid={cid}")

        return MarketSelection(
            condition_id=cid,
            question=str(best.get("question") or ""),
            outcome=outcome,
            token_id=token_id,
            end_ts=_extract_end_ts(best),
        )

    raise ValueError("market.condition_id or market.question_contains is required")
