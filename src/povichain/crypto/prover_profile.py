from dataclasses import dataclass
from typing import Optional, Tuple

from ..core.errors import CalibrationError
from ..core.types import ProofBackend
from ..ingestion.processed_schema import ProcessedCalibration, ProverBlock
from ..ingestion.trace_loader import TraceReplay, make_replay


@dataclass
class ProverProfile:
    device_class: str
    backend: ProofBackend
    latency_ms_replay: TraceReplay
    cpu_percent_replay: TraceReplay
    memory_mb_replay: TraceReplay
    latency_series_ms: Tuple[float, ...]


def _seconds_to_ms(series: Tuple[float, ...]) -> Tuple[float, ...]:
    return tuple(float(x) * 1000.0 for x in series)


def _resolve_block(cal: ProcessedCalibration, backend: ProofBackend) -> Optional[ProverBlock]:
    if backend is ProofBackend.GROTH16:
        return cal.pi4_groth16
    if backend is ProofBackend.STARK:
        return cal.pi4_stark
    return None


def build_prover_profile(
    cal: ProcessedCalibration,
    backend: ProofBackend,
    replay_mode: str,
) -> ProverProfile:
    if backend is ProofBackend.NONE:
        raise CalibrationError("prover_profile_requested_for_none_backend")
    block = _resolve_block(cal, backend)
    if block is None:
        raise CalibrationError("missing_prover_block_for_backend:" + backend.value)
    latency_ms = _seconds_to_ms(block.proving_latency_seconds.deterministic_series)
    cpu_series = tuple(float(x) for x in block.cpu_utilization_percent.deterministic_series)
    mem_series = tuple(float(x) for x in block.resident_memory_mb.deterministic_series)
    return ProverProfile(
        device_class="raspberry_pi_4",
        backend=backend,
        latency_ms_replay=make_replay(replay_mode, latency_ms),
        cpu_percent_replay=make_replay(replay_mode, cpu_series),
        memory_mb_replay=make_replay(replay_mode, mem_series),
        latency_series_ms=latency_ms,
    )
