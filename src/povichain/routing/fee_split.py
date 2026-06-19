from dataclasses import dataclass
from typing import Tuple

from ..core.errors import DispatcherError
from .smart_zone import SmartZone


@dataclass(frozen=True)
class FeeSplitPolicy:
    validator_floor: float = 0.0
    protocol_floor: float = 0.0
    treasury_floor: float = 0.0


@dataclass(frozen=True)
class FeeBreakdown:
    validator: float
    protocol: float
    treasury: float
    total: float


def apply_fee_split(zone: SmartZone, gross_fee: float, policy: FeeSplitPolicy = FeeSplitPolicy()) -> FeeBreakdown:
    total_share = zone.validator_share + zone.protocol_share + zone.treasury_share
    if abs(total_share - 1.0) > 1e-9:
        raise DispatcherError("fee_shares_must_sum_to_one")
    v = gross_fee * zone.validator_share
    p = gross_fee * zone.protocol_share
    t = gross_fee * zone.treasury_share
    if v < policy.validator_floor or p < policy.protocol_floor or t < policy.treasury_floor:
        raise DispatcherError("fee_split_floor_violation")
    return FeeBreakdown(validator=v, protocol=p, treasury=t, total=gross_fee)
