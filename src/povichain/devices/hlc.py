from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..core.errors import DeterminismError
from ..core.types import BlockHeader
from ..crypto.verifier import verify_merkle_only
from ..ingestion.trace_loader import TraceReplay


@dataclass
class HLCState:
    device_id: int
    resident_kb: float
    peak_kb: float
    reception_peak_kb: float
    verification_peak_kb: float
    post_update_return_kb: float
    ram_now_kb: float
    headers: Dict[str, BlockHeader] = field(default_factory=dict)
    verifications: int = 0
    peak_observed_kb: float = 0.0


@dataclass
class HybridLightClient:
    state: HLCState
    latency_replay: TraceReplay
    _allow_zkp: bool = False

    def attach_header(self, header: BlockHeader) -> None:
        self.state.headers[header.zone_id] = header

    def receive_proof(self) -> None:
        self.state.ram_now_kb = self.state.reception_peak_kb
        if self.state.ram_now_kb > self.state.peak_observed_kb:
            self.state.peak_observed_kb = self.state.ram_now_kb

    def verify_merkle(
        self,
        leaf: bytes,
        path: Tuple[Tuple[bytes, bool], ...],
        zone_id: str,
    ) -> Tuple[bool, float]:
        header = self.state.headers.get(zone_id)
        if header is None:
            return False, 0.0
        self.state.ram_now_kb = self.state.verification_peak_kb
        if self.state.ram_now_kb > self.state.peak_observed_kb:
            self.state.peak_observed_kb = self.state.ram_now_kb
        ok = verify_merkle_only(leaf, path, header.merkle_root)
        self.state.verifications += 1
        latency_ms = float(self.latency_replay.next_value())
        self.state.ram_now_kb = self.state.post_update_return_kb
        return ok, latency_ms

    def verify_zkp_forbidden(self) -> None:
        if not self._allow_zkp:
            raise DeterminismError("hlc_cannot_verify_full_zkp")
