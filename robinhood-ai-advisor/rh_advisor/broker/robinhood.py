"""Robinhood backend built on the community ``robin_stocks`` library.

IMPORTANT CONTEXT
-----------------
Robinhood has no official public API. ``robin_stocks`` automates the private
mobile/web API and logs in with your real credentials. It is widely used and
great for *reading* your portfolio, but because it is unofficial there is some
breakage and account risk. Read DISCLAIMER.md before using live mode.

This module is import-safe even when ``robin_stocks`` is not installed: the
dependency is imported lazily inside methods, so the rest of the package (and
the demo broker) keeps working.
"""

from __future__ import annotations

from ..config import Settings
from .base import Broker, OrderRequest, OrderResult, Portfolio, Position


class RobinhoodError(RuntimeError):
    pass


class RobinhoodBroker(Broker):
    read_only = False

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._rh = None
        self._sector_cache: dict[str, str] = {}

    # ----- auth -------------------------------------------------------------
    def _client(self):
        """Import robin_stocks and log in once (cached for the process)."""
        if self._rh is not None:
            return self._rh
        try:
            import robin_stocks.robinhood as rh  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RobinhoodError(
                "robin_stocks is not installed. Run: pip install robin_stocks pyotp"
            ) from exc

        if not self.settings.rh_username or not self.settings.rh_password:
            raise RobinhoodError(
                "RH_USERNAME / RH_PASSWORD are not set. Add them to your .env."
            )

        mfa_code = None
        if self.settings.rh_mfa_secret:
            try:
                import pyotp  # type: ignore

                mfa_code = pyotp.TOTP(self.settings.rh_mfa_secret).now()
            except ImportError as exc:  # pragma: no cover
                raise RobinhoodError(
                    "RH_MFA_SECRET is set but pyotp is not installed. Run: pip install pyotp"
                ) from exc

        rh.login(
            username=self.settings.rh_username,
            password=self.settings.rh_password,
            mfa_code=mfa_code,
            store_session=True,
        )
        self._rh = rh
        return rh

    # ----- reads ------------------------------------------------------------
    def get_portfolio(self) -> Portfolio:
        rh = self._client()
        positions: list[Position] = []

        holdings = rh.build_holdings() or {}
        for symbol, h in holdings.items():
            asset_type = "etf" if str(h.get("type", "")).lower() in {"etp", "etf"} else "stock"
            positions.append(
                Position(
                    symbol=symbol,
                    quantity=_f(h.get("quantity")),
                    price=_f(h.get("price")),
                    average_buy_price=_f(h.get("average_buy_price")),
                    name=h.get("name", symbol),
                    asset_type=asset_type,
                    sector=self._sector(rh, symbol),
                )
            )

        # Crypto positions are a separate endpoint.
        try:
            for c in rh.crypto.get_crypto_positions() or []:
                qty = _f(c.get("quantity"))
                if qty <= 0:
                    continue
                code = c.get("currency", {}).get("code", "?")
                quote = rh.crypto.get_crypto_quote(code) or {}
                price = _f(quote.get("mark_price"))
                cost = _f(c.get("cost_bases", [{}])[0].get("direct_cost_basis")) if c.get("cost_bases") else 0.0
                avg = (cost / qty) if qty else 0.0
                positions.append(
                    Position(symbol=code, quantity=qty, price=price,
                             average_buy_price=avg, name=code,
                             asset_type="crypto", sector="Crypto")
                )
        except Exception:  # pragma: no cover - crypto is best-effort
            pass

        cash = 0.0
        try:
            acct = rh.profiles.load_account_profile() or {}
            cash = _f(acct.get("portfolio_cash") or acct.get("cash"))
        except Exception:  # pragma: no cover
            pass

        return Portfolio(positions=positions, cash=cash, account_label="Robinhood")

    def get_quote(self, symbol: str, asset_type: str = "stock") -> float:
        rh = self._client()
        if asset_type == "crypto":
            q = rh.crypto.get_crypto_quote(symbol) or {}
            return _f(q.get("mark_price"))
        price = rh.stocks.get_latest_price(symbol)
        return _f(price[0]) if price else 0.0

    def _sector(self, rh, symbol: str) -> str:
        if symbol in self._sector_cache:
            return self._sector_cache[symbol]
        sector = "Unknown"
        try:
            fund = rh.stocks.get_fundamentals(symbol)
            if fund and fund[0]:
                sector = fund[0].get("sector") or "Unknown"
        except Exception:  # pragma: no cover
            pass
        self._sector_cache[symbol] = sector
        return sector

    # ----- writes -----------------------------------------------------------
    def submit_order(self, order: OrderRequest) -> OrderResult:
        # Hard seatbelt: never submit unless live trading is explicitly armed.
        if not self.settings.live_trading_armed:
            return OrderResult(
                accepted=False,
                dry_run=True,
                detail=(
                    "Live trading is NOT armed. Simulated only. "
                    "Set RH_ADVISOR_ALLOW_LIVE_TRADES=yes to enable real orders."
                ),
            )

        rh = self._client()
        side = order.side.lower()
        try:
            if order.asset_type == "crypto":
                if side == "buy":
                    res = rh.orders.order_buy_crypto_by_price(order.symbol, order.amount_usd)
                else:
                    res = rh.orders.order_sell_crypto_by_price(order.symbol, order.amount_usd)
            elif order.amount_usd is not None:
                if side == "buy":
                    res = rh.orders.order_buy_fractional_by_price(order.symbol, order.amount_usd)
                else:
                    res = rh.orders.order_sell_fractional_by_price(order.symbol, order.amount_usd)
            else:
                if side == "buy":
                    res = rh.orders.order_buy_market(order.symbol, order.quantity)
                else:
                    res = rh.orders.order_sell_market(order.symbol, order.quantity)
        except Exception as exc:  # pragma: no cover - depends on live API
            return OrderResult(accepted=False, dry_run=False,
                               detail=f"Broker rejected order: {exc}")

        order_id = (res or {}).get("id")
        accepted = bool(order_id) and "detail" not in (res or {})
        return OrderResult(
            accepted=accepted,
            dry_run=False,
            broker_order_id=order_id,
            detail=(res or {}).get("detail", "submitted"),
            raw=res,
        )


def _f(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
