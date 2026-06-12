"""Deterministic portfolio metrics.

Pure functions over a ``Portfolio`` snapshot — no network, no randomness — so
the numbers are reproducible and easy to unit-test. These feed both the rules
engine (``tips.py``) and the planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..broker.base import Portfolio


@dataclass
class Weight:
    symbol: str
    name: str
    equity: float
    weight: float            # fraction of total account value (incl. cash)
    unrealized_gain_pct: float
    asset_type: str
    sector: str


@dataclass
class PortfolioMetrics:
    total_value: float
    invested_equity: float
    cash: float
    cash_pct: float
    num_positions: int
    weights: list[Weight] = field(default_factory=list)
    top_holding_pct: float = 0.0
    top_holding_symbol: str = ""
    # Herfindahl-Hirschman Index over invested weights (0..1). Higher = more
    # concentrated. ~0.15 is reasonably diversified; >0.25 is concentrated.
    concentration_hhi: float = 0.0
    sector_allocation: dict[str, float] = field(default_factory=dict)
    asset_type_allocation: dict[str, float] = field(default_factory=dict)
    crypto_pct: float = 0.0
    total_unrealized_gain: float = 0.0
    total_unrealized_gain_pct: float = 0.0
    # 0..100 convenience score derived from concentration + breadth + cash.
    diversification_score: float = 0.0

    def as_dict(self) -> dict:
        return {
            "total_value": round(self.total_value, 2),
            "invested_equity": round(self.invested_equity, 2),
            "cash": round(self.cash, 2),
            "cash_pct": round(self.cash_pct, 4),
            "num_positions": self.num_positions,
            "top_holding_symbol": self.top_holding_symbol,
            "top_holding_pct": round(self.top_holding_pct, 4),
            "concentration_hhi": round(self.concentration_hhi, 4),
            "crypto_pct": round(self.crypto_pct, 4),
            "sector_allocation": {k: round(v, 4) for k, v in self.sector_allocation.items()},
            "asset_type_allocation": {k: round(v, 4) for k, v in self.asset_type_allocation.items()},
            "total_unrealized_gain": round(self.total_unrealized_gain, 2),
            "total_unrealized_gain_pct": round(self.total_unrealized_gain_pct, 4),
            "diversification_score": round(self.diversification_score, 1),
            "weights": [
                {
                    "symbol": w.symbol,
                    "name": w.name,
                    "equity": round(w.equity, 2),
                    "weight": round(w.weight, 4),
                    "unrealized_gain_pct": round(w.unrealized_gain_pct, 4),
                    "asset_type": w.asset_type,
                    "sector": w.sector,
                }
                for w in self.weights
            ],
        }


def compute_metrics(portfolio: Portfolio) -> PortfolioMetrics:
    total = portfolio.total_value
    invested = portfolio.invested_equity
    cash = portfolio.cash

    weights: list[Weight] = []
    for p in portfolio.positions:
        weights.append(
            Weight(
                symbol=p.symbol,
                name=p.name or p.symbol,
                equity=p.equity,
                weight=(p.equity / total) if total > 0 else 0.0,
                unrealized_gain_pct=p.unrealized_gain_pct,
                asset_type=p.asset_type,
                sector=p.sector,
            )
        )
    weights.sort(key=lambda w: w.equity, reverse=True)

    # HHI over *invested* weights (cash excluded) so an all-cash account does
    # not look artificially diversified.
    hhi = 0.0
    if invested > 0:
        for p in portfolio.positions:
            share = p.equity / invested
            hhi += share * share

    sector_alloc: dict[str, float] = {}
    type_alloc: dict[str, float] = {}
    for p in portfolio.positions:
        if invested > 0:
            sector_alloc[p.sector] = sector_alloc.get(p.sector, 0.0) + p.equity / invested
            type_alloc[p.asset_type] = type_alloc.get(p.asset_type, 0.0) + p.equity / invested

    crypto_pct = sum(p.equity for p in portfolio.positions if p.asset_type == "crypto")
    crypto_pct = (crypto_pct / total) if total > 0 else 0.0

    top = weights[0] if weights else None
    cost_basis = portfolio.total_cost_basis
    gain = portfolio.total_unrealized_gain
    gain_pct = (gain / cost_basis) if cost_basis > 0 else 0.0

    return PortfolioMetrics(
        total_value=total,
        invested_equity=invested,
        cash=cash,
        cash_pct=(cash / total) if total > 0 else 0.0,
        num_positions=len(portfolio.positions),
        weights=weights,
        top_holding_pct=top.weight if top else 0.0,
        top_holding_symbol=top.symbol if top else "",
        concentration_hhi=hhi,
        sector_allocation=dict(sorted(sector_alloc.items(), key=lambda kv: kv[1], reverse=True)),
        asset_type_allocation=dict(sorted(type_alloc.items(), key=lambda kv: kv[1], reverse=True)),
        crypto_pct=crypto_pct,
        total_unrealized_gain=gain,
        total_unrealized_gain_pct=gain_pct,
        diversification_score=_diversification_score(hhi, len(portfolio.positions), invested),
    )


def _diversification_score(hhi: float, n: int, invested: float) -> float:
    """Map concentration + breadth onto a friendly 0..100 score."""
    if invested <= 0 or n == 0:
        return 0.0
    # Lower HHI is better. HHI for n equal holdings is 1/n.
    concentration_component = max(0.0, 1.0 - hhi) * 70.0
    breadth_component = min(n, 15) / 15.0 * 30.0
    return round(concentration_component + breadth_component, 1)
