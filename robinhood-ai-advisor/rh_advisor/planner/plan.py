"""Investment-plan generator.

Given a risk profile and a monthly contribution, produce:

* a target asset-class allocation,
* a gap analysis vs. the current portfolio, and
* a concrete, non-prescriptive action checklist (emergency fund first,
  dollar-cost averaging, rebalancing cadence).

This is an educational framework, not personalized financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..analysis.metrics import PortfolioMetrics

# Target weights across coarse asset classes for three risk profiles.
# Buckets: "equities" (stocks + equity ETFs), "bonds" (fixed income),
# "cash" (buffer / dry powder), "alt" (crypto and other speculative).
RISK_PROFILES: dict[str, dict[str, float]] = {
    "conservative": {"equities": 0.40, "bonds": 0.45, "cash": 0.12, "alt": 0.03},
    "balanced": {"equities": 0.65, "bonds": 0.25, "cash": 0.05, "alt": 0.05},
    "aggressive": {"equities": 0.85, "bonds": 0.03, "cash": 0.02, "alt": 0.10},
}

_TYPE_TO_BUCKET = {
    "stock": "equities",
    "etf": "equities",
    "crypto": "alt",
    "cash": "cash",
}


@dataclass
class AllocationRow:
    bucket: str
    current_pct: float
    target_pct: float
    current_usd: float
    target_usd: float
    gap_usd: float          # +ve = add money here, -ve = trim

    def as_dict(self) -> dict:
        return {
            "bucket": self.bucket,
            "current_pct": round(self.current_pct, 4),
            "target_pct": round(self.target_pct, 4),
            "current_usd": round(self.current_usd, 2),
            "target_usd": round(self.target_usd, 2),
            "gap_usd": round(self.gap_usd, 2),
        }


@dataclass
class InvestmentPlan:
    risk_profile: str
    monthly_contribution: float
    total_value: float
    target_allocation: dict[str, float]
    rows: list[AllocationRow] = field(default_factory=list)
    contribution_split: dict[str, float] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "risk_profile": self.risk_profile,
            "monthly_contribution": round(self.monthly_contribution, 2),
            "total_value": round(self.total_value, 2),
            "target_allocation": self.target_allocation,
            "rows": [r.as_dict() for r in self.rows],
            "contribution_split": {k: round(v, 2) for k, v in self.contribution_split.items()},
            "actions": self.actions,
        }


def _current_buckets(m: PortfolioMetrics) -> dict[str, float]:
    """Current dollar value per bucket (includes cash)."""
    buckets = {"equities": 0.0, "bonds": 0.0, "cash": m.cash, "alt": 0.0}
    for w in m.weights:
        bucket = _TYPE_TO_BUCKET.get(w.asset_type, "equities")
        buckets[bucket] += w.equity
    return buckets


def build_plan(
    m: PortfolioMetrics,
    risk_profile: str = "balanced",
    monthly_contribution: float = 0.0,
) -> InvestmentPlan:
    risk_profile = risk_profile.lower().strip()
    target = RISK_PROFILES.get(risk_profile, RISK_PROFILES["balanced"])
    total = m.total_value

    current = _current_buckets(m)
    rows: list[AllocationRow] = []
    for bucket, target_pct in target.items():
        cur_usd = current.get(bucket, 0.0)
        cur_pct = (cur_usd / total) if total > 0 else 0.0
        tgt_usd = target_pct * total
        rows.append(AllocationRow(
            bucket=bucket,
            current_pct=cur_pct,
            target_pct=target_pct,
            current_usd=cur_usd,
            target_usd=tgt_usd,
            gap_usd=tgt_usd - cur_usd,
        ))

    # Direct new monthly money preferentially at the most underweight buckets
    # (positive gaps). This rebalances by *adding* rather than selling, which
    # is usually more tax-friendly.
    split: dict[str, float] = {}
    if monthly_contribution > 0:
        underweight = {r.bucket: r.gap_usd for r in rows if r.gap_usd > 0}
        gap_total = sum(underweight.values())
        if gap_total > 0:
            for bucket, gap in underweight.items():
                split[bucket] = round(monthly_contribution * gap / gap_total, 2)
        else:
            # Already balanced — contribute along target weights.
            for bucket, pct in target.items():
                split[bucket] = round(monthly_contribution * pct, 2)

    return InvestmentPlan(
        risk_profile=risk_profile,
        monthly_contribution=monthly_contribution,
        total_value=total,
        target_allocation=target,
        rows=rows,
        contribution_split=split,
        actions=_action_checklist(m, rows, risk_profile, monthly_contribution),
    )


def _action_checklist(
    m: PortfolioMetrics,
    rows: list[AllocationRow],
    risk_profile: str,
    monthly: float,
) -> list[str]:
    actions: list[str] = []

    actions.append(
        "Emergency fund first: keep 3–6 months of expenses in cash/savings "
        "OUTSIDE this brokerage before adding risk."
    )

    if monthly > 0:
        actions.append(
            f"Automate a ${monthly:,.0f}/month dollar-cost-averaging contribution so "
            f"you invest on a schedule instead of timing the market."
        )

    # Largest underweight bucket gets a concrete nudge.
    underweight = sorted([r for r in rows if r.gap_usd > 0], key=lambda r: r.gap_usd, reverse=True)
    if underweight:
        top = underweight[0]
        label = {
            "equities": "a broad equity index ETF",
            "bonds": "a bond/fixed-income ETF",
            "cash": "your cash buffer",
            "alt": "your speculative sleeve (size it small)",
        }.get(top.bucket, top.bucket)
        actions.append(
            f"Biggest gap vs. your {risk_profile} target is {top.bucket} "
            f"(~${top.gap_usd:,.0f} light). New contributions toward {label} would "
            f"close it without selling."
        )

    overweight = sorted([r for r in rows if r.gap_usd < -1], key=lambda r: r.gap_usd)
    if overweight:
        top = overweight[0]
        actions.append(
            f"{top.bucket.title()} is ~${abs(top.gap_usd):,.0f} over target. You can "
            f"let new money into other buckets bring it back in line, or trim if you "
            f"prefer to rebalance actively (mind taxes on gains)."
        )

    if m.top_holding_pct >= 0.25:
        actions.append(
            f"Single-name risk: {m.top_holding_symbol} is {m.top_holding_pct:.0%} of the "
            f"account. Decide on a personal cap (e.g., 10%) and rebalance toward it over time."
        )

    actions.append(
        "Rebalance on a cadence (e.g., quarterly or when a bucket drifts >5% off "
        "target) rather than reacting to headlines."
    )
    actions.append(
        "Review this plan whenever your goals, income, or risk tolerance change — "
        "at least once a year."
    )
    return actions
