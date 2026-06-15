# Using Robinhood's Official Agentic Trading MCP (recommended)

On **May 27, 2026** Robinhood launched **Agentic Trading**: a dedicated
brokerage account you connect an AI agent to through Robinhood's own hosted MCP
server. This is the **recommended** way to let Claude see your account and place
trades — it's official, uses OAuth (no stored password, no API key), and ships
with real broker-side safety controls.

- **Endpoint:** `https://agent.robinhood.com/mcp/trading`
- **Auth:** OAuth to a dedicated Robinhood Agentic Account (you approve it)
- **Safety built in by Robinhood:** real-time activity feed, P&L tracking,
  **per-trade push notifications**, and an **instant kill switch** to disconnect
  the agent at any time
- **Scope (beta):** equities today; options/crypto/futures "coming soon"

> Set up the Agentic Account from the Robinhood app first. Funds in the agentic
> account are what the agent can act on — keep it sized to your comfort.

## Connect it to Claude

```bash
claude mcp add robinhood-trading --transport http https://agent.robinhood.com/mcp/trading
```

Claude walks you through the OAuth approval on first use. After that, Claude can
read your agentic account and place equity trades directly through Robinhood —
with Robinhood's own confirmation + kill-switch protecting you.

## How this advisor fits in (two MCP servers, one Claude)

```
                 ┌─────────────────────────────────────────┐
                 │                  Claude                  │
                 │            (claude.ai, no API key)       │
                 └───────────────┬───────────────┬──────────┘
                                 │               │
        reads account & trades   │               │  diversification, tips, plan
                                 ▼               ▼
   ┌──────────────────────────────────┐   ┌──────────────────────────────┐
   │  Robinhood Agentic Trading MCP   │   │   This advisor's MCP server   │
   │  agent.robinhood.com/mcp/trading │   │        (mcp_server.py)        │
   │  • official, OAuth, kill switch  │   │  • analyze_holdings           │
   │  • read positions, place trades  │   │  • plan_for_holdings          │
   └──────────────────────────────────┘   └──────────────────────────────┘
```

- **Robinhood's MCP** = the source of truth + the thing that actually trades.
- **This advisor's MCP** = the *analysis brain*. It does not need its own
  Robinhood connection: Claude fetches your positions from Robinhood's MCP and
  hands them to `analyze_holdings` / `plan_for_holdings`.

### Example prompt

> *"Use the robinhood-trading tools to pull my current positions and cash.
> Then call analyze_holdings with them for a diversification review and tips,
> and plan_for_holdings with a balanced profile and $500/month. Summarize the
> top 3 things to improve. Don't place any trades yet — show me first."*

Claude will read from Robinhood, run it through this advisor's analysis, and
report back. Any actual order goes through Robinhood's own MCP, so Robinhood's
confirmation and kill switch apply.

## Run both servers together

See [`.mcp.json.example`](.mcp.json.example) for a config that registers both
the official Robinhood server and this advisor's server at once.

## Do I still need the `robin_stocks` path?

Only if you are **not** using a Robinhood Agentic Account. The bundled
`robin_stocks` broker (see `README.md`) remains as a fallback for reading a
regular Robinhood account and for this app's own propose→confirm trade flow.
If you have the Agentic Account, prefer the official MCP above for anything that
places orders.

## Safety notes

- Robinhood's kill switch is your fastest "stop everything" — know where it is.
- Start in the agentic account with a small balance while you learn the agent's
  behavior.
- Nothing here is financial advice. See [`DISCLAIMER.md`](DISCLAIMER.md).

Sources: Robinhood Newsroom — "Robinhood is Now Open to Agents"; Robinhood
"Agentic Trading overview" support article (May 27, 2026).
