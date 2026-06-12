"""Unit tests for the planner."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rh_advisor.analysis.metrics import compute_metrics
from rh_advisor.broker.base import Portfolio, Position
from rh_advisor.planner import RISK_PROFILES, build_plan


def _metrics():
    return compute_metrics(Portfolio(
        positions=[
            Position("VOO", 10, 100.0, 100.0, asset_type="etf", sector="Index"),
            Position("BTC", 1, 100.0, 100.0, asset_type="crypto", sector="Crypto"),
        ],
        cash=800.0,
    ))


def test_targets_sum_to_one():
    for profile, weights in RISK_PROFILES.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, profile


def test_plan_rows_cover_all_buckets():
    plan = build_plan(_metrics(), "balanced", 0.0)
    buckets = {r.bucket for r in plan.rows}
    assert buckets == set(RISK_PROFILES["balanced"].keys())


def test_gap_points_to_underweight_equities():
    # Portfolio is mostly cash, so equities should be underweight (positive gap).
    plan = build_plan(_metrics(), "aggressive", 0.0)
    equities = next(r for r in plan.rows if r.bucket == "equities")
    assert equities.gap_usd > 0


def test_contribution_split_targets_gaps():
    plan = build_plan(_metrics(), "balanced", 1000.0)
    assert plan.contribution_split  # non-empty
    assert abs(sum(plan.contribution_split.values()) - 1000.0) < 1.0


def test_actions_always_include_emergency_fund():
    plan = build_plan(_metrics(), "conservative", 250.0)
    assert any("Emergency fund" in a for a in plan.actions)
