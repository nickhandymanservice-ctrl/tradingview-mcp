"""Tests for ingesting external holdings (e.g. from Robinhood's official MCP)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rh_advisor.ingest import portfolio_from_records


def test_parses_canonical_records():
    p = portfolio_from_records(
        [
            {"symbol": "AAPL", "quantity": 10, "price": 200.0, "average_buy_price": 150.0,
             "asset_type": "stock", "sector": "Technology"},
            {"symbol": "VOO", "shares": 5, "market_price": 500.0, "type": "etp"},
        ],
        cash=1000.0,
    )
    assert len(p.positions) == 2
    assert p.cash == 1000.0
    aapl = next(x for x in p.positions if x.symbol == "AAPL")
    assert aapl.equity == 2000.0
    voo = next(x for x in p.positions if x.symbol == "VOO")
    assert voo.asset_type == "etf"          # "etp" normalized
    assert voo.quantity == 5                # "shares" alias picked up


def test_derives_avg_from_cost_basis():
    p = portfolio_from_records([{"ticker": "MSFT", "qty": 4, "price": 400.0, "cost_basis": 1200.0}])
    msft = p.positions[0]
    assert abs(msft.average_buy_price - 300.0) < 1e-9


def test_skips_bad_or_empty_rows():
    p = portfolio_from_records([
        {"symbol": "", "quantity": 5, "price": 10},     # no symbol
        {"symbol": "ZZZ", "quantity": 0, "price": 10},  # zero qty
        {"symbol": "OK", "quantity": 1, "price": 10},
    ])
    assert [x.symbol for x in p.positions] == ["OK"]


def test_handles_none_and_empty():
    assert portfolio_from_records(None).total_value == 0.0
    assert portfolio_from_records([], cash=50).total_value == 50.0
