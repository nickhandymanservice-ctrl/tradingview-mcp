"""Tests for the suggest-then-confirm trade flow using the demo broker."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from rh_advisor.broker.demo import DemoBroker
from rh_advisor.config import Settings
from rh_advisor.trading import confirm_order, get_pending_proposal, propose_order
from rh_advisor.trading.orders import TradeError, _STATE_FILE


@pytest.fixture(autouse=True)
def clean_state():
    _STATE_FILE.unlink(missing_ok=True)
    yield
    _STATE_FILE.unlink(missing_ok=True)


def _settings(**kw):
    return Settings(broker="demo", **kw)


def test_propose_does_not_submit_and_creates_token():
    proposal = propose_order(DemoBroker(), _settings(), symbol="VOO", side="buy", amount_usd=200)
    assert proposal.token
    assert get_pending_proposal() is not None
    # Demo broker is read-only -> proposal must be flagged dry-run/simulated.
    assert any("read-only" in w or "DRY-RUN" in w for w in proposal.warnings)


def test_requires_exactly_one_of_amount_or_quantity():
    with pytest.raises(TradeError):
        propose_order(DemoBroker(), _settings(), symbol="VOO", side="buy")
    with pytest.raises(TradeError):
        propose_order(DemoBroker(), _settings(), symbol="VOO", side="buy", amount_usd=10, quantity=1)


def test_bad_token_rejected():
    propose_order(DemoBroker(), _settings(), symbol="VOO", side="buy", amount_usd=200)
    with pytest.raises(TradeError):
        confirm_order(DemoBroker(), _settings(), "deadbeef")


def test_confirm_consumes_proposal_once():
    proposal = propose_order(DemoBroker(), _settings(), symbol="VOO", side="buy", amount_usd=200)
    result = confirm_order(DemoBroker(), _settings(), proposal.token)
    assert result.dry_run is True
    assert result.accepted is False  # demo never really submits
    # Token cannot be replayed.
    assert get_pending_proposal() is None
    with pytest.raises(TradeError):
        confirm_order(DemoBroker(), _settings(), proposal.token)


def test_over_cap_warns():
    proposal = propose_order(DemoBroker(), _settings(max_order_usd=100.0),
                             symbol="VOO", side="buy", amount_usd=500)
    assert any("safety cap" in w for w in proposal.warnings)
