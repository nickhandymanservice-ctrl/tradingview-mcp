"""Ingest external holdings into the advisor's data model.

This is what lets Claude use the **official Robinhood Agentic Trading MCP**
(https://agent.robinhood.com/mcp/trading) as the data source: Claude pulls your
real holdings from Robinhood's hosted MCP, then hands the raw records to this
package's analysis tools. So our metrics/tips/planner work on live Robinhood
data without this code needing its own brokerage connection.

The parser is intentionally forgiving about field names because different
sources label things differently (quantity vs shares, price vs market_price,
average_buy_price vs cost_basis, etc.).
"""

from __future__ import annotations

from typing import Any

from .broker.base import Portfolio, Position

# Accepted aliases for each field we care about, in priority order.
_ALIASES: dict[str, tuple[str, ...]] = {
    "symbol": ("symbol", "ticker", "instrument", "name_symbol"),
    "quantity": ("quantity", "shares", "qty", "units", "amount"),
    "price": ("price", "market_price", "last_price", "current_price", "mark_price"),
    "average_buy_price": ("average_buy_price", "avg_cost", "average_cost", "cost_per_share"),
    "cost_basis": ("cost_basis", "total_cost", "cost_bases"),
    "name": ("name", "description", "company", "long_name"),
    "asset_type": ("asset_type", "type", "instrument_type", "security_type"),
    "sector": ("sector", "industry", "category"),
}

_TYPE_NORMALIZE = {
    "etp": "etf", "etf": "etf", "fund": "etf",
    "stock": "stock", "equity": "stock", "equities": "stock", "share": "stock",
    "crypto": "crypto", "cryptocurrency": "crypto", "coin": "crypto",
    "cash": "cash",
}


def _pick(record: dict, field: str) -> Any:
    for key in _ALIASES[field]:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return None


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def position_from_record(record: dict) -> Position | None:
    symbol = _pick(record, "symbol")
    if not symbol:
        return None
    quantity = _to_float(_pick(record, "quantity"))
    if quantity <= 0:
        return None
    price = _to_float(_pick(record, "price"))

    avg = _to_float(_pick(record, "average_buy_price"))
    if avg <= 0:
        cost_basis = _to_float(_pick(record, "cost_basis"))
        avg = (cost_basis / quantity) if (cost_basis > 0 and quantity) else 0.0

    raw_type = str(_pick(record, "asset_type") or "stock").strip().lower()
    asset_type = _TYPE_NORMALIZE.get(raw_type, "stock")

    return Position(
        symbol=str(symbol).upper(),
        quantity=quantity,
        price=price,
        average_buy_price=avg,
        name=str(_pick(record, "name") or symbol),
        asset_type=asset_type,
        sector=str(_pick(record, "sector") or "Unknown"),
    )


def portfolio_from_records(
    records: list[dict] | None,
    cash: float = 0.0,
    account_label: str = "Robinhood (via Agentic MCP)",
) -> Portfolio:
    """Build a Portfolio from a list of holding dicts (e.g. from Robinhood's MCP)."""
    positions = []
    for record in records or []:
        pos = position_from_record(record)
        if pos is not None:
            positions.append(pos)
    return Portfolio(positions=positions, cash=_to_float(cash), account_label=account_label)
