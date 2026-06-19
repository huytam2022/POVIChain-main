from dataclasses import dataclass
from typing import Dict, Tuple

from ..core.types import CommitteeRecord, ValidatorId
from ..crypto.vrf import vrf_fraction, vrf_seed


L_BITS_DEFAULT = 256


def _public_key_for(vid: ValidatorId) -> bytes:
    return ("pk|" + str(vid)).encode("utf-8")


def select_committee(
    epoch: int,
    prev_block_id_bytes: bytes,
    randao: bytes,
    effective_reputations: Dict[ValidatorId, float],
    theta: float,
    r_min: float,
    l_bits: int = L_BITS_DEFAULT,
) -> CommitteeRecord:
    seed = vrf_seed(prev_block_id_bytes, randao)
    total = 0.0
    for vid, r in effective_reputations.items():
        if r >= r_min:
            total += float(r)
    members = []
    if total > 0.0:
        for vid in sorted(effective_reputations.keys()):
            r = float(effective_reputations[vid])
            if r < r_min:
                continue
            frac = vrf_fraction(seed, _public_key_for(vid), l_bits=l_bits)
            threshold = theta * (r / total)
            if frac < threshold:
                members.append(vid)
    return CommitteeRecord(
        epoch=epoch,
        seed=seed,
        threshold_theta=float(theta),
        members=tuple(members),
        r_min=float(r_min),
    )


@dataclass
class CommitteeSelector:
    theta: float
    r_min: float
    l_bits: int = L_BITS_DEFAULT

    def select(
        self,
        epoch: int,
        prev_block_id: int,
        randao: bytes,
        effective_reputations: Dict[ValidatorId, float],
    ) -> CommitteeRecord:
        prev_bytes = prev_block_id.to_bytes(8, "big", signed=False)
        return select_committee(
            epoch,
            prev_bytes,
            randao,
            effective_reputations,
            self.theta,
            self.r_min,
            self.l_bits,
        )
