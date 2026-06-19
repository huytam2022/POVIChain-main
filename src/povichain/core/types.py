from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


ZoneId = str
ValidatorId = int
NodeId = int
BlockId = int
TxId = int
Hash = bytes


class ProofBackend(str, Enum):
    GROTH16 = "groth16"
    STARK = "stark"
    NONE = "none"


class Mode(str, Enum):
    A = "A"
    B = "B"


class ReplayMode(str, Enum):
    EXACT_CYCLE = "exact_cycle"
    EXACT_ONCE = "exact_once"
    MEDIAN_FIXED = "median_fixed"
    ENVELOPE_FIXED = "envelope_fixed"


@dataclass(frozen=True)
class Transaction:
    tx_id: TxId
    sender: int
    zone_id: ZoneId
    payload_bytes: int
    submitted_at_ms: float
    nonce: int


@dataclass(frozen=True)
class Vote:
    validator_id: ValidatorId
    block_id: BlockId
    stance: str
    weight: float
    cast_at_ms: float
    digest: bytes


@dataclass
class BlockHeader:
    block_id: BlockId
    parent_id: Optional[BlockId]
    zone_id: ZoneId
    merkle_root: Hash
    state_root: Hash
    tx_count: int
    proposer: ValidatorId
    epoch: int
    proposed_at_ms: float


@dataclass
class ReputationState:
    validator_id: ValidatorId
    r_current: float
    r_effective: float
    stake: float
    penalties: float
    collusion_flag: float


@dataclass
class CommitteeRecord:
    epoch: int
    seed: bytes
    threshold_theta: float
    members: Tuple[ValidatorId, ...]
    r_min: float


@dataclass
class ProofBundle:
    block_id: BlockId
    zone_id: ZoneId
    backend: ProofBackend
    proof_digest: bytes
    state_root: Hash
    merkle_root: Hash
    circuit_r1cs: int
    curve: str
    hash_primitive: str
    produced_at_ms: float
    proving_latency_ms: float


@dataclass
class DeviceProfile:
    device_class: str
    proving_latency_series_seconds: Tuple[float, ...] = field(default_factory=tuple)
    cpu_series_percent: Tuple[float, ...] = field(default_factory=tuple)
    memory_series_mb: Tuple[float, ...] = field(default_factory=tuple)
    verifier_latency_series_ms: Tuple[float, ...] = field(default_factory=tuple)
    resident_kb: float = 0.0
    peak_kb: float = 0.0
    proof_backend: Optional[ProofBackend] = None


@dataclass
class EnergyCoefficients:
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float
