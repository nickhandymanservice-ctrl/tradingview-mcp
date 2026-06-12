"""Robinhood AI Advisor.

A read-first portfolio assistant for Robinhood:

* pull your holdings,
* compute risk / diversification metrics,
* generate plain-English tips (NOT financial advice),
* draft a personalized investment plan, and
* propose trades that always require an explicit second confirmation
  before anything is ever submitted to the broker.

The AI "brain" is pluggable:

* a built-in deterministic rules engine works offline with no API key, and
* an MCP server (``mcp_server.py``) lets you attach Claude (via your
  claude.ai subscription on desktop or mobile) to read, reason about, and
  audit everything here without an API key.

Nothing in this package places a live order on its own. See DISCLAIMER.md.
"""

__version__ = "0.1.0"
