from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class LorenzResult:
    label: str
    reputations: List[float]
    cumulative_share: List[float]
    cumulative_population_pct: List[float]
    top_decile_share_pct: float
    median_to_top_decile_gap: float


def power_law_reputations(prover_count: int, alpha: float) -> List[float]:
    """rep_i = i^(-alpha) for i = 1..N (i=1 is the top prover)."""
    if prover_count <= 0:
        return []
    return [(i ** (-alpha)) for i in range(1, prover_count + 1)]


def lorenz_from_reputations(label: str, reps: List[float]) -> LorenzResult:
    """Compute cumulative-from-top Lorenz curve.

    cumulative_share[k] = sum of top-k reputations / total reputation
    cumulative_population_pct[k] = 100 * k / N
    """
    n = len(reps)
    total = float(sum(reps)) if reps else 1.0
    if total <= 0.0:
        total = 1.0
    cum_share = [0.0]
    running = 0.0
    for r in reps:
        running += float(r)
        cum_share.append(running / total)
    cum_pop_pct = [100.0 * k / n for k in range(n + 1)]

    decile_idx = max(1, n // 10)
    top_decile_share = cum_share[decile_idx] * 100.0

    median_idx = max(1, n // 2)
    median_share = cum_share[median_idx] * 100.0
    median_to_top_decile_gap = top_decile_share - cum_share[median_idx - 1] * 100.0
    gap = top_decile_share - (median_share - top_decile_share)
    if gap < 0.0:
        gap = abs(gap)

    return LorenzResult(
        label=label,
        reputations=reps,
        cumulative_share=cum_share,
        cumulative_population_pct=cum_pop_pct,
        top_decile_share_pct=top_decile_share,
        median_to_top_decile_gap=median_to_top_decile_gap,
    )


def reduction_pct(without_top10_pct: float, with_top10_pct: float) -> Tuple[float, float]:
    """Return (absolute_percentage_points, relative_percent) reduction in top-10 share.

    The absolute percentage-point reduction (e.g., 85% → 55% = 30 pp)
    is the headline figure; the relative reduction is provided as a
    secondary diagnostic.
    """
    abs_pp = without_top10_pct - with_top10_pct
    rel = (abs_pp / without_top10_pct * 100.0) if without_top10_pct > 0.0 else 0.0
    return abs_pp, rel
