from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from .source_chain import SourceBlock


@dataclass(frozen=True)
class TrustedHeader:
    chain_id: str
    block_id: int
    merkle_root: bytes
    state_root: bytes
    trusted_at_ms: float


@dataclass
class RelayLightClient:
    counterparty_chain_id: str
    storage_footprint_per_header_kb: float
    retention_headers: int
    _headers: Dict[int, TrustedHeader] = field(default_factory=dict)
    _order: list = field(default_factory=list)
    _latest_trusted_height: int = 0
    _updates_applied: int = 0
    _cumulative_verify_ms: float = 0.0
    _cumulative_storage_kb: float = 0.0

    def latest_trusted_height(self) -> int:
        return self._latest_trusted_height

    def trusted_header(self, height: int) -> Optional[TrustedHeader]:
        return self._headers.get(height)

    def has_trusted_header_for(self, height: int) -> bool:
        return height in self._headers

    def apply_header_update(
        self,
        source_block: SourceBlock,
        verify_latency_ms: float,
        applied_at_ms: float,
    ) -> TrustedHeader:
        if source_block.chain_id != self.counterparty_chain_id:
            raise ValueError("ibc_light_client_counterparty_mismatch")
        if source_block.block_id <= self._latest_trusted_height:
            raise ValueError("ibc_light_client_non_monotonic_update")
        header = TrustedHeader(
            chain_id=source_block.chain_id,
            block_id=source_block.block_id,
            merkle_root=source_block.merkle_root,
            state_root=source_block.state_root,
            trusted_at_ms=applied_at_ms,
        )
        self._headers[source_block.block_id] = header
        self._order.append(source_block.block_id)
        while len(self._order) > self.retention_headers:
            dropped = self._order.pop(0)
            self._headers.pop(dropped, None)
        self._latest_trusted_height = source_block.block_id
        self._updates_applied += 1
        self._cumulative_verify_ms += float(verify_latency_ms)
        self._cumulative_storage_kb = float(len(self._headers)) * self.storage_footprint_per_header_kb
        return header

    def updates_applied(self) -> int:
        return self._updates_applied

    def cumulative_verify_ms(self) -> float:
        return self._cumulative_verify_ms

    def storage_footprint_kb(self) -> float:
        return self._cumulative_storage_kb

    def headers_in_retention(self) -> int:
        return len(self._headers)
