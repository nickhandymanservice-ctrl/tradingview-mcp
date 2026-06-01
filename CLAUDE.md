# CLAUDE.md

Guidance for AI coding assistants working in this repository.

## Project Overview

`tradingview-mcp-server` is a Python **MCP (Model Context Protocol) server** that exposes an
"AI Trading Intelligence" toolkit to MCP clients (Claude Desktop, Codex, Cursor, etc.). It
provides live market data and analysis with **no API keys required** by calling public
endpoints directly:

- **TradingView** (via `tradingview-ta` and `tradingview-screener`) — technical analysis,
  multi-exchange screeners, Bollinger ratings, candle/volume patterns.
- **Yahoo Finance Chart API** (raw HTTP, no `yfinance` library) — real-time quotes, market
  snapshots, extended-hours prices, options chains, and historical OHLC for backtesting.
- **Reddit + RSS feeds** — community sentiment and financial news.
- A **pure-Python backtesting engine** (6 strategies, walk-forward, Sharpe/Calmar/etc.).

It supports crypto exchanges (KuCoin, Binance, Bybit, MEXC, OKX, Bitget, Coinbase, Gate.io,
Huobi, Bitfinex) and stock markets (NASDAQ, NYSE, AMEX/NYSE Arca, BIST/Turkey, EGX/Egypt,
Bursa Malaysia, HKEX, SSE/SZSE China, TWSE/TPEX Taiwan, ASX).

Published to PyPI as `tradingview-mcp-server`; the console entry point is `tradingview-mcp`.

## Tech Stack

- **Python** `>=3.10` (Dockerfile uses 3.11; README recommends pinning `uvx --python 3.13`
  on Windows because `pandas`/native wheels can be missing on bleeding-edge Python).
- **MCP framework**: `mcp[cli]` (`FastMCP` from `mcp.server.fastmcp`).
- **Runtime deps** (from `pyproject.toml`): `mcp[cli]>=1.12.0`, `requests>=2.32`,
  `feedparser>=6.0.12`, `tradingview-screener>=0.6.4`, `tradingview-ta>=3.3.0`.
  `numpy` is present only transitively (pulled by the tradingview libs); the project's own
  code does **not** import `pandas`/`numpy`/`yfinance` — backtesting math is hand-rolled.
- **Package manager / runner**: `uv` (with `uv.lock`). Build backend: `setuptools`.
- **Optional**: `python-dotenv` for `.env` loading (imported defensively; absence is fine).

## Repository Structure

```
src/tradingview_mcp/
  server.py                 # MCP server: FastMCP instance, all @mcp.tool() defs, main() entry point
  __init__.py
  coinlist/*.txt            # Symbol universes per exchange (binance.txt, nasdaq.txt, egx.txt, ...) — package data
  core/
    types.py
    portfolio.py
    data/                   # EGX index/sector static data (egx_indices.py, egx_sectors.py)
    utils/validators.py     # Timeframe/exchange sanitizers + symbol normalization (TradingView & Yahoo)
    services/               # ALL business logic lives here (server.py is routing only)
      screener_service.py        # trending/bollinger/coin analysis, candle patterns, multi-timeframe
      scanner_service.py         # volume breakout / confirmation / smart-volume scans
      screener_provider.py       # low-level scanner.tradingview.com requests (e.g. ATR fallback)
      multi_agent_service.py     # 3-agent debate (Technical / Sentiment / Risk)
      egx_service.py             # Egyptian Exchange tools
      sentiment_service.py       # Reddit sentiment
      news_service.py            # RSS news
      yahoo_finance_service.py   # Yahoo quotes + market snapshot
      bitcoin_market_service.py  # BTC macro pulse
      extended_hours_service.py  # pre/post-market prices
      options_service.py         # options chain + unusual activity
      backtest_service.py        # pure-Python backtester (run_backtest, compare_strategies, walk_forward_backtest)
      indicators.py / indicators_calc.py  # RSI/MACD/Bollinger/EMA/Supertrend/Donchian math
      coinlist.py                # load_symbols(exchange) from coinlist/*.txt
      proxy_manager.py           # optional Webshare proxy (env-driven)
tests/unit/                 # pytest: validators, exchange aliases/fixes, ATR injection
openclaw/                   # trading.py CLI wrapper + SKILL.md for OpenClaw (Telegram/WhatsApp) integration
.codex-plugin/plugin.json   # Codex plugin metadata; references .codex-mcp.json
.codex-mcp.json             # Codex MCP server config (uvx --from tradingview-mcp-server tradingview-mcp)
Dockerfile                  # 2-stage build, runs streamable-http on :8000
docker-compose.yml          # maps host 8080 -> container 8000
.github/workflows/publish-image.yml  # builds & pushes multi-arch image to GHCR
README.md INSTALLATION.md EXAMPLES.md CONTRIBUTING.md CHANGELOG.md OPENCLAW.md SECURITY.md
```

**Architecture rule**: `server.py` is a thin routing layer only. Each `@mcp.tool()` handler
validates/sanitizes inputs (via `core/utils/validators.py`) and delegates to a
`core/services/*` function. Put all computation in services, never in `server.py`.

## Install & Run

### From source (development)
```bash
uv run tradingview-mcp                 # stdio transport (default) — for Claude Desktop
uv run tradingview-mcp streamable-http --host 127.0.0.1 --port 8000   # HTTP transport
```

### As an installed tool / via uvx (how MCP clients launch it)
```bash
uv tool install tradingview-mcp-server
uvx --from tradingview-mcp-server tradingview-mcp
# Windows / bleeding-edge Python: pin a version with prebuilt wheels
uvx --python 3.13 --from tradingview-mcp-server tradingview-mcp
```

### Claude Desktop config
```json
{
  "mcpServers": {
    "tradingview": {
      "command": "/path/to/uvx",
      "args": ["--from", "tradingview-mcp-server", "tradingview-mcp"]
    }
  }
}
```

### Docker (HTTP transport)
```bash
docker compose up --build          # exposes http://localhost:8080 (container :8000)
# or
docker build -t tradingview-mcp .
docker run -p 8000:8000 tradingview-mcp
```
The image runs `tradingview-mcp streamable-http --host 0.0.0.0 --port 8000` and has a
healthcheck hitting `http://localhost:8000/health`. Runs as non-root user `mcpuser`.

### Transport
`main()` (in `server.py`) takes a positional `transport` arg: `stdio` (default) or
`streamable-http`, plus `--host`/`--port` (also read from `HOST`/`PORT` env vars).

## Environment Variables

All optional — the server runs fully **without any env vars or API keys**. Configured in
`.env` (copy from `.env.example`; `.env` is gitignored). Read by
`core/services/proxy_manager.py`:

| Var | Purpose | Default |
|-----|---------|---------|
| `PROXY_ENABLED` | Master switch (`true`/`false`) | `true` |
| `PROXY_HOST` | Webshare proxy host | `p.webshare.io` |
| `PROXY_PORT` | Proxy port | `80` |
| `PROXY_USERNAME_PREFIX` | Webshare rotating username prefix | `""` |
| `PROXY_PASSWORD` | Webshare password | `""` |
| `PROXY_SESSION_MIN` / `PROXY_SESSION_MAX` | Sticky-session ID range | `1` / `250` |
| `HOST` / `PORT` | HTTP transport bind address/port | `127.0.0.1` / `8000` |
| `DEBUG_MCP` | If set, prints debug info to stderr on startup | unset |

Proxy is only active when `PROXY_ENABLED=true` **and** both `PROXY_USERNAME_PREFIX` and
`PROXY_PASSWORD` are set; otherwise services fall back to direct (no-proxy) requests and
degrade gracefully. The proxy helps with Yahoo Finance / Reddit rate limits.

**Never hardcode proxy credentials** — they come from env/`.env` only.

## Testing

```bash
uv run pytest                  # run all tests (pytest is a uv dev-dependency)
uv run pytest tests/unit/test_validators.py
```
Tests are unit-level and network-free (validators, exchange alias mapping, ATR injection
logic). There is no lint/format config committed.

## MCP Tools (32 tools + 1 resource)

All defined in `src/tradingview_mcp/server.py`. Default exchange is `KUCOIN`, default
timeframe `15m` (stocks default `1D`). Allowed timeframes: `5m, 15m, 1h, 4h, 1D, 1W, 1M`.

**Screeners**: `top_gainers`, `top_losers`, `bollinger_scan` (squeeze detection),
`rating_filter` (BB rating -3..+3).

**Asset analysis**: `coin_analysis` (full TA for one symbol), `multi_timeframe_analysis`
(Weekly→Daily→4H→1H→15m alignment), `multi_agent_analysis` (3-agent debate).

**Pattern/volume scanners**: `consecutive_candles_scan`, `advanced_candle_pattern`,
`volume_breakout_scanner`, `volume_confirmation_analysis`, `smart_volume_scanner`.

**EGX (Egypt)**: `egx_market_overview`, `egx_sector_scan`, `egx_sector_scanner`,
`egx_index_analysis`, `egx_stock_screener`, `egx_trade_plan`, `egx_fibonacci_retracement`.

**Sentiment & news**: `market_sentiment` (Reddit), `financial_news` (RSS),
`combined_analysis` (technical + sentiment + news confluence — "power tool").

**Backtesting** (Yahoo symbols, pure-Python engine): `backtest_strategy`,
`compare_strategies` (ranks all 6), `walk_forward_backtest_strategy` (overfitting check).
Strategies: `rsi`, `bollinger`, `macd`, `ema_cross`, `supertrend`, `donchian`.

**Yahoo Finance / market data**: `yahoo_price`, `market_snapshot`, `bitcoin_market_pulse`,
`stock_extended_hours`, `stock_options_chain`, `stock_options_unusual_activity`.

**Resource**: `exchanges://list` — lists available exchanges from `coinlist/*.txt`.

## Conventions

- **Routing vs logic**: keep `server.py` handlers thin; computation goes in `core/services/`.
- **Input sanitizing**: always run user-supplied `exchange`/`timeframe`/`symbol` through
  `sanitize_exchange`, `sanitize_timeframe`, `normalize_tradingview_symbol`,
  `normalize_yahoo_symbol` (`core/utils/validators.py`). Invalid values fall back to
  defaults rather than erroring.
- **Symbol formats differ by tool family**:
  - TradingView tools take exchange + bare symbol (e.g. `BTCUSDT`, `COMI`, `THYAO`), often
    normalized to `EXCHANGE:SYMBOL`.
  - Yahoo/backtest tools take Yahoo-format symbols (`AAPL`, `BTC-USD`, `THYAO.IS`, `^GSPC`,
    `EURUSD=X`).
- **Graceful degradation**: network/parse failures should return error dicts or fall back
  (e.g. ATR fetched directly when `tradingview-ta` omits it; proxy optional), not crash.
- **No secrets in code**; use env/`.env`.
- Docs/CI: Markdown-only changes are excluded from the Docker publish workflow via
  `paths-ignore`.

## Pitfalls / Gotchas

- **`pandas` build timeout on Windows**: a fresh `uvx` install on a too-new Python (e.g.
  3.14) may source-build `pandas` and exceed Claude Desktop's 60s init timeout. Fix: pin
  `--python 3.13`, or pre-run `uv tool install --python 3.13 tradingview-mcp-server`.
- **macOS PATH**: GUI apps may lack `~/.local/bin` in PATH — use the full path to `uvx` in
  the client config.
- **`coinlist/*.txt` are package data**: declared in `pyproject.toml`
  (`[tool.setuptools.package-data]`). New exchange symbol files must live under
  `src/tradingview_mcp/coinlist/` and the Docker build copies the source tree so they ship.
- **AMEX vs NYSE prefix**: ETFs (GDX, GLD, SPY, QQQ) live on NYSE Arca; TradingView wants
  the `AMEX:` prefix. `nysearca`/`pcx`/`amex` all map to `AMEX` in
  `_EXCHANGE_TV_PREFIX`. Using `NYSE:GDX` returns no data.
- **ATR null bug**: `tradingview-ta` omits the `ATR` column; `analyze_coin` falls back to a
  direct `scanner.tradingview.com` request (`fetch_atr_for_ticker` in
  `screener_provider.py`). Keep that fallback when touching analysis code.
- **OpenClaw `trading.py` is a separate interface**: `openclaw/SKILL.md` lists command names
  (e.g. `calculate_rsi`, `screener_bullish`, `technical_analysis`) that are the bash wrapper's
  own commands and do **not** all match the MCP tool names in `server.py`. OpenClaw imports
  service functions directly (no MCP protocol) and the wrapper hardcodes a uv site-packages
  path. Don't confuse the two tool name sets.
- **Backtest engine is hand-rolled**: don't reach for `pandas`/`numpy`/`yfinance`; indicators
  live in `indicators_calc.py` and data comes from Yahoo's chart HTTP API.
- **Version is maintained in three places**: `pyproject.toml`, `.codex-plugin/plugin.json`,
  and the README badge — keep them in sync on release.
