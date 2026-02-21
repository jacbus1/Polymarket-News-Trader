"""Tests for the rule-matching engine."""
import tempfile
import os

import pytest
import yaml

from polymarket_news_trader.ingest.rss import NewsItem
from polymarket_news_trader.rules.matcher import load_rules, match, Rule, Signal

SAMPLE_RULES_YAML = """
rules:
  - name: "election-buy"
    keywords: ["election", "president", "vote"]
    market_tag: "US presidential election"
    outcome: "YES"
    side: "BUY"
    size: 20.0
    order_type: "market"
  - name: "rate-hike-limit"
    keywords: ["rate hike", "federal reserve", "interest rate"]
    market_tag: "Fed rate hike"
    outcome: "YES"
    side: "BUY"
    size: 10.0
    order_type: "limit"
    limit_price: 0.65
"""


def _write_rules(tmp_path) -> str:
    p = tmp_path / "rules.yaml"
    p.write_text(SAMPLE_RULES_YAML)
    return str(p)


def _make_item(title: str, summary: str = "") -> NewsItem:
    return NewsItem(id=title, title=title, summary=summary, url="https://example.com")


def test_load_rules(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    assert len(rules) == 2
    assert rules[0].name == "election-buy"
    assert rules[1].limit_price == 0.65


def test_match_keyword_in_title(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    items = [_make_item("New president elected in landslide victory")]
    signals = match(items, rules)
    assert len(signals) == 1
    assert signals[0].rule.name == "election-buy"


def test_match_keyword_in_summary(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    items = [_make_item("Central Bank Update", "Federal Reserve signals interest rate change")]
    signals = match(items, rules)
    assert len(signals) == 1
    assert signals[0].rule.name == "rate-hike-limit"


def test_no_match_returns_empty(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    items = [_make_item("Weather forecast: sunny skies ahead")]
    signals = match(items, rules)
    assert signals == []


def test_multiple_rules_can_match(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    # Item mentioning both election and rate hike
    items = [_make_item("Election results and interest rate decision announced")]
    signals = match(items, rules)
    assert len(signals) == 2


def test_case_insensitive_match(tmp_path):
    path = _write_rules(tmp_path)
    rules = load_rules(path)
    items = [_make_item("ELECTION RESULTS: President wins")]
    signals = match(items, rules)
    assert len(signals) >= 1
