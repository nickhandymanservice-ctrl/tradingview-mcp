"""Suggest-then-confirm order flow.

The whole point of this module: **no order is ever submitted in a single
step.** You first ``propose_order(...)`` which validates and returns a summary
plus a one-time confirmation token. Only a subsequent ``confirm_order(token)``
will reach the broker — and even then only if live trading is armed.

The pending proposal is persisted to a small git-ignored JSON file so the flow
works across processes (e.g., propose in the web UI, confirm in the CLI, or
both driven by Claude over MCP). Proposals expire quickly.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ..broker.base import Broker, OrderRequest, OrderResult
from ..config import Settings

_STATE_FILE = Path(__file__).resolve().parent.parent.parent / ".rh_advisor_state.json"
_PROPOSAL_TTL_SECONDS = 300  # proposals are valid for 5 minutes


@dataclass
class OrderProposal:
    token: str
    symbol: str
    side: str
    asset_type: str
    amount_usd: float | None
    quantity: float | None
    est_price: float
    est_quantity: float
    est_value: float
    created_at: float
    expires_at: float
    live: bool                 # would this actually hit the broker on confirm?
    summary: str
    warnings: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


class TradeError(ValueError):
    pass


def _write_state(proposal: OrderProposal | None) -> None:
    if proposal is None:
        _STATE_FILE.unlink(missing_ok=True)
        return
    _STATE_FILE.write_text(json.dumps({"proposal": proposal.as_dict()}, indent=2), encoding="utf-8")


def _read_state() -> OrderProposal | None:
    if not _STATE_FILE.exists():
        return None
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return OrderProposal(**data["proposal"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def get_pending_proposal() -> OrderProposal | None:
    """Return the current pending proposal if it exists and hasn't expired."""
    proposal = _read_state()
    if proposal is None:
        return None
    if proposal.expires_at < time.time():
        _write_state(None)
        return None
    return proposal


def propose_order(
    broker: Broker,
    settings: Settings,
    *,
    symbol: str,
    side: str,
    amount_usd: float | None = None,
    quantity: float | None = None,
    asset_type: str = "stock",
) -> OrderProposal:
    """Validate a desired trade and stage it for confirmation. Submits nothing."""
    side = side.lower().strip()
    symbol = symbol.upper().strip()
    if side not in {"buy", "sell"}:
        raise TradeError("side must be 'buy' or 'sell'")
    if (amount_usd is None) == (quantity is None):
        raise TradeError("provide exactly one of amount_usd or quantity")
    if amount_usd is not None and amount_usd <= 0:
        raise TradeError("amount_usd must be positive")
    if quantity is not None and quantity <= 0:
        raise TradeError("quantity must be positive")

    warnings: list[str] = []

    price = broker.get_quote(symbol, asset_type)
    if price <= 0:
        warnings.append(f"Could not fetch a live price for {symbol}; estimates may be off.")

    if amount_usd is not None:
        est_value = amount_usd
        est_quantity = (amount_usd / price) if price > 0 else 0.0
    else:
        est_quantity = quantity or 0.0
        est_value = est_quantity * price

    # Guardrail: per-order ceiling.
    if est_value > settings.max_order_usd:
        warnings.append(
            f"Order value ${est_value:,.2f} exceeds the per-order safety cap of "
            f"${settings.max_order_usd:,.2f}. Lower the amount or raise "
            f"RH_ADVISOR_MAX_ORDER_USD deliberately."
        )

    # Affordability / holdings sanity check against the current snapshot.
    try:
        portfolio = broker.get_portfolio()
        if side == "buy" and est_value > portfolio.cash:
            warnings.append(
                f"Estimated cost ${est_value:,.2f} is more than your cash "
                f"(${portfolio.cash:,.2f}). Robinhood may reject or use margin."
            )
        if side == "sell":
            held = next((p.quantity for p in portfolio.positions if p.symbol == symbol), 0.0)
            if est_quantity > held + 1e-9:
                warnings.append(
                    f"You appear to hold {held:g} {symbol}, fewer than the {est_quantity:g} "
                    f"you're trying to sell."
                )
    except Exception:  # pragma: no cover - portfolio read is best-effort here
        pass

    live = settings.live_trading_armed
    if not live:
        warnings.append("DRY-RUN: live trading is not armed, so confirming will only simulate.")
    if getattr(broker, "read_only", False):
        warnings.append("This broker is read-only (demo); confirming will not place a real order.")

    now = time.time()
    token = secrets.token_hex(4)
    order_kind = (
        f"${amount_usd:,.2f}" if amount_usd is not None else f"{quantity:g} share(s)"
    )
    summary = (
        f"{side.upper()} {order_kind} of {symbol} "
        f"(~{est_quantity:.4g} @ ${price:,.2f} ≈ ${est_value:,.2f}). "
        f"{'LIVE' if live else 'DRY-RUN'}. Confirm with token {token}."
    )

    proposal = OrderProposal(
        token=token,
        symbol=symbol,
        side=side,
        asset_type=asset_type,
        amount_usd=amount_usd,
        quantity=quantity,
        est_price=price,
        est_quantity=est_quantity,
        est_value=est_value,
        created_at=now,
        expires_at=now + _PROPOSAL_TTL_SECONDS,
        live=live,
        summary=summary,
        warnings=warnings,
    )
    _write_state(proposal)
    return proposal


def confirm_order(broker: Broker, settings: Settings, token: str) -> OrderResult:
    """Execute a previously proposed order, identified by its token."""
    proposal = get_pending_proposal()
    if proposal is None:
        raise TradeError("No pending proposal (it may have expired). Propose again.")
    if token.strip() != proposal.token:
        raise TradeError("Confirmation token does not match the pending proposal.")

    # Consume the proposal up front so a token can never be replayed.
    _write_state(None)

    order = OrderRequest(
        symbol=proposal.symbol,
        side=proposal.side,
        amount_usd=proposal.amount_usd,
        quantity=proposal.quantity,
        asset_type=proposal.asset_type,
    )
    return broker.submit_order(order)
