"""Unit tests for the rules-based tips engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rh_advisor.analysis.metrics import compute_metrics
from rh_advisor.analysis.tips import generate_tips
from rh_advisor.broker.base import Portfolio, Position


def _tips_for(portfolio):
    return generate_tips(compute_metrics(portfolio))


def _categories(tips):
    return {t.category for t in tips}


def test_single_name_concentration_warns():
    p = Portfolio(positions=[
        Position("BIG", 10, 100.0, 100.0, asset_type="stock", sector="Tech"),
        Position("SML", 1, 50.0, 50.0, asset_type="stock", sector="Health"),
    ], cash=0.0)
    tips = _tips_for(p)
    assert "concentration" in _categories(tips)
    assert any("BIG" in t.title for t in tips)


def test_cash_drag_flagged():
    p = Portfolio(positions=[Position("X", 1, 100.0, 100.0, sector="Tech")], cash=900.0)
    tips = _tips_for(p)
    assert any(t.category == "cash" for t in tips)


def test_crypto_heavy_warns():
    p = Portfolio(positions=[
        Position("BTC", 1, 600.0, 600.0, asset_type="crypto", sector="Crypto"),
        Position("VOO", 1, 400.0, 400.0, asset_type="etf", sector="Index"),
    ], cash=0.0)
    tips = _tips_for(p)
    assert any(t.category == "risk" and "Crypto" in t.title for t in tips)


def test_big_loser_flagged():
    p = Portfolio(positions=[
        Position("DOWN", 10, 50.0, 100.0, sector="Tech"),   # -50%
        Position("OK", 10, 100.0, 100.0, sector="Health"),
        Position("OK2", 10, 100.0, 100.0, sector="Energy"),
        Position("OK3", 10, 100.0, 100.0, sector="Index"),
        Position("OK4", 10, 100.0, 100.0, sector="Utilities"),
    ], cash=50.0)
    tips = _tips_for(p)
    assert any("DOWN" in t.title and "down" in t.title.lower() for t in tips)


def test_empty_portfolio_returns_info():
    tips = _tips_for(Portfolio())
    assert len(tips) == 1
    assert tips[0].severity == "info"


def test_every_tip_has_required_fields():
    p = Portfolio(positions=[Position("X", 1, 100.0, 100.0, sector="Tech")], cash=900.0)
    for t in _tips_for(p):
        assert t.severity in {"info", "suggestion", "warning"}
        assert t.title and t.detail and t.category
