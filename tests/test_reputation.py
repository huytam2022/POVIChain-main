import math

from povichain.consensus.reputation import (
    ReputationLedger,
    ReputationParams,
    effective_reputation,
    update_reputation,
)


def _params() -> ReputationParams:
    return ReputationParams(
        alpha=0.7,
        beta=0.15,
        gamma=0.10,
        lambd=0.05,
        delta=0.25,
        eta=0.02,
        mu=0.10,
        r_min=0.05,
    )


def test_effective_reputation_formula_is_exact():
    r_current = 1.2
    stake = 10.0
    delta = 0.25
    expected = delta * math.log(1.0 + stake) + (1.0 - delta) * r_current
    assert abs(effective_reputation(r_current, stake, delta) - expected) < 1e-12


def test_update_reputation_formula_is_exact():
    p = _params()
    r = 2.0
    next_r = update_reputation(r, 0.5, -0.2, 0.1, 1.0, p)
    expected = (
        (1.0 - p.eta) * r
        + p.alpha * 0.5
        + p.beta * (-0.2)
        - p.lambd * 0.1
        - p.mu * 1.0
    )
    assert abs(next_r - expected) < 1e-12


def test_ledger_apply_round_monotonic_decay_without_positive_signal():
    p = _params()
    ledger = ReputationLedger(params=p)
    ledger.register(0, stake=2.0, initial_r=1.0)
    ledger.apply_round({0: 0.0}, {0: 0.0})
    assert ledger.reputations[0] == (1.0 - p.eta) * 1.0


def test_negative_reputations_clip_at_zero():
    p = _params()
    ledger = ReputationLedger(params=p)
    ledger.register(0, stake=0.0, initial_r=0.1)
    ledger.apply_penalty(0, amount=100.0)
    ledger.apply_round({0: 0.0}, {0: 0.0})
    assert ledger.reputations[0] >= 0.0
