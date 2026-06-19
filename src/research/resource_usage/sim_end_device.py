import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, List, Tuple

_RAM_PREFIX = "SEED|ESP32|RAM|"


def _det_jitter(prefix: str, key: int, amplitude: float) -> float:
    if amplitude <= 0.0:
        return 0.0
    h = hashlib.sha256((prefix + str(key)).encode("utf-8")).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass
class RAMSample:
    time_ms: float
    ram_kb: float


@dataclass
class EnergyBreakdown:
    protocol: str
    crypto_verify_mj: float
    hash_check_mj: float
    state_update_mj: float
    network_io_mj: float
    idle_baseline_mj: float

    @property
    def total_mj(self) -> float:
        return (
            self.crypto_verify_mj
            + self.hash_check_mj
            + self.state_update_mj
            + self.network_io_mj
            + self.idle_baseline_mj
        )


def run_esp32_ram_cycle(
    duration_ms: int,
    sample_interval_ms: int,
    idle_baseline_kb: float,
    peaks: Iterable[Tuple[float, float, float]],
    jitter_kb: float,
) -> List[RAMSample]:
    """Trace ESP32 RAM usage across one verification cycle.

    Each peak is (center_ms, height_kb, width_ms). RAM at time t is the
    idle baseline plus the sum of Gaussian peak contributions, plus
    deterministic per-sample jitter.
    """
    peaks_t = tuple(peaks)
    samples: List[RAMSample] = []
    t = 0
    while t <= duration_ms:
        ram = idle_baseline_kb
        for center, height, width in peaks_t:
            if width > 0.0:
                ram += height * math.exp(-((t - center) ** 2) / (2.0 * width ** 2))
        ram += _det_jitter(_RAM_PREFIX, t, jitter_kb)
        if ram < 0.0:
            ram = 0.0
        samples.append(RAMSample(time_ms=float(t), ram_kb=ram))
        t += sample_interval_ms
    return samples


def compute_energy_breakdown(spec: dict) -> EnergyBreakdown:
    return EnergyBreakdown(
        protocol=str(spec["protocol"]),
        crypto_verify_mj=float(spec["crypto_verify_mj"]),
        hash_check_mj=float(spec["hash_check_mj"]),
        state_update_mj=float(spec["state_update_mj"]),
        network_io_mj=float(spec["network_io_mj"]),
        idle_baseline_mj=float(spec["idle_baseline_mj"]),
    )
