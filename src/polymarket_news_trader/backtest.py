from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

from .gamma import fetch_markets, select_market
from .gdelt_ingest import fetch_gdelt_all
from .news import NewsItem, fetch_all
from .prices import get_price_history, last_price_at_or_before
from .strategy import match_rules


@dataclass(frozen=True)
class BacktestParams:
    lookahead_minutes: int
    min_entry_price: float
    max_entry_price: float


def run_backtest(
    *,
    host: str,
    feeds: list[dict],
    rules: list[dict],
    gdelt_queries: list[dict],
    out_csv: str | Path,
    lookahead_minutes: int = 30,
    min_entry_price: float = 0.0,
    max_entry_price: float = 0.15,
    max_items: int | None = None,
    max_days_to_resolution: int | None = None,
) -> Path:
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    items = fetch_all(feeds)
    if gdelt_queries:
        items.extend(fetch_gdelt_all(gdelt_queries))

    if max_items is not None:
        items = items[: max_items]

    markets = fetch_markets(active=True)

    params = BacktestParams(
        lookahead_minutes=int(lookahead_minutes),
        min_entry_price=float(min_entry_price),
        max_entry_price=float(max_entry_price),
    )

    now = time.time()

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "published_ts",
                "published",
                "category",
                "source",
                "title",
                "link",
                "rule",
                "question",
                "condition_id",
                "token_id",
                "outcome",
                "p0",
                "p30",
                "delta",
                "return_pct",
                "eligible_low_prob",
            ],
        )
        w.writeheader()

        for item in items:
            if item.published_ts is None:
                continue

            matched = match_rules(
                item=item,
                rules=rules,
                now=now,
                last_rule_fired_at={},
            )

            for rule in matched:
                name = str(rule.get("name") or "")
                market = rule.get("market") or {}

                try:
                    sel = select_market(
                        markets,
                        condition_id=market.get("condition_id"),
                        question_contains=market.get("question_contains"),
                        outcome=str(market.get("outcome") or ""),
                    )
                except Exception:
                    continue

                if max_days_to_resolution is not None:
                    if sel.end_ts is None:
                        continue
                    horizon = int(item.published_ts + max_days_to_resolution * 86400)
                    if sel.end_ts > horizon:
                        continue

                start_ts = int(item.published_ts)
                end_ts = int(item.published_ts + params.lookahead_minutes * 60)

                history = get_price_history(
                    host,
                    token_id=sel.token_id,
                    start_ts=start_ts - 10 * 60,
                    end_ts=end_ts,
                    fidelity_minutes=1,
                )

                p0_pt = last_price_at_or_before(history, start_ts)
                p30_pt = last_price_at_or_before(history, end_ts)
                if not p0_pt or not p30_pt:
                    continue

                p0 = float(p0_pt.p)
                p30 = float(p30_pt.p)
                delta = p30 - p0
                ret = (delta / p0 * 100.0) if p0 > 0 else 0.0

                eligible = (p0 >= params.min_entry_price) and (p0 <= params.max_entry_price)

                w.writerow(
                    {
                        "published_ts": item.published_ts,
                        "published": item.published,
                        "category": item.category,
                        "source": item.source,
                        "title": item.title,
                        "link": item.link,
                        "rule": name,
                        "question": sel.question,
                        "condition_id": sel.condition_id,
                        "token_id": sel.token_id,
                        "outcome": sel.outcome,
                        "p0": f"{p0:.6f}",
                        "p30": f"{p30:.6f}",
                        "delta": f"{delta:.6f}",
                        "return_pct": f"{ret:.3f}",
                        "eligible_low_prob": str(bool(eligible)).lower(),
                    }
                )

    return out_csv
