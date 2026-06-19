from dataclasses import dataclass, field
from typing import Deque, Dict, List, Tuple
from collections import deque

from ..core.errors import DispatcherError
from ..core.types import Transaction, ZoneId
from .causal_rules import CausalRules
from .smart_zone import SmartZoneRegistry


@dataclass(frozen=True)
class DispatchResult:
    tx_id: int
    zone_id: ZoneId
    queued: bool
    reason: str


@dataclass
class Dispatcher:
    registry: SmartZoneRegistry
    causal: CausalRules = field(default_factory=CausalRules)
    queues: Dict[ZoneId, Deque[Transaction]] = field(default_factory=dict)
    congestion_log: Dict[ZoneId, int] = field(default_factory=dict)
    committed_zones: Dict[int, ZoneId] = field(default_factory=dict)
    backlog_peak: Dict[ZoneId, int] = field(default_factory=dict)

    def _queue_for(self, zone_id: ZoneId) -> Deque[Transaction]:
        if zone_id not in self.queues:
            self.queues[zone_id] = deque()
        return self.queues[zone_id]

    def dispatch(self, tx: Transaction) -> DispatchResult:
        zone_id = tx.zone_id
        if not self.registry.contains(zone_id):
            raise DispatcherError("unknown_zone:" + zone_id)
        if tx.tx_id in self.committed_zones:
            self.causal.forbid_reroute(tx.tx_id, self.committed_zones[tx.tx_id], zone_id)
        self.committed_zones[tx.tx_id] = zone_id
        if not self.causal.check_dispatch(tx.tx_id, zone_id):
            return DispatchResult(tx.tx_id, zone_id, False, "causal_blocked")
        q = self._queue_for(zone_id)
        q.append(tx)
        size = len(q)
        self.backlog_peak[zone_id] = max(self.backlog_peak.get(zone_id, 0), size)
        self.congestion_log[zone_id] = size
        return DispatchResult(tx.tx_id, zone_id, True, "queued")

    def drain_batch(self, zone_id: ZoneId, batch_size: int) -> Tuple[Transaction, ...]:
        if not self.registry.contains(zone_id):
            raise DispatcherError("unknown_zone:" + zone_id)
        q = self._queue_for(zone_id)
        out: List[Transaction] = []
        while q and len(out) < batch_size:
            out.append(q.popleft())
        self.congestion_log[zone_id] = len(q)
        return tuple(out)

    def pending(self, zone_id: ZoneId) -> int:
        return len(self._queue_for(zone_id))

    def per_zone_pending(self) -> Dict[ZoneId, int]:
        return {z: len(q) for z, q in self.queues.items()}
