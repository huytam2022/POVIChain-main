from dataclasses import dataclass
from typing import Tuple

from .voting import VoteTally


@dataclass(frozen=True)
class FinalizationPolicy:
    quorum_ratio: float
    min_committee_size: int


@dataclass(frozen=True)
class FinalizationDecision:
    block_id: int
    finalized: bool
    reason: str
    accept_ratio: float


def finalize_block(
    tally: VoteTally,
    committee_size: int,
    policy: FinalizationPolicy,
) -> FinalizationDecision:
    total_w = tally.accept_weight + tally.reject_weight + tally.abstain_weight
    if committee_size < policy.min_committee_size:
        return FinalizationDecision(tally.block_id, False, "committee_too_small", 0.0)
    if total_w <= 0.0:
        return FinalizationDecision(tally.block_id, False, "no_votes", 0.0)
    ratio = tally.accept_weight / total_w
    if ratio >= policy.quorum_ratio:
        return FinalizationDecision(tally.block_id, True, "quorum_reached", ratio)
    return FinalizationDecision(tally.block_id, False, "below_quorum", ratio)
