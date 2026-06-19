from dataclasses import dataclass
from typing import Tuple

from ..core.errors import CalibrationError
from ..ingestion.processed_schema import ProcessedCalibration
from ..ingestion.trace_loader import TraceReplay, make_replay


@dataclass
class McuProfile:
    latency_replay: TraceReplay
    latency_series_ms: Tuple[float, ...]
    resident_baseline_kb: float
    proof_reception_peak_kb: float
    verification_peak_kb: float
    post_update_return_kb: float


def build_mcu_profile(cal: ProcessedCalibration, replay_mode: str) -> McuProfile:
    if cal.esp32 is None:
        raise CalibrationError("missing_esp32_block")
    series = tuple(float(x) for x in cal.esp32.merkle_verify_latency_ms.deterministic_series)
    ram = cal.esp32.ram_profile_kb
    return McuProfile(
        latency_replay=make_replay(replay_mode, series),
        latency_series_ms=series,
        resident_baseline_kb=float(ram.resident_baseline),
        proof_reception_peak_kb=float(ram.proof_reception_peak),
        verification_peak_kb=float(ram.verification_peak),
        post_update_return_kb=float(ram.post_update_return),
    )
