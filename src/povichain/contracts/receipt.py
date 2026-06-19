from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Receipt:
    tx_id: int
    block_id: int
    zone_id: str
    success: bool
    submitted_at_ms: float
    finalized_at_ms: float


@dataclass(frozen=True)
class FinalizationReceipt:
    block_id: int
    zone_id: str
    finalized_at_ms: float
    tx_ids: Tuple[int, ...]
    state_root: bytes
    merkle_root: bytes
