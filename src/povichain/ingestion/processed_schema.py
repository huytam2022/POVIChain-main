from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SeriesStats:
    deterministic_series: Tuple[float, ...]
    median: Optional[float] = None
    ci95_low: Optional[float] = None
    ci95_high: Optional[float] = None


@dataclass(frozen=True)
class ProverBlock:
    proving_latency_seconds: SeriesStats
    cpu_utilization_percent: SeriesStats
    resident_memory_mb: SeriesStats


@dataclass(frozen=True)
class EspRamProfile:
    resident_baseline: float
    proof_reception_peak: float
    verification_peak: float
    post_update_return: float


@dataclass(frozen=True)
class EspBlock:
    merkle_verify_latency_ms: SeriesStats
    ram_profile_kb: EspRamProfile


@dataclass(frozen=True)
class EnergyCoefficientsSchema:
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float


@dataclass(frozen=True)
class ProofStack:
    curve: str
    hash: str
    r1cs_constraints: int
    stack: str


@dataclass(frozen=True)
class CalibrationPolicy:
    replay_mode: str
    interpolation: str


@dataclass(frozen=True)
class ProcessedCalibration:
    version: int
    generated_at: str
    generated_by: str
    raw_files: Tuple[str, ...]
    pi4_groth16: Optional[ProverBlock]
    pi4_stark: Optional[ProverBlock]
    esp32: Optional[EspBlock]
    calibration_policy: CalibrationPolicy
    energy_coefficients: Optional[EnergyCoefficientsSchema]
    proof_stack: Optional[ProofStack]
    raw_document: Dict = field(default_factory=dict)
