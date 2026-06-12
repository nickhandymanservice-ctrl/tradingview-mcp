"""Core data model and the Broker protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Position:
    """A single holding."""

    symbol: str
    quantity: float
    price: float                      # current market price per share/unit
    average_buy_price: float = 0.0    # your cost per share/unit
    name: str = ""                    # human-readable name
    asset_type: str = "stock"         # stock | etf | crypto | cash
    sector: str = "Unknown"

    @property
    def equity(self) -> float:
        """Current market value of the position."""
        return self.quantity * self.price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.average_buy_price

    @property
    def unrealized_gain(self) -> float:
        return self.equity - self.cost_basis

    @property
    def unrealized_gain_pct(self) -> float:
        if self.cost_basis <= 0:
            return 0.0
        return self.unrealized_gain / self.cost_basis


@dataclass
class Portfolio:
    """A snapshot of an account."""

    positions: list[Position] = field(default_factory=list)
    cash: float = 0.0
    account_label: str = "Robinhood"

    @property
    def invested_equity(self) -> float:
        return sum(p.equity for p in self.positions)

    @property
    def total_value(self) -> float:
        return self.invested_equity + self.cash

    @property
    def total_cost_basis(self) -> float:
        return sum(p.cost_basis for p in self.positions)

    @property
    def total_unrealized_gain(self) -> float:
        return sum(p.unrealized_gain for p in self.positions)


@dataclass
class OrderRequest:
    """A trade the caller wants to make."""

    symbol: str
    side: str               # buy | sell
    amount_usd: float | None = None    # dollar-based order
    quantity: float | None = None      # share/unit-based order
    asset_type: str = "stock"          # stock | crypto


@dataclass
class OrderResult:
    """What the broker reports back after a submit attempt."""

    accepted: bool
    detail: str
    dry_run: bool
    broker_order_id: str | None = None
    raw: dict | None = None


@runtime_checkable
class Broker(Protocol):
    """Everything the advisor needs from a brokerage backend."""

    read_only: bool

    def get_portfolio(self) -> Portfolio: ...

    def get_quote(self, symbol: str, asset_type: str = "stock") -> float: ...

    def submit_order(self, order: OrderRequest) -> OrderResult: ...
