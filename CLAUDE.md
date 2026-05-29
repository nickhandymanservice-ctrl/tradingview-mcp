# CLAUDE.md

Guidance for AI coding assistants working in this repository.

## Project Overview

**tradingview-mcp** (PyPI package: `tradingview-mcp-server`) is a Python
**Model Context Protocol (MCP) server** that exposes an "AI Trading Intelligence
Framework" to MCP clients (Claude Desktop, Codex, Cursor, etc.). It provides
30+ tools for market data, multi-exchange screening, technical analysis,
sentiment, news, options, and strategy backtesting.

Key characteristics:
- **No API keys required** for core functionality. Data comes from public
  sources: TradingView (via `tradingview-screener` / `tradingview-ta`), Yahoo
  Finance's public chart API (raw HTTP), Reddit, and RSS news feeds.
- Backtesting and Yahoo Finance services are **pure Python** (no pandas/numpy in
  that code). `pandas`/`numpy` are pulled in only transitively by
  `tradingview-screener`.
- License: MIT. Current version: `0.7.1` (see `pyproject.toml`).

## Tech Stack

- **Language:** Python `>=3.10` (Docker image uses 3.11; README recommends
  pinning `uvx --python 3.13` on Windows to get prebuilt pandas wheels).
- **Package manager:** [`uv`](https://docs.astral.sh/uv/) (with `uv.lock`).
- **MCP framework:** `mcp[cli]>=1.12.0`, specifically `FastMCP`
  (`from mcp.server.fastmcp import FastMCP`).
- **Build backend:** setuptools (`src/` layout, packages found under `src`).
- **Direct dependencies** (`pyproject.toml`): `feedparser`, `mcp[cli]`,
  `requests`, `tradingview-screener`, `tradingview-ta`.
- **Dev dependency:** `pytest` (under `[tool.uv] dev-dependencies`).

## Repository Layout

```
src/tradingview_mcp/
  __init__.py
  server.py                 # MCP entrypoint: ALL @mcp.tool() definitions live here (routing only)
  coinlist/*.txt            # Per-exchange symbol lists (binance.txt, nasdaq.txt, egx.txt, ...)
  core/
    types.py
    portfolio.py
    data/                   # Static data (egx_indices.py, egx_sectors.py)
    services/               # ALL business logic lives here
      backtest_service.py        # run_backtest, compare_strategies, walk_forward_backtest (pure Python)
      yahoo_finance_service.py    # get_price, get_market_snapshot (raw Yahoo chart API via requests)
      bitcoin_market_service.py
      extended_hours_service.py
      options_service.py
      screener_service.py / scanner_service.py / screener_provider.py
      multi_agent_service.py      # 3-agent debate (Technical / Sentiment / Risk)
      egx_service.py              # Egyptian Exchange tools
      sentiment_service.py        # Reddit sentiment
      news_service.py             # RSS news
      indicators.py / indicators_calc.py
      coinlist.py                 # load_symbols(exchange) reads coinlist/*.txt
      proxy_manager.py            # optional Webshare proxy support
    utils/
      validators.py         # sanitize_timeframe, sanitize_exchange, normalize_*_symbol
tests/unit/                 # pytest tests (validators, exchange aliases/fixes, ATR injection)
openclaw/                   # SKILL.md + trading.py (OpenClaw bash-wrapper integration)
.codex-plugin/plugin.json   # Codex plugin metadata -> references .codex-mcp.json
.codex-mcp.json             # Codex MCP server config (uvx --from tradingview-mcp-server tradingview-mcp)
Dockerfile / docker-compose.yml
```

### Architecture convention (important)

`server.py` is a **routing layer only**. Each `@mcp.tool()` handler should:
1. Validate/sanitize parameters (use `core/utils/validators.py` helpers).
2. Delegate to the matching function in `core/services/*`.
3. Return the result.

**Do not put business/computation logic in `server.py`.** Add it to a service
module and call it from the tool handler. New tools are added by writing a
`@mcp.tool()`-decorated function in `server.py` that wraps a service function.

## Entrypoint

- Console script: `tradingview-mcp = "tradingview_mcp.server:main"` (`pyproject.toml`).
- `main()` parses an optional positional `transport` arg: `stdio` (default) or
  `streamable-http`, plus `--host` / `--port` (env `HOST`, `PORT`, default
  `127.0.0.1:8000`). `DEBUG_MCP=1` prints debug info to stderr.
- There is also an `@mcp.resource("exchanges://list")` resource listing exchanges.

## Build / Run / Dev / Test Commands

```bash
# Install deps into a uv-managed venv
uv sync

# Run the server from source (stdio transport, default)
uv run tradingview-mcp

# Run over HTTP (for Docker/remote)
uv run tradingview-mcp streamable-http --host 0.0.0.0 --port 8000

# Run tests
uv run pytest
uv run pytest tests/unit/test_validators.py   # single file
```

(`pip install tradingview-mcp-server` then `tradingview-mcp` also works once
installed.)

## Configuration & Environment Variables

All env vars are **optional**; the server runs fully without any of them.
See `.env.example` (copy to `.env`, which is gitignored).

- **Proxy (optional, Webshare rotating residential):** `PROXY_ENABLED`,
  `PROXY_HOST`, `PROXY_PORT`, `PROXY_USERNAME_PREFIX`, `PROXY_PASSWORD`,
  `PROXY_SESSION_MIN`, `PROXY_SESSION_MAX`. Improves access to Yahoo Finance /
  Xueqiu and reduces Reddit rate-limits. Handled by
  `core/services/proxy_manager.py`. Leave blank to run without a proxy.
- **Server transport:** `HOST`, `PORT` (HTTP mode), `DEBUG_MCP` (debug logging).
- **No trading/broker API keys** are used or required.

## Tools Exposed (defined in `server.py`)

- **Screeners:** `top_gainers`, `top_losers`, `bollinger_scan`, `rating_filter`,
  `consecutive_candles_scan`, `advanced_candle_pattern`,
  `volume_breakout_scanner`, `volume_confirmation_analysis`,
  `smart_volume_scanner`.
- **Analysis:** `coin_analysis`, `multi_agent_analysis`,
  `multi_timeframe_analysis`, `combined_analysis` (technical + Reddit + news).
- **Sentiment / news:** `market_sentiment` (Reddit), `financial_news` (RSS).
- **Backtesting:** `backtest_strategy`, `compare_strategies`,
  `walk_forward_backtest_strategy`. Six strategies: `rsi`, `bollinger`, `macd`,
  `ema_cross`, `supertrend`, `donchian`.
- **Yahoo Finance / market data:** `yahoo_price`, `market_snapshot`,
  `bitcoin_market_pulse`, `stock_extended_hours`, `stock_options_chain`,
  `stock_options_unusual_activity`.
- **EGX (Egyptian Exchange):** `egx_market_overview`, `egx_sector_scan`,
  `egx_sector_scanner`, `egx_index_analysis`, `egx_stock_screener`,
  `egx_trade_plan`, `egx_fibonacci_retracement`.

Supported markets: crypto exchanges (KUCOIN, BINANCE, BYBIT, MEXC, BITGET, OKX,
COINBASE, etc.) and stock markets (NASDAQ, NYSE, AMEX, BIST, EGX, BURSA, HKEX,
SSE, SZSE, TWSE, TPEX). Symbol formats differ per tool: TradingView screeners
take exchange + bare symbol (e.g. `BTCUSDT`, `COMI`); backtest/Yahoo tools take
Yahoo symbols (`AAPL`, `BTC-USD`, `^GSPC`, `THYAO.IS`).

## Distribution

- **PyPI:** `tradingview-mcp-server`. Recommended client config uses
  `uvx --from tradingview-mcp-server tradingview-mcp` (see README for Claude
  Desktop JSON). On Windows, pin `--python 3.13` to avoid a source build of
  pandas blowing past the 60s MCP init timeout.
- **Docker:** multi-stage `Dockerfile` (python:3.11-slim, installs via
  `uv pip install --system .`, runs as non-root `mcpuser`, `streamable-http` on
  port 8000, has a `/health` HEALTHCHECK). `docker-compose.yml` maps host
  `8080 -> 8000`. CI (`.github/workflows/publish-image.yml`) builds multi-arch
  (amd64/arm64) images and pushes to GHCR on `main` pushes and `v*` tags.
- **Codex plugin:** `.codex-plugin/plugin.json` + `.codex-mcp.json` register the
  same `uvx` entrypoint. Restart Codex after enabling.
- **OpenClaw:** `openclaw/` contains `SKILL.md` and `trading.py`. OpenClaw does
  **not** use the MCP protocol here — `trading.py` is a thin CLI wrapper that
  imports `tradingview_mcp.core.services.*` directly (bash bridge) so messaging
  channels (Telegram/WhatsApp/Discord) can call the library. See `OPENCLAW.md`.

## Conventions & Gotchas for AI Assistants

- Add new MCP tools in `server.py` as thin wrappers; implement logic in a
  `core/services/` module.
- Always sanitize tool inputs via `validators.py`
  (`sanitize_timeframe`, `sanitize_exchange`, `normalize_tradingview_symbol`,
  `normalize_yahoo_symbol`) and clamp numeric `limit`/threshold params like the
  existing tools do (e.g. `limit = max(1, min(limit, 50))`).
- Timeframes are normalized to TradingView style: lowercase intraday is kept
  (`5m`, `15m`, `1h`, `4h`); `1d/1w/1m` are uppercased to `1D/1W/1M`. Verify in
  `tests/unit/test_validators.py`.
- Tool functions return plain `dict`/`list[dict]`; keep docstrings accurate —
  they become the MCP tool descriptions shown to clients.
- `coinlist/*.txt` are packaged data files (`[tool.setuptools.package-data]`).
  Read them via the package path (see the `exchanges://list` resource and
  `core/services/coinlist.py`), not a hardcoded CWD path.
- `tradingview_screener` import is guarded (`TRADINGVIEW_SCREENER_AVAILABLE`);
  some tools fall back when it is unavailable. Preserve that pattern.
- Network-dependent services (Yahoo, Reddit, RSS, TradingView) can fail or rate
  limit; handle errors gracefully and return error dicts rather than raising.
- Keep `pyproject.toml` `version` and `.codex-plugin/plugin.json` `version`
  in sync when bumping releases.
- This is educational/research tooling, not financial advice.
