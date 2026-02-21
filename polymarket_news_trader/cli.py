"""Command-line entry point for polymarket-news-trader."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import List, Optional

from .ingest.rss import fetch_rss, NewsItem
from .ingest.gdelt import fetch_gdelt
from .store.dedup import SeenStore
from .rules.matcher import load_rules, match
from .markets.selector import fetch_markets, select_market
from .backtest.engine import run_backtest
from .execution.trader import Trader

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_FEEDS = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
]


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="polymarket-news-trader",
        description="Monitor news feeds and trade Polymarket markets based on rules.",
    )
    parser.add_argument(
        "--rules", default=None, metavar="PATH",
        help="Path to rules YAML file (default: rules.yaml in project root).",
    )
    parser.add_argument(
        "--feeds", nargs="+", default=DEFAULT_FEEDS, metavar="URL",
        help="One or more RSS/Atom feed URLs to monitor.",
    )
    parser.add_argument(
        "--gdelt", nargs="*", default=None, metavar="QUERY",
        help="One or more GDELT search queries (e.g. 'election president').",
    )
    parser.add_argument(
        "--store", default=None, metavar="PATH",
        help="Path to the seen-events JSON store.",
    )
    parser.add_argument(
        "--backtest", action="store_true",
        help="Run in backtest mode (simulates trades, no orders placed).",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Enable live trading (real orders will be placed!).",
    )
    parser.add_argument(
        "--api-key", default="", metavar="KEY",
        help="Polymarket CLOB API key (required for live mode).",
    )
    parser.add_argument(
        "--interval", type=int, default=60, metavar="SECONDS",
        help="Poll interval in seconds (default: 60). Use 0 for a single run.",
    )
    return parser.parse_args(argv)


def run_once(args: argparse.Namespace, store: SeenStore, trader: Trader) -> None:
    """Fetch news, deduplicate, match rules, and act on signals."""
    rules = load_rules(args.rules)
    if not rules:
        logger.warning("No rules loaded – check your rules.yaml file.")
        return

    # --- Ingest ---
    items: List[NewsItem] = []
    for feed_url in args.feeds:
        try:
            fetched = fetch_rss(feed_url)
            logger.info("Fetched %d items from %s", len(fetched), feed_url)
            items.extend(fetched)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", feed_url, exc)

    if args.gdelt:
        for query in args.gdelt:
            gdelt_items = fetch_gdelt(query)
            logger.info("GDELT: %d items for query '%s'", len(gdelt_items), query)
            items.extend(gdelt_items)

    # --- Deduplicate ---
    new_items = store.filter_new(items)
    logger.info("%d new items after deduplication", len(new_items))
    if not new_items:
        return

    # --- Match rules ---
    signals = match(new_items, rules)
    logger.info("%d signal(s) matched", len(signals))
    if not signals:
        return

    # --- Fetch markets ---
    markets = fetch_markets()

    # --- Process signals ---
    if args.backtest:
        # In backtest mode: pair each signal with its market and run the engine.
        pairs = []
        for sig in signals:
            sel = select_market(sig.rule.market_tag, sig.rule.outcome, markets)
            if sel:
                pairs.append((sig, sel))
        if pairs:
            result = run_backtest(pairs, prices={})
            logger.info(
                "Backtest: %d trade(s) | total spent=%.2f | win_rate=%.1f%%",
                len(result.trades), result.total_spent, result.win_rate * 100,
            )
            for trade in result.trades:
                logger.info("  [%s] %s outcome=%s size=%.2f fill=%.3f pnl=%.2f",
                            trade.rule_name, trade.question, trade.outcome,
                            trade.size, trade.fill_price, trade.pnl)
        return

    # Live / dry-run mode
    for sig in signals:
        sel = select_market(sig.rule.market_tag, sig.rule.outcome, markets)
        if sel is None:
            logger.warning("No market found for rule '%s' (tag='%s')", sig.rule.name, sig.rule.market_tag)
            continue
        result = trader.submit(sig, sel)
        if result.dry_run:
            logger.info("[DRY-RUN] Rule '%s' matched '%s'", sig.rule.name, sig.item.title)
        elif result.success:
            logger.info("Order placed: id=%s rule='%s'", result.order_id, sig.rule.name)
        else:
            logger.error("Order failed: rule='%s' msg=%s", sig.rule.name, result.message)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    store_kwargs = {"path": args.store} if args.store else {}
    store = SeenStore(**store_kwargs)
    trader = Trader(api_key=args.api_key, live_mode=args.live)

    if args.interval == 0:
        run_once(args, store, trader)
        return

    while True:
        try:
            run_once(args, store, trader)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            sys.exit(0)
        except Exception as exc:
            logger.error("Unhandled error: %s", exc, exc_info=True)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
