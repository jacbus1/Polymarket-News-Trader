from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from .backtest import run_backtest
from .clob_client import (
    TradingEnv,
    make_readonly_client,
    make_trading_client,
    place_limit_order_shares,
    place_market_order_usdc,
)
from .config import load_config
from .gamma import fetch_markets, select_market
from .gdelt_ingest import fetch_gdelt_all
from .news import fetch_all
from .risk import compute_trade_size_usdc, load_risk_config, record_spend, record_trade
from .state import load_state, save_state
from .strategy import build_action, match_rules
from .wss import print_market_stream


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="rules.yaml")
    ap.add_argument("--state", default="data/state.json")
    ap.add_argument("--poll-seconds", type=int, default=30)
    ap.add_argument("--market-refresh-seconds", type=int, default=15 * 60)
    ap.add_argument("--log-level", default="INFO")
    ap.add_argument("--live", action="store_true", help="Enable live trading (overrides DRY_RUN=1)")

    ap.add_argument(
        "--wss-assets",
        nargs="+",
        help="If set, run a CLOB market websocket stream for these token IDs and exit.",
    )
    ap.add_argument("--wss-max-messages", type=int, default=50)

    ap.add_argument(
        "--backtest",
        action="store_true",
        help="Run a simple backtest: for matched news, compute price change after a window and write CSV.",
    )
    ap.add_argument("--backtest-window-minutes", type=int, default=30)
    ap.add_argument("--backtest-max-entry-price", type=float, default=0.15)
    ap.add_argument("--backtest-min-entry-price", type=float, default=0.0)
    ap.add_argument("--backtest-out", default="data/backtest.csv")
    ap.add_argument("--backtest-max-items", type=int, default=500)

    args = ap.parse_args()

    if args.wss_assets:
        print_market_stream(list(args.wss_assets), max_messages=args.wss_max_messages)
        return

    _setup_logging(args.log_level)
    log = logging.getLogger("polymarket_news_trader")

    cfg = load_config(args.rules)
    risk_cfg = load_risk_config(cfg.risk)

    if args.backtest:
        out = run_backtest(
            host=cfg.host,
            feeds=cfg.feeds,
            rules=cfg.rules,
            gdelt_queries=cfg.gdelt_queries,
            out_csv=args.backtest_out,
            lookahead_minutes=args.backtest_window_minutes,
            min_entry_price=args.backtest_min_entry_price,
            max_entry_price=args.backtest_max_entry_price,
            max_items=args.backtest_max_items,
            max_days_to_resolution=risk_cfg.max_days_to_resolution,
        )
        log.info("Backtest wrote %s", out)
        return

    dry_run = (not args.live) and cfg.dry_run

    if not cfg.feeds and not cfg.gdelt_queries:
        raise SystemExit("No feeds configured (rules.yaml -> feeds or gdelt)")

    state_path = Path(args.state)
    state = load_state(state_path)

    readonly = make_readonly_client(cfg.host)

    trading_client = None
    if not dry_run:
        if not cfg.private_key or not cfg.funder_address:
            raise SystemExit("Missing POLYMARKET_PRIVATE_KEY or POLYMARKET_FUNDER_ADDRESS for live trading")
        trading_client = make_trading_client(
            TradingEnv(
                host=cfg.host,
                chain_id=cfg.chain_id,
                private_key=cfg.private_key,
                funder_address=cfg.funder_address,
                signature_type=cfg.signature_type,
            )
        )

    log.info("Starting (dry_run=%s) polling %d feeds", dry_run, len(cfg.feeds))

    markets_cache = []
    next_market_refresh = 0.0

    while True:
        now = time.time()
        if now >= next_market_refresh:
            try:
                markets_cache = fetch_markets(active=True)
                log.info("Fetched %d active markets from Gamma", len(markets_cache))
            except Exception as e:
                log.warning("Gamma fetch failed: %s", e)
            next_market_refresh = now + float(args.market_refresh_seconds)

        items: list = []
        if cfg.feeds:
            try:
                items.extend(fetch_all(cfg.feeds))
            except Exception as e:
                log.warning("Feed fetch failed: %s", e)

        if cfg.gdelt_queries:
            try:
                items.extend(fetch_gdelt_all(cfg.gdelt_queries))
            except Exception as e:
                log.warning("GDELT fetch failed: %s", e)

        new_items = [it for it in items if it.item_id not in state.seen_ids]
        if new_items:
            log.info("Fetched %d items (%d new)", len(items), len(new_items))

        for item in new_items:
            state.seen_ids.add(item.item_id)

            matched = match_rules(
                item=item,
                rules=cfg.rules,
                now=now,
                last_rule_fired_at=state.last_rule_fired_at,
            )

            for rule in matched:
                name = str(rule.get("name") or "")
                market = rule.get("market") or {}
                order = rule.get("order") or {}

                try:
                    sel = select_market(
                        markets_cache,
                        condition_id=market.get("condition_id"),
                        question_contains=market.get("question_contains"),
                        outcome=str(market.get("outcome") or ""),
                    )
                except Exception as e:
                    log.warning("Rule %r market selection failed: %s", name, e)
                    continue

                action = build_action(name, sel.token_id, sel.outcome, order)

                log.info(
                    "MATCH rule=%r outcome=%s token_id=%s question=%r title=%r",
                    action.rule_name,
                    action.outcome,
                    action.token_id,
                    sel.question,
                    item.title,
                )

                if risk_cfg.max_days_to_resolution is not None:
                    if sel.end_ts is None:
                        log.info("Skip: missing end date for market %s", sel.condition_id)
                        continue
                    max_horizon = now + risk_cfg.max_days_to_resolution * 86400
                    if sel.end_ts > max_horizon:
                        log.info(
                            "Skip: market resolves in %.1f days (limit %d)",
                            (sel.end_ts - now) / 86400.0,
                            risk_cfg.max_days_to_resolution,
                        )
                        continue

                if dry_run:
                    log.info("DRY_RUN: would place %s order %s", action.kind, action)
                    state.last_rule_fired_at[action.rule_name] = now
                    continue

                assert trading_client is not None

                try:
                    if action.kind == "market":
                        size_usdc = compute_trade_size_usdc(
                            requested_size=action.size_usdc,
                            risk=risk_cfg,
                            state=state,
                            now=now,
                        )
                        if size_usdc is None:
                            log.info("Skip: daily cap reached or size <= 0")
                            continue
                        if action.max_price is not None:
                            mid = readonly.get_midpoint(action.token_id)
                            if mid is not None and float(mid) > float(action.max_price):
                                log.info("Skip: midpoint %.4f > max_price %.4f", float(mid), float(action.max_price))
                                continue
                        resp = place_market_order_usdc(
                            trading_client,
                            token_id=action.token_id,
                            side=action.side,
                            amount_usdc=float(size_usdc),
                        )
                        record_spend(state, now=now, amount_usdc=float(size_usdc))
                        record_trade(state, now=now)
                    else:
                        if action.price is None or action.size_shares is None:
                            raise ValueError("limit order requires order.price and order.size_shares")
                        resp = place_limit_order_shares(
                            trading_client,
                            token_id=action.token_id,
                            side=action.side,
                            price=float(action.price),
                            size=float(action.size_shares),
                        )

                    log.info("ORDER OK: %s", resp)
                    state.last_rule_fired_at[action.rule_name] = now
                except Exception as e:
                    log.warning("ORDER FAILED (%s): %s", action.rule_name, e)

        save_state(state_path, state)
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    cli()
