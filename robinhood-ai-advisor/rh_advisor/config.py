"""Configuration and safety flags.

All secrets come from environment variables (optionally loaded from a local
``.env`` file that is git-ignored). Nothing is hard-coded.

Two safety switches matter most:

* ``RH_ADVISOR_BROKER`` — ``demo`` (default) serves a built-in sample
  portfolio so you can try everything offline. Set to ``robinhood`` to talk
  to your real account.
* ``RH_ADVISOR_ALLOW_LIVE_TRADES`` — must be the literal string ``yes`` for
  any order to actually be submitted. When it is anything else (the default),
  the trading layer runs in dry-run mode: it will still *propose* and
  *confirm* orders, but submission is simulated. This is the seatbelt.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency).

    Looks for a ``.env`` next to the project root and populates os.environ
    for any keys not already set. Intentionally tiny: ``KEY=value`` lines,
    ``#`` comments, and surrounding quotes are handled; everything else is
    left alone.
    """
    here = Path(__file__).resolve().parent.parent  # robinhood-ai-advisor/
    env_path = here / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings."""

    broker: str = "demo"
    rh_username: str | None = None
    rh_password: str | None = None
    rh_mfa_secret: str | None = None  # TOTP base32 secret for headless 2FA
    allow_live_trades: bool = False
    default_risk_profile: str = "balanced"
    default_monthly_contribution: float = 0.0
    # Per-order ceiling. Even when live trading is enabled, a single proposal
    # above this dollar amount is refused and must be split or raised
    # deliberately. A small, sane guardrail against fat-finger mistakes.
    max_order_usd: float = 2000.0

    @property
    def live_trading_armed(self) -> bool:
        """True only when the broker is real AND live trades are allowed."""
        return self.broker == "robinhood" and self.allow_live_trades


def load_settings() -> Settings:
    """Build a Settings object from the environment (+ optional .env)."""
    _load_dotenv()

    def _float(name: str, default: float) -> float:
        try:
            return float(os.environ.get(name, default))
        except (TypeError, ValueError):
            return default

    return Settings(
        broker=os.environ.get("RH_ADVISOR_BROKER", "demo").strip().lower(),
        rh_username=os.environ.get("RH_USERNAME") or None,
        rh_password=os.environ.get("RH_PASSWORD") or None,
        rh_mfa_secret=os.environ.get("RH_MFA_SECRET") or None,
        allow_live_trades=_flag("RH_ADVISOR_ALLOW_LIVE_TRADES", False),
        default_risk_profile=os.environ.get(
            "RH_ADVISOR_RISK_PROFILE", "balanced"
        ).strip().lower(),
        default_monthly_contribution=_float(
            "RH_ADVISOR_MONTHLY_CONTRIBUTION", 0.0
        ),
        max_order_usd=_float("RH_ADVISOR_MAX_ORDER_USD", 2000.0),
    )
