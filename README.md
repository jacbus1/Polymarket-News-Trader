# Polymarket-News-Trader

`polymarket-news-trader` is a Python bot that monitors real-time news and maps events to Polymarket markets. It can run in analysis mode (dry-run/backtest) or place live orders through the Polymarket CLOB API.

## Features

- **RSS/Atom ingestion** – poll any number of news feeds via `feedparser`
- **GDELT Doc API ingestion** – free global news search, no API key required
- **Deduplication** – seen event IDs are persisted to disk so no headline is processed twice across restarts
- **Rule matching** – keyword-based rules in `rules.yaml` map headlines to market/outcome/side/size decisions
- **Market selection** – queries the Polymarket Gamma API and picks the best-matching market by word overlap
- **Backtesting** – simulates P&L for matched signals without touching any external service
- **Order execution** – places market or limit orders via the Polymarket CLOB API; real orders are only sent when `--live` is explicitly passed

## Installation

```bash
pip install -e .
```

Or install dependencies directly:

```bash
pip install feedparser requests PyYAML
```

## Quick Start

**Dry-run (default)** – fetch news, match rules, log what would be traded:

```bash
polymarket-news-trader
```

**Backtest mode** – simulate P&L without placing orders:

```bash
polymarket-news-trader --backtest
```

**Add GDELT queries** alongside RSS feeds:

```bash
polymarket-news-trader --gdelt "presidential election" "interest rate hike"
```

**Live trading** – places real orders (requires a Polymarket CLOB API key):

```bash
polymarket-news-trader --live --api-key YOUR_KEY
```

**Custom feeds and rules file:**

```bash
polymarket-news-trader \
  --feeds https://feeds.bbci.co.uk/news/rss.xml https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml \
  --rules /path/to/my-rules.yaml \
  --interval 30
```

## Configuration – `rules.yaml`

Each rule maps a set of keywords to a Polymarket market and trade parameters:

```yaml
rules:
  - name: "fed-rate-hike"
    keywords:
      - "rate hike"
      - "Federal Reserve raises"
    market_tag: "Fed interest rate hike"   # matched against market questions
    outcome: "YES"                         # YES or NO token
    side: "BUY"                            # BUY or SELL
    size: 15.0                             # USDC amount
    order_type: "limit"                    # market or limit
    limit_price: 0.60                      # only for limit orders (0–1)
```

See `rules.yaml` for a complete set of example rules.

## Project Structure

```
polymarket_news_trader/
├── ingest/
│   ├── rss.py        # RSS/Atom feed ingestion → NewsItem
│   └── gdelt.py      # GDELT Doc API ingestion
├── store/
│   └── dedup.py      # JSON-backed seen-ID deduplication store
├── rules/
│   └── matcher.py    # YAML rule loader + keyword matcher
├── markets/
│   └── selector.py   # Polymarket Gamma API client + market selector
├── backtest/
│   └── engine.py     # P&L simulator
├── execution/
│   └── trader.py     # CLOB API order submitter (dry-run + live)
└── cli.py            # CLI entry point
rules.yaml            # Sample trading rules
```

## Running Tests

```bash
pytest tests/ -v
```

## Security Notes

- The API key is passed at runtime (`--api-key`) and is never stored in source code.
- Live trading requires the explicit `--live` flag; all other modes are read-only.
- Seen-event state is stored in `~/.polymarket_news_trader/seen.json`.
