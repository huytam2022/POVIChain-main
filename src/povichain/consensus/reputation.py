import math
from dataclasses import dataclass, field
from typing import Dict, Tuple

from ..core.types import ValidatorId


@dataclass(frozen=True)
class ReputationParams:
    alpha: float
    beta: float
    gamma: float
    lambd: float
    delta: float
    eta: float
    mu: float
    r_min: float


def effective_reputation(r_current: float, stake: float, delta: float) -> float:
    return delta * math.log(1.0 + max(0.0, stake)) + (1.0 - delta) * max(0.0, r_current)


def update_reputation(
    r_current: float,
    delta_availability: float,
    delta_voting: float,
    penalty: float,
    collusion_flag: float,
    params: ReputationParams,
) -> float:
    next_r = (
        (1.0 - params.eta) * r_current
        + params.alpha * delta_availability
        + params.beta * delta_voting
        - params.lambd * penalty
        - params.mu * collusion_flag
    )
    if next_r < 0.0:
        next_r = 0.0
    return next_r


@dataclass
class ReputationLedger:
    params: ReputationParams
    stakes: Dict[ValidatorId, float] = field(default_factory=dict)
    reputations: Dict[ValidatorId, float] = field(default_factory=dict)
    penalties: Dict[ValidatorId, float] = field(default_factory=dict)
    collusion_flags: Dict[ValidatorId, float] = field(default_factory=dict)

    def register(self, validator_id: ValidatorId, stake: float, initial_r: float) -> None:
        self.stakes[validator_id] = float(stake)
        self.reputations[validator_id] = float(initial_r)
        self.penalties[validator_id] = 0.0
        self.collusion_flags[validator_id] = 0.0

    def apply_penalty(self, validator_id: ValidatorId, amount: float) -> None:
        self.penalties[validator_id] = self.penalties.get(validator_id, 0.0) + float(amount)

    def set_collusion(self, validator_id: ValidatorId, flag: float) -> None:
        self.collusion_flags[validator_id] = float(flag)

    def apply_round(
        self,
        deltas_availability: Dict[ValidatorId, float],
        deltas_voting: Dict[ValidatorId, float],
    ) -> None:
        for vid, r in list(self.reputations.items()):
            da = float(deltas_availability.get(vid, 0.0))
            dv = float(deltas_voting.get(vid, 0.0))
            pen = float(self.penalties.get(vid, 0.0))
            coll = float(self.collusion_flags.get(vid, 0.0))
            self.reputations[vid] = update_reputation(r, da, dv, pen, coll, self.params)
            self.penalties[vid] = 0.0

    def effective_map(self) -> Dict[ValidatorId, float]:
        out: Dict[ValidatorId, float] = {}
        for vid, r in self.reputations.items():
            s = float(self.stakes.get(vid, 0.0))
            out[vid] = effective_reputation(r, s, self.params.delta)
        return out

    def snapshot(self) -> Tuple[Dict[ValidatorId, float], Dict[ValidatorId, float]]:
        return dict(self.reputations), self.effective_map()
