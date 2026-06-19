import hashlib
from dataclasses import dataclass
from typing import List

_PREFIX = "SEED|HW|"


def _det_jitter(class_name: str, replicate: int, amplitude: float) -> float:
    if amplitude <= 0.0:
        return 0.0
    h = hashlib.sha256(
        (_PREFIX + class_name + "|" + str(replicate)).encode("utf-8")
    ).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass
class CostSample:
    class_name: str
    replicate: int
    value: float
    unit: str


@dataclass
class CostSummary:
    class_name: str
    unit: str
    median: float
    mean: float
    min_value: float
    max_value: float
    err_low: float
    err_high: float


def sample_uniform_jitter(
    class_name: str,
    median: float,
    amplitude: float,
    replicates: int,
) -> List[CostSample]:
    """Generate `replicates` deterministic samples with median±amplitude.

    Each sample = median + jitter, where jitter is uniform in [-amplitude, +amplitude]
    keyed by (class_name, replicate_idx) via SHA-256.
    """
    out: List[CostSample] = []
    for r in range(replicates):
        v = median + _det_jitter(class_name, r, amplitude)
        if v < 0.0:
            v = 0.0
        out.append(CostSample(class_name=class_name, replicate=r, value=v, unit=""))
    return out


def summarize_cost(samples: List[CostSample], unit: str) -> CostSummary:
    if not samples:
        return CostSummary(
            class_name="", unit=unit,
            median=0.0, mean=0.0, min_value=0.0, max_value=0.0,
            err_low=0.0, err_high=0.0,
        )
    name = samples[0].class_name
    vals = sorted(s.value for s in samples)
    n = len(vals)
    median = vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    mean = sum(vals) / n
    return CostSummary(
        class_name=name,
        unit=unit,
        median=median,
        mean=mean,
        min_value=vals[0],
        max_value=vals[-1],
        err_low=median - vals[0],
        err_high=vals[-1] - median,
    )
