"""Offline demo broker.

Serves a realistic-but-fake portfolio so every feature (metrics, tips, plan,
dashboard, MCP tools) can be exercised with no Robinhood account and no
network. It is strictly read-only and refuses to submit orders.
"""

from __future__ import annotations

from .base import Broker, OrderRequest, OrderResult, Portfolio, Position

# A deliberately *imperfect* sample portfolio so the tips engine has something
# to talk about: over-concentrated in one tech name, heavy single sector,
# a chunk of crypto, a losing position, and a lot of idle cash.
_SAMPLE = [
    Position("NVDA", 18, 122.50, 70.00, "NVIDIA Corp", "stock", "Technology"),
    Position("AAPL", 12, 198.40, 165.00, "Apple Inc", "stock", "Technology"),
    Position("MSFT", 6, 421.30, 380.00, "Microsoft Corp", "stock", "Technology"),
    Position("VOO", 9, 505.10, 470.00, "Vanguard S&P 500 ETF", "etf", "Index"),
    Position("TSLA", 7, 178.20, 250.00, "Tesla Inc", "stock", "Consumer Cyclical"),
    Position("KO", 20, 62.10, 58.00, "Coca-Cola Co", "stock", "Consumer Defensive"),
    Position("BTC", 0.05, 64200.00, 48000.00, "Bitcoin", "crypto", "Crypto"),
    Position("ETH", 0.8, 3380.00, 2600.00, "Ethereum", "crypto", "Crypto"),
]


class DemoBroker(Broker):
    read_only = True

    def get_portfolio(self) -> Portfolio:
        # Fresh copies each call so callers can mutate without side effects.
        positions = [Position(**vars(p)) for p in _SAMPLE]
        return Portfolio(positions=positions, cash=4200.0, account_label="Demo (sample data)")

    def get_quote(self, symbol: str, asset_type: str = "stock") -> float:
        for p in _SAMPLE:
            if p.symbol.upper() == symbol.upper():
                return p.price
        return 0.0

    def submit_order(self, order: OrderRequest) -> OrderResult:
        return OrderResult(
            accepted=False,
            dry_run=True,
            detail=(
                "Demo broker is read-only and never submits orders. "
                "Set RH_ADVISOR_BROKER=robinhood (and arm live trading) to trade for real."
            ),
        )
