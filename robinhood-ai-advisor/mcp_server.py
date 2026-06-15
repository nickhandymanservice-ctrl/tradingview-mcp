"""MCP server exposing the advisor to Claude (no API key required).

Run this and connect it from Claude Desktop / mobile (claude.ai) as an MCP
server. Claude then becomes the "AI brain": it can read your portfolio,
metrics, tips, and plan, and can *propose* trades — but, exactly like the CLI,
it must call ``confirm_trade`` with the one-time token to submit anything, and
only when live trading is armed. This keeps you in the loop and lets you audit
every step from the Claude app.

Usage (stdio transport):
    python mcp_server.py

Claude Desktop config snippet (claude_desktop_config.json):
    {
      "mcpServers": {
        "robinhood-advisor": {
          "command": "python",
          "args": ["/absolute/path/to/robinhood-ai-advisor/mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from rh_advisor.service import Advisor

mcp = FastMCP("robinhood-advisor")


def _advisor() -> Advisor:
    # Build per-call so .env / settings changes are picked up without restart.
    return Advisor()


def _json(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


@mcp.tool()
def portfolio_summary() -> str:
    """Return current Robinhood holdings, cash, and per-position values as JSON."""
    return _json(_advisor().portfolio())


@mcp.tool()
def portfolio_metrics() -> str:
    """Return risk/diversification metrics (concentration HHI, sector & asset
    allocation, cash %, crypto %, unrealized gains, diversification score)."""
    return _json(_advisor().metrics())


@mcp.tool()
def portfolio_tips() -> str:
    """Return deterministic, rules-based educational tips about the portfolio.
    These are observations, not financial advice."""
    return _json(_advisor().tips())


@mcp.tool()
def investment_plan(risk_profile: str = "balanced", monthly_contribution: float = 0.0) -> str:
    """Generate a target-allocation investment plan.

    Args:
        risk_profile: one of "conservative", "balanced", "aggressive".
        monthly_contribution: planned monthly contribution in USD.
    """
    return _json(_advisor().plan(risk_profile, monthly_contribution))


@mcp.tool()
def propose_trade(
    symbol: str,
    side: str,
    amount_usd: float | None = None,
    quantity: float | None = None,
    asset_type: str = "stock",
) -> str:
    """Stage a trade and return a summary + one-time confirmation token.

    This NEVER submits an order. Provide exactly one of amount_usd or quantity.
    To actually place it, call confirm_trade with the returned token.
    """
    try:
        return _json(_advisor().propose_trade(symbol, side, amount_usd, quantity, asset_type))
    except ValueError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def confirm_trade(token: str) -> str:
    """Submit the pending proposed trade identified by its token.

    Only reaches the broker when live trading is armed; otherwise it simulates.
    """
    try:
        return _json(_advisor().confirm_trade(token))
    except ValueError as exc:
        return _json({"error": str(exc)})


@mcp.tool()
def pending_trade() -> str:
    """Return the current pending trade proposal, if any."""
    return _json(_advisor().pending_trade() or {"pending": None})


@mcp.tool()
def analyze_holdings(holdings: list[dict], cash: float = 0.0) -> str:
    """Run diversification metrics + tips on holdings you pass in.

    Use this to analyze data from the OFFICIAL Robinhood Agentic Trading MCP
    (https://agent.robinhood.com/mcp/trading): fetch the account's positions
    there, then pass them here. Each holding is a dict; flexible field names
    are accepted (symbol/ticker, quantity/shares, price/market_price,
    average_buy_price/cost_basis, asset_type/type, sector). Returns JSON with
    "metrics" and "tips". This reads nothing and trades nothing.
    """
    return _json(_advisor().analyze_records(holdings, cash))


@mcp.tool()
def plan_for_holdings(
    holdings: list[dict],
    cash: float = 0.0,
    risk_profile: str = "balanced",
    monthly_contribution: float = 0.0,
) -> str:
    """Build an investment plan for holdings you pass in (e.g. from Robinhood's
    official Agentic MCP). Returns target allocation, dollar gaps, a monthly
    contribution split, and an action checklist."""
    return _json(_advisor().plan_records(holdings, cash, risk_profile, monthly_contribution))


if __name__ == "__main__":
    mcp.run()
