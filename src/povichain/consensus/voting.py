from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from ..core.types import Vote


@dataclass
class VoteTally:
    block_id: int
    accept_weight: float
    reject_weight: float
    abstain_weight: float
    accepted_ids: Tuple[int, ...]
    rejected_ids: Tuple[int, ...]


def tally_votes(block_id: int, votes: Iterable[Vote], weights: Dict[int, float]) -> VoteTally:
    accept_w = 0.0
    reject_w = 0.0
    abstain_w = 0.0
    accepted_ids = []
    rejected_ids = []
    for v in votes:
        if v.block_id != block_id:
            continue
        w = float(weights.get(v.validator_id, v.weight))
        if v.stance == "accept":
            accept_w += w
            accepted_ids.append(v.validator_id)
        elif v.stance == "reject":
            reject_w += w
            rejected_ids.append(v.validator_id)
        else:
            abstain_w += w
    return VoteTally(
        block_id=block_id,
        accept_weight=accept_w,
        reject_weight=reject_w,
        abstain_weight=abstain_w,
        accepted_ids=tuple(sorted(accepted_ids)),
        rejected_ids=tuple(sorted(rejected_ids)),
    )
