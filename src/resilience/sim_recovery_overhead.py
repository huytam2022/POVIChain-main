import hashlib
from dataclasses import dataclass
from typing import List

_PREFIX = "SEED|RECOV|"


def _det_jitter(duration: int, replicate: int, metric: str, amplitude: float) -> float:
    if amplitude <= 0.0:
        return 0.0
    h = hashlib.sha256(
        (_PREFIX + str(duration) + "|" + str(replicate) + "|" + metric).encode("utf-8")
    ).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass
class RecoverySample:
    partition_duration: int
    replicate: int
    backlog_peak_tx: float
    orphan_stale_rate_pct: float


@dataclass
class RecoverySummary:
    partition_duration: int
    backlog_mean_tx: float
    backlog_min_tx: float
    backlog_max_tx: float
    orphan_mean_pct: float
    orphan_min_pct: float
    orphan_max_pct: float


def run_recovery_sweep(
    partition_durations: List[int],
    replicates: int,
    backlog_arrival_per_round: float,
    backlog_base_offset_tx: float,
    backlog_jitter_tx: float,
    orphan_slope_pct_per_round: float,
    orphan_base_offset_pct: float,
    orphan_jitter_pct: float,
):
    raw: List[RecoverySample] = []
    for d in partition_durations:
        for r in range(replicates):
            backlog = (
                backlog_arrival_per_round * d
                + backlog_base_offset_tx
                + _det_jitter(d, r, "backlog", backlog_jitter_tx)
            )
            orphan = (
                orphan_slope_pct_per_round * d
                + orphan_base_offset_pct
                + _det_jitter(d, r, "orphan", orphan_jitter_pct)
            )
            if backlog < 0.0:
                backlog = 0.0
            if orphan < 0.0:
                orphan = 0.0
            raw.append(RecoverySample(
                partition_duration=d,
                replicate=r,
                backlog_peak_tx=backlog,
                orphan_stale_rate_pct=orphan,
            ))
    return raw


def summarize_recovery(samples: List[RecoverySample]) -> List[RecoverySummary]:
    by_duration = {}
    for s in samples:
        by_duration.setdefault(s.partition_duration, []).append(s)
    out: List[RecoverySummary] = []
    for d in sorted(by_duration.keys()):
        rs = by_duration[d]
        bl = [s.backlog_peak_tx for s in rs]
        oc = [s.orphan_stale_rate_pct for s in rs]
        out.append(RecoverySummary(
            partition_duration=d,
            backlog_mean_tx=sum(bl) / len(bl),
            backlog_min_tx=min(bl),
            backlog_max_tx=max(bl),
            orphan_mean_pct=sum(oc) / len(oc),
            orphan_min_pct=min(oc),
            orphan_max_pct=max(oc),
        ))
    return out
