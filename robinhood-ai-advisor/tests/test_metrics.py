"""Unit tests for the metrics engine (pure functions, no network)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rh_advisor.analysis.metrics import compute_metrics
from rh_advisor.broker.base import Portfolio, Position


def _portfolio():
    return Portfolio(
        positions=[
            Position("AAA", 10, 100.0, 50.0, asset_type="stock", sector="Tech"),  # 1000, +100%
            Position("BBB", 10, 50.0, 60.0, asset_type="stock", sector="Tech"),   # 500, -16.7%
            Position("CCC", 1, 500.0, 400.0, asset_type="crypto", sector="Crypto"),  # 500
        ],
        cash=1000.0,
    )


def test_totals():
    m = compute_metrics(_portfolio())
    assert m.invested_equity == 2000.0
    assert m.cash == 1000.0
    assert m.total_value == 3000.0
    assert abs(m.cash_pct - (1000.0 / 3000.0)) < 1e-9


def test_top_holding_and_hhi():
    m = compute_metrics(_portfolio())
    assert m.top_holding_symbol == "AAA"
    assert abs(m.top_holding_pct - (1000.0 / 3000.0)) < 1e-9
    # HHI over invested weights: 0.5^2 + 0.25^2 + 0.25^2 = 0.375
    assert abs(m.concentration_hhi - 0.375) < 1e-9


def test_sector_and_crypto():
    m = compute_metrics(_portfolio())
    # Tech = (1000+500)/2000 = 0.75 of invested
    assert abs(m.sector_allocation["Tech"] - 0.75) < 1e-9
    # Crypto = 500 / 3000 of total account
    assert abs(m.crypto_pct - (500.0 / 3000.0)) < 1e-9


def test_unrealized_gain():
    m = compute_metrics(_portfolio())
    # AAA +500, BBB -100, CCC +100 => +500 total; cost basis = 500+600+400=1500
    assert abs(m.total_unrealized_gain - 500.0) < 1e-9
    assert abs(m.total_unrealized_gain_pct - (500.0 / 1500.0)) < 1e-9


def test_empty_portfolio_is_safe():
    m = compute_metrics(Portfolio())
    assert m.total_value == 0.0
    assert m.diversification_score == 0.0
    assert m.top_holding_pct == 0.0
