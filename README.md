# polymarket-news-trader

`polymarket-news-trader` is a Python bot that monitors real-time news and maps events to Polymarket markets.  
It can run in analysis mode (dry-run/backtest) or place live orders through the Polymarket CLOB API.

## Project Overview

This project is built for event-driven trading workflows:

- Ingest headlines from RSS/Atom feeds
- Optionally ingest global news via GDELT Doc API (free)
- Deduplicate and persist seen events locally
- Match text signals to trading rules in `rules.yaml`
- Select market/outcome pairs from Polymarket metadata
- Simulate performance in backtests
- Execute market or limit orders (only when live mode is enabled)

## Key Features

- Safe-by-default behavior with dry-run enabled unless `--live` is passed
- Rule-based strategy engine (`all/any/not`, synonyms, regex patterns, score gates)
- Risk controls (`bankroll`, per-trade caps, daily trade limits, time-to-resolution limits)
- Backtesting pipeline for headline-to-price-reaction analysis
- Optional WebSocket smoke test for market channel monitoring

## Repository Structure

- `src/polymarket_news_trader/main.py`: runtime loop and CLI entry flow
- `src/polymarket_news_trader/strategy.py`: signal matching and action builder
- `src/polymarket_news_trader/clob_client.py`: CLOB trading client wrapper
- `src/polymarket_news_trader/backtest.py`: backtest execution and CSV output
- `rules.example.yaml`: example strategy/risk configuration
- `feeds.candidates.yaml`: curated feed starter list

## Quick Start

### 1) Install

```bash
cd polymarket-news-trader
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Configure rules

```bash
cp rules.example.yaml rules.yaml
```

Optional: start from curated feeds:

```bash
cp feeds.candidates.yaml rules.yaml
# then merge in the `rules:` section from rules.example.yaml
```

### 3) (Optional) create `.env` for live trading

You only need this for real order placement:

```bash
cat > .env << 'EOF'
POLYMARKET_HOST=https://clob.polymarket.com
POLYMARKET_CHAIN_ID=137
POLYMARKET_PRIVATE_KEY=
POLYMARKET_FUNDER_ADDRESS=
POLYMARKET_SIGNATURE_TYPE=1
DRY_RUN=1
EOF
```

## Required Files Before Running

To run this project successfully, make sure these files exist:

- Required: `rules.yaml`
  - Create it with: `cp rules.example.yaml rules.yaml`
- Optional (recommended): `.env`
  - Needed for live trading credentials and runtime options
  - If missing, the app can still run in dry-run/backtest mode with defaults
- Not required: `.DS_Store`
  - This is a macOS metadata file, not a project config file
  - Do not create it manually

## Usage

### Backtest

Writes `data/backtest.csv` with `p0`, `p30`, and return.

```bash
python -m polymarket_news_trader --rules rules.yaml --backtest \
  --backtest-window-minutes 30 \
  --backtest-max-entry-price 0.15 \
  --backtest-out data/backtest.csv
```

### Dry-run (recommended)

```bash
python -m polymarket_news_trader --rules rules.yaml
```

### Live trading

```bash
python -m polymarket_news_trader --rules rules.yaml --live
```

### WebSocket smoke test

```bash
python -m polymarket_news_trader --wss-assets <TOKEN_ID> --wss-max-messages 50
```

## Safety Notes

- Keep private keys out of source control.
- Always validate rules in dry-run before enabling `--live`.
- Keep `DRY_RUN=1` as default and only switch to live intentionally.
