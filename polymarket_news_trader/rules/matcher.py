"""Rule-matching engine.

Loads trading rules from a YAML file and evaluates them against
the title/summary text of a NewsItem.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

from ..ingest.rss import NewsItem

_DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent / "rules.yaml"


@dataclass
class Rule:
    name: str
    keywords: List[str]
    market_tag: str
    outcome: str          # "YES" | "NO"
    side: str             # "BUY" | "SELL"
    size: float           # USDC amount
    order_type: str = "market"   # "market" | "limit"
    limit_price: Optional[float] = None  # 0–1, only for limit orders


@dataclass
class Signal:
    rule: Rule
    item: NewsItem


def load_rules(path: Optional[str] = None) -> List[Rule]:
    """Load rules from *path* (defaults to rules.yaml in project root)."""
    rules_path = Path(path) if path else _DEFAULT_RULES_PATH
    with open(rules_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    rules: List[Rule] = []
    for entry in raw.get("rules", []):
        rules.append(
            Rule(
                name=entry["name"],
                keywords=entry.get("keywords", []),
                market_tag=entry["market_tag"],
                outcome=entry.get("outcome", "YES").upper(),
                side=entry.get("side", "BUY").upper(),
                size=float(entry.get("size", 10.0)),
                order_type=entry.get("order_type", "market").lower(),
                limit_price=entry.get("limit_price"),
            )
        )
    return rules


def _text_matches(text: str, keywords: List[str]) -> bool:
    """Return True if *any* keyword appears (case-insensitive) in *text*."""
    lower = text.lower()
    return any(re.search(re.escape(kw.lower()), lower) for kw in keywords)


def match(items: List[NewsItem], rules: List[Rule]) -> List[Signal]:
    """Match a list of NewsItems against a list of Rules.

    Returns a Signal for every (item, rule) combination that matches.
    """
    signals: List[Signal] = []
    for item in items:
        combined = f"{item.title} {item.summary}"
        for rule in rules:
            if _text_matches(combined, rule.keywords):
                signals.append(Signal(rule=rule, item=item))
    return signals
