from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json
import time


@dataclass
class State:
    seen_ids: set[str]
    last_rule_fired_at: dict[str, float]
    spent_by_day_usdc: dict[str, float]
    trades_by_day: dict[str, int]


def load_state(path: str | Path) -> State:
    path = Path(path)
    if not path.exists():
        return State(seen_ids=set(), last_rule_fired_at={}, spent_by_day_usdc={}, trades_by_day={})

    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return State(
        seen_ids=set(raw.get("seen_ids") or []),
        last_rule_fired_at=dict(raw.get("last_rule_fired_at") or {}),
        spent_by_day_usdc=dict(raw.get("spent_by_day_usdc") or {}),
        trades_by_day=dict(raw.get("trades_by_day") or {}),
    )


def save_state(path: str | Path, state: State) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seen_ids": sorted(state.seen_ids),
        "last_rule_fired_at": state.last_rule_fired_at,
        "spent_by_day_usdc": state.spent_by_day_usdc,
        "trades_by_day": state.trades_by_day,
        "saved_at": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
