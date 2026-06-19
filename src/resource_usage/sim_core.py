import hashlib
from dataclasses import dataclass
from typing import List

_CPU_PREFIX = "SEED|CPU|"
_MEM_PREFIX = "SEED|MEM|"
_PROVER_G16_PREFIX = "SEED|PROVER|G16|"
_PROVER_STK_PREFIX = "SEED|PROVER|STK|"


def _det_jitter(prefix: str, epoch: int, amplitude: float) -> float:
    """Deterministic per-epoch jitter, uniform in [-amplitude, +amplitude]."""
    if amplitude <= 0.0:
        return 0.0
    h = hashlib.sha256((prefix + str(epoch)).encode("utf-8")).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass
class ResourceEpochRecord:
    epoch: int
    cpu_utilization_pct: float
    memory_mb: float


@dataclass
class ProverEpochRecord:
    epoch: int
    groth16_seconds: float
    stark_seconds: float


def run_resource_profile(
    epochs: int,
    cpu_base_pct: float,
    cpu_slope_pct_per_epoch: float,
    cpu_jitter_pct: float,
    mem_base_mb: float,
    mem_slope_mb_per_epoch: float,
    mem_jitter_mb: float,
) -> List[ResourceEpochRecord]:
    records: List[ResourceEpochRecord] = []
    for e in range(1, epochs + 1):
        cpu = (
            cpu_base_pct
            + cpu_slope_pct_per_epoch * (e - 1)
            + _det_jitter(_CPU_PREFIX, e, cpu_jitter_pct)
        )
        mem = (
            mem_base_mb
            + mem_slope_mb_per_epoch * (e - 1)
            + _det_jitter(_MEM_PREFIX, e, mem_jitter_mb)
        )
        cpu = max(0.0, cpu)
        mem = max(0.0, mem)
        records.append(ResourceEpochRecord(
            epoch=e,
            cpu_utilization_pct=cpu,
            memory_mb=mem,
        ))
    return records


def run_prover_timing(
    epochs: int,
    groth16_base_s: float,
    groth16_slope_s_per_epoch: float,
    groth16_jitter_s: float,
    stark_base_s: float,
    stark_slope_s_per_epoch: float,
    stark_jitter_s: float,
) -> List[ProverEpochRecord]:
    records: List[ProverEpochRecord] = []
    for e in range(1, epochs + 1):
        g16 = (
            groth16_base_s
            + groth16_slope_s_per_epoch * (e - 1)
            + _det_jitter(_PROVER_G16_PREFIX, e, groth16_jitter_s)
        )
        stk = (
            stark_base_s
            + stark_slope_s_per_epoch * (e - 1)
            + _det_jitter(_PROVER_STK_PREFIX, e, stark_jitter_s)
        )
        g16 = max(0.0, g16)
        stk = max(0.0, stk)
        records.append(ProverEpochRecord(
            epoch=e,
            groth16_seconds=g16,
            stark_seconds=stk,
        ))
    return records
