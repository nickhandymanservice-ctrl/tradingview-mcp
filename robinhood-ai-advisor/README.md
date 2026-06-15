# 📈 Robinhood AI Advisor

An AI-assisted, **read-first** advisor for your Robinhood account. It pulls your
holdings, computes risk/diversification metrics, gives plain-English **tips**
(observations, *not* advice), drafts a **personalized investment plan**, and can
**propose trades that always require a second confirmation** before anything is
submitted.

> ⚠️ **Educational tool, not financial advice.** Nothing here recommends
> securities or predicts prices. Read [`DISCLAIMER.md`](DISCLAIMER.md) before
> using live mode.

---

## What you get

| Capability | How |
|---|---|
| See your investments | Holdings table, total value, per-position gain/loss |
| Risk & diversification metrics | Concentration (HHI), sector/asset mix, cash %, crypto %, a 0–100 diversification score |
| Tips on how to improve | Deterministic rules engine — flags concentration, sector/crypto overexposure, cash drag, big losers/winners |
| Investment plan | Target allocation by risk profile + dollar-gap analysis + DCA contribution split + action checklist |
| Trade (carefully) | `propose` → `confirm` flow with a one-time token; live trading **off by default** |
| Two AI "brains" | (1) offline rules engine, (2) **Claude via MCP** — your claude.ai subscription, **no API key** |
| Three surfaces | CLI, local web dashboard, MCP server |
| **Official Robinhood trading** | Works with Robinhood's **Agentic Trading MCP** (OAuth, kill switch). See [`ROBINHOOD_AGENTIC.md`](ROBINHOOD_AGENTIC.md) |

The core (metrics, tips, planner, CLI) needs **only the Python standard
library** — it runs immediately against a built-in demo portfolio.

---

## Quick start (offline demo, 30 seconds)

```bash
cd robinhood-ai-advisor
python -m rh_advisor.cli summary      # holdings table (sample data)
python -m rh_advisor.cli metrics      # risk/diversification metrics
python -m rh_advisor.cli tips         # educational tips
python -m rh_advisor.cli plan --risk balanced --monthly 500
```

No install, no account, no keys. When you're ready, point it at your real
account (below).

---

## The trade-safety model (read this)

1. **Nothing trades in one step.** Every order is `propose` → `confirm` with a
   one-time token that expires in 5 minutes.
2. **Live trading is OFF by default.** An order only reaches Robinhood when
   **both** `RH_ADVISOR_BROKER=robinhood` and `RH_ADVISOR_ALLOW_LIVE_TRADES=yes`.
   Otherwise it's a dry-run (simulated).
3. **Per-order ceiling** (`RH_ADVISOR_MAX_ORDER_USD`, default $2000) flags
   oversized proposals.

```bash
# Propose (submits nothing):
python -m rh_advisor.cli propose --symbol VOO --side buy --usd 200
#   → prints a summary + a token, e.g. "Confirm with token 1f7e7b7e"
# Confirm (only now does it reach the broker, and only if live is armed):
python -m rh_advisor.cli confirm --token 1f7e7b7e
```

---

## Connect your real Robinhood account

You have two paths:

### A. Official Robinhood Agentic Trading MCP (recommended for trading)

Robinhood's own hosted MCP server (launched May 27, 2026) lets Claude read your
account and place equity trades via **OAuth — no password, no API key** — with a
real-time activity feed, per-trade push notifications, and an **instant kill
switch**.

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

Then let Claude pull your positions from Robinhood and feed them to this app's
analysis tools (`analyze_holdings`, `plan_for_holdings`). Full walkthrough +
two-server config: **[`ROBINHOOD_AGENTIC.md`](ROBINHOOD_AGENTIC.md)**.

### B. `robin_stocks` (fallback for a regular, non-agentic account)

Use this if you don't have a Robinhood Agentic Account. It powers this app's own
read + propose→confirm flow directly.

```bash
pip install robin_stocks pyotp
cp .env.example .env       # then edit .env
```

In `.env`:

```ini
RH_ADVISOR_BROKER=robinhood
RH_USERNAME=you@example.com
RH_PASSWORD=your-password
RH_MFA_SECRET=YOURBASE32TOTPSECRET   # from Robinhood's authenticator-app setup
RH_ADVISOR_ALLOW_LIVE_TRADES=no      # keep "no" until you're confident
```

> Robinhood has **no official API**; live mode uses the community `robin_stocks`
> library, which logs in with your credentials. It's great for reading your
> portfolio but is unofficial — see [`DISCLAIMER.md`](DISCLAIMER.md). Credentials
> stay in your local, git-ignored `.env`.

Now the same commands (`summary`, `tips`, `plan`, …) operate on your real data.

---

## Use Claude as the AI brain (no API key)

The MCP server exposes the advisor as tools Claude can call. Attach it from
**Claude Desktop or mobile** using your **claude.ai subscription** — you run and
audit everything from the Claude app, no Anthropic API key needed.

```bash
pip install mcp
python mcp_server.py        # runs over stdio
```

Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "robinhood-advisor": {
      "command": "python",
      "args": ["/absolute/path/to/robinhood-ai-advisor/mcp_server.py"]
    }
  }
}
```

Then ask Claude things like:

> *"Pull my Robinhood portfolio, review my diversification, and give me three
> concrete tips. Then build a balanced plan with $500/month and propose a first
> trade — but don't confirm it until I say so."*

Tools exposed: `portfolio_summary`, `portfolio_metrics`, `portfolio_tips`,
`investment_plan`, `propose_trade`, `confirm_trade`, `pending_trade`, plus
`analyze_holdings` and `plan_for_holdings` (analyze positions passed in from the
official Robinhood Agentic MCP). The same propose→confirm seatbelt applies to
Claude.

---

## Web dashboard

```bash
pip install fastapi uvicorn
python web/app.py            # → http://127.0.0.1:8000
```

A single-page dashboard: total value, diversification score, allocation
doughnuts (by holding and by sector), holdings table, live tips, an interactive
plan builder, and a propose/confirm trade panel.

---

## CLI reference

| Command | Description |
|---|---|
| `summary` | Holdings table with values and gain% |
| `metrics` | Concentration, sector/asset allocation, cash %, scores |
| `tips` | Educational rules-engine tips |
| `plan --risk {conservative\|balanced\|aggressive} --monthly N` | Investment plan |
| `propose --symbol S --side {buy\|sell} [--usd N \| --shares N] [--asset-type {stock\|crypto}]` | Stage a trade (no submit) |
| `confirm --token T` | Submit the staged trade |
| `pending` | Show the current staged proposal |

---

## Architecture

```
rh_advisor/
  config.py            # settings + safety flags from .env
  broker/
    base.py            # Position / Portfolio / Broker protocol
    demo.py            # offline sample portfolio (read-only)
    robinhood.py       # robin_stocks backend (lazy-imported)
  analysis/
    metrics.py         # deterministic portfolio metrics
    tips.py            # rules engine (the offline AI brain)
  planner/plan.py      # risk profiles, gap analysis, action checklist
  trading/orders.py    # propose -> confirm token flow
  ingest.py            # parse external holdings (e.g. Robinhood Agentic MCP)
  service.py           # facade shared by CLI / web / MCP
  cli.py               # argparse CLI
web/app.py + static/   # FastAPI dashboard (Chart.js)
mcp_server.py          # MCP server (attach Claude, no API key)
tests/                 # 21 unit tests (stdlib-only core)
```

Run the tests:

```bash
pip install pytest && python -m pytest tests/ -q
```

---

## License & disclaimer

Provided as-is for educational purposes. **Not financial advice.** You are
responsible for every trade you confirm. See [`DISCLAIMER.md`](DISCLAIMER.md).
