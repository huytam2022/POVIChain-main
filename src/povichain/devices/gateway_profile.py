from dataclasses import dataclass
from typing import Tuple

from ..core.errors import CalibrationError
from ..core.types import ProofBackend
from ..ingestion.processed_schema import ProcessedCalibration
from ..ingestion.trace_loader import TraceReplay, make_replay


@dataclass
class GatewayProfile:
    backend: ProofBackend
    cpu_replay: TraceReplay
    memory_replay: TraceReplay
    cpu_series_percent: Tuple[float, ...]
    memory_series_mb: Tuple[float, ...]


def build_gateway_profile(
    cal: ProcessedCalibration,
    backend: ProofBackend,
    replay_mode: str,
) -> GatewayProfile:
    if backend is ProofBackend.GROTH16:
        block = cal.pi4_groth16
    elif backend is ProofBackend.STARK:
        block = cal.pi4_stark
    else:
        raise CalibrationError("gateway_profile_requested_for_none_backend")
    if block is None:
        raise CalibrationError("missing_gateway_block_for_backend:" + backend.value)
    cpu_series = tuple(float(x) for x in block.cpu_utilization_percent.deterministic_series)
    mem_series = tuple(float(x) for x in block.resident_memory_mb.deterministic_series)
    return GatewayProfile(
        backend=backend,
        cpu_replay=make_replay(replay_mode, cpu_series),
        memory_replay=make_replay(replay_mode, mem_series),
        cpu_series_percent=cpu_series,
        memory_series_mb=mem_series,
    )
