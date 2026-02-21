from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import os

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class BotConfig:
    host: str
    chain_id: int
    private_key: str | None
    funder_address: str | None
    signature_type: int
    dry_run: bool

    feeds: list[dict[str, str]]
    rules: list[dict[str, Any]]
    gdelt_queries: list[dict[str, Any]]
    risk: dict[str, Any]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _normalize_feeds(raw: Any) -> list[dict[str, str]]:
    feeds: list[dict[str, str]] = []

    if raw is None:
        return feeds

    # Backwards compatible: list[str]
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, str):
                feeds.append({"url": entry, "category": "general"})
            elif isinstance(entry, dict) and entry.get("url"):
                feeds.append({"url": str(entry["url"]), "category": str(entry.get("category") or "general")})
        return feeds

    # New: dict[category] -> list[url]
    if isinstance(raw, dict):
        for category, urls in raw.items():
            if not isinstance(urls, list):
                continue
            for url in urls:
                if isinstance(url, str) and url:
                    feeds.append({"url": url, "category": str(category)})
        return feeds

    return feeds


def _normalize_gdelt(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def load_config(rules_path: str | Path) -> BotConfig:
    load_dotenv(override=False)

    rules_path = Path(rules_path)
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}

    host = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
    chain_id = int(os.getenv("POLYMARKET_CHAIN_ID", "137"))
    private_key = os.getenv("POLYMARKET_PRIVATE_KEY") or None
    funder_address = os.getenv("POLYMARKET_FUNDER_ADDRESS") or None
    signature_type = int(os.getenv("POLYMARKET_SIGNATURE_TYPE", "1"))

    dry_run_env = _as_bool(os.getenv("DRY_RUN"), default=True)

    feeds = _normalize_feeds(data.get("feeds"))
    rules = list(data.get("rules") or [])
    gdelt_queries = _normalize_gdelt(data.get("gdelt"))
    risk = dict(data.get("risk") or {})

    return BotConfig(
        host=host,
        chain_id=chain_id,
        private_key=private_key,
        funder_address=funder_address,
        signature_type=signature_type,
        dry_run=dry_run_env,
        feeds=feeds,
        rules=rules,
        gdelt_queries=gdelt_queries,
        risk=risk,
    )
