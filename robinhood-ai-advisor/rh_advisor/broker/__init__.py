"""Broker abstraction layer.

``get_broker(settings)`` returns the right implementation:

* ``DemoBroker``  — offline sample data, no credentials, read-only.
* ``RobinhoodBroker`` — talks to a real account via the community
  ``robin_stocks`` library (lazy-imported so the package works without it).
"""

from __future__ import annotations

from ..config import Settings
from .base import Broker, Portfolio, Position


def get_broker(settings: Settings) -> Broker:
    if settings.broker == "robinhood":
        from .robinhood import RobinhoodBroker

        return RobinhoodBroker(settings)
    from .demo import DemoBroker

    return DemoBroker()


__all__ = ["Broker", "Portfolio", "Position", "get_broker"]
