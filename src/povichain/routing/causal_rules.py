from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..core.errors import DispatcherError
from ..core.types import TxId, ZoneId


@dataclass(frozen=True)
class CausalViolation:
    tx_id: TxId
    expected_zone: ZoneId
    attempted_zone: ZoneId
    reason: str


@dataclass
class CausalRules:
    required_predecessors: Dict[TxId, Tuple[TxId, ...]] = field(default_factory=dict)
    observed_finalized: Dict[TxId, ZoneId] = field(default_factory=dict)
    violations: List[CausalViolation] = field(default_factory=list)

    def declare_predecessors(self, tx_id: TxId, predecessors: Tuple[TxId, ...]) -> None:
        self.required_predecessors[tx_id] = tuple(predecessors)

    def mark_finalized(self, tx_id: TxId, zone_id: ZoneId) -> None:
        self.observed_finalized[tx_id] = zone_id

    def check_dispatch(self, tx_id: TxId, zone_id: ZoneId) -> bool:
        preds = self.required_predecessors.get(tx_id, ())
        for p in preds:
            if p not in self.observed_finalized:
                violation = CausalViolation(tx_id, zone_id, zone_id, "predecessor_unfinalized:" + str(p))
                self.violations.append(violation)
                return False
        return True

    def forbid_reroute(self, tx_id: TxId, committed_zone: ZoneId, attempted_zone: ZoneId) -> None:
        if committed_zone != attempted_zone:
            self.violations.append(
                CausalViolation(tx_id, committed_zone, attempted_zone, "reroute_ex_post_forbidden")
            )
            raise DispatcherError("reroute_ex_post_forbidden")
