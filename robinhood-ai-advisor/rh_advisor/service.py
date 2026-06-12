"""High-level service facade.

One place that wires the broker, metrics, tips, planner, and trading flow
together and returns plain dicts. The CLI, the web API, and the MCP server all
call into here so behavior stays identical across surfaces.
"""

from __future__ import annotations

from .analysis import compute_metrics, generate_tips
from .broker import get_broker
from .config import Settings, load_settings
from .planner import build_plan
from .trading import confirm_order, get_pending_proposal, propose_order


class Advisor:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.broker = get_broker(self.settings)

    # ----- reads ------------------------------------------------------------
    def portfolio(self) -> dict:
        p = self.broker.get_portfolio()
        return {
            "account_label": p.account_label,
            "broker": self.settings.broker,
            "live_trading_armed": self.settings.live_trading_armed,
            "total_value": round(p.total_value, 2),
            "cash": round(p.cash, 2),
            "positions": [
                {
                    "symbol": pos.symbol,
                    "name": pos.name,
                    "asset_type": pos.asset_type,
                    "sector": pos.sector,
                    "quantity": pos.quantity,
                    "price": round(pos.price, 2),
                    "equity": round(pos.equity, 2),
                    "average_buy_price": round(pos.average_buy_price, 2),
                    "unrealized_gain": round(pos.unrealized_gain, 2),
                    "unrealized_gain_pct": round(pos.unrealized_gain_pct, 4),
                }
                for pos in sorted(p.positions, key=lambda x: x.equity, reverse=True)
            ],
        }

    def metrics(self) -> dict:
        return compute_metrics(self.broker.get_portfolio()).as_dict()

    def tips(self) -> list[dict]:
        m = compute_metrics(self.broker.get_portfolio())
        return [t.as_dict() for t in generate_tips(m)]

    def plan(self, risk_profile: str | None = None, monthly_contribution: float | None = None) -> dict:
        m = compute_metrics(self.broker.get_portfolio())
        plan = build_plan(
            m,
            risk_profile or self.settings.default_risk_profile,
            monthly_contribution if monthly_contribution is not None
            else self.settings.default_monthly_contribution,
        )
        return plan.as_dict()

    # ----- trading ----------------------------------------------------------
    def propose_trade(
        self,
        symbol: str,
        side: str,
        amount_usd: float | None = None,
        quantity: float | None = None,
        asset_type: str = "stock",
    ) -> dict:
        proposal = propose_order(
            self.broker, self.settings,
            symbol=symbol, side=side,
            amount_usd=amount_usd, quantity=quantity, asset_type=asset_type,
        )
        return proposal.as_dict()

    def confirm_trade(self, token: str) -> dict:
        result = confirm_order(self.broker, self.settings, token)
        return {
            "accepted": result.accepted,
            "dry_run": result.dry_run,
            "detail": result.detail,
            "broker_order_id": result.broker_order_id,
        }

    def pending_trade(self) -> dict | None:
        proposal = get_pending_proposal()
        return proposal.as_dict() if proposal else None
