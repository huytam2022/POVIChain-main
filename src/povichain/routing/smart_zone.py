from dataclasses import dataclass, field
from typing import Dict, Tuple

from ..core.errors import DispatcherError
from ..core.types import ZoneId


@dataclass(frozen=True)
class SmartZone:
    zone_id: ZoneId
    fee_weight: float
    base_fee: float
    validator_share: float
    protocol_share: float
    treasury_share: float


def default_zones() -> Dict[ZoneId, SmartZone]:
    return {
        "identity": SmartZone("identity", 1.0, 1.0, 0.6, 0.3, 0.1),
        "finance": SmartZone("finance", 1.0, 1.5, 0.6, 0.3, 0.1),
        "traffic": SmartZone("traffic", 1.0, 0.8, 0.6, 0.3, 0.1),
        "energy": SmartZone("energy", 1.0, 0.8, 0.6, 0.3, 0.1),
        "environment": SmartZone("environment", 1.0, 0.8, 0.6, 0.3, 0.1),
        "governance": SmartZone("governance", 1.0, 1.2, 0.6, 0.3, 0.1),
    }


@dataclass
class SmartZoneRegistry:
    zones: Dict[ZoneId, SmartZone] = field(default_factory=default_zones)

    def contains(self, zone_id: ZoneId) -> bool:
        return zone_id in self.zones

    def get(self, zone_id: ZoneId) -> SmartZone:
        if zone_id not in self.zones:
            raise DispatcherError("unknown_zone:" + zone_id)
        return self.zones[zone_id]

    def known_zones(self) -> Tuple[ZoneId, ...]:
        return tuple(sorted(self.zones.keys()))
